import logging
import os
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

from core.reader.mp3_reader import MP3Reader
from ui.widgets.file_list_data import rating_to_stars
from ui.widgets.row_preview_player import RowPreviewPlayer

logger = logging.getLogger(__name__)


class PlaylistTrackOpsMixin:
    def add_track(self, path, silent=False, skip_file_read=False, playlist_order=None):
        if not silent:
            for r in range(self.table.rowCount()):
                item = self.table.item(r, 4)
                if item and item.data(Qt.ItemDataRole.UserRole) == path:
                    title_item = self.table.item(r, 4)
                    title = title_item.text() if title_item else os.path.basename(path)
                    artist_item = self.table.item(r, 3)
                    artist = artist_item.text() if artist_item else ""
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setWindowTitle("Canción repetida")
                    msg.setText("Esta canción ya está en la lista:")
                    msg.setDetailedText(f"{artist} - {title}\n{path}")
                    btn_skip = msg.addButton("Omitir", QMessageBox.ButtonRole.NoRole)
                    _btn_add_anyway = msg.addButton(
                        "Añadir de todos modos", QMessageBox.ButtonRole.AcceptRole
                    )
                    btn_go_to = msg.addButton(
                        "Ir a la canción", QMessageBox.ButtonRole.AcceptRole
                    )
                    msg.setDefaultButton(btn_skip)
                    msg.exec()
                    if msg.clickedButton() == btn_skip:
                        return
                    if msg.clickedButton() == btn_go_to:
                        self.table.selectRow(r)
                        scroll_item = self.table.item(r, 0)
                        if scroll_item:
                            self.table.scrollToItem(scroll_item)
                        return
                    break

        t0 = time.perf_counter()
        r = self.table.rowCount()
        self.table.insertRow(r)
        self._modified = True
        artist, title, genre, dur, stars = "...", os.path.basename(path), "", None, 0

        duration = None
        source = "none"
        try:
            from services.db import get_db

            if self._db_cache is None:
                db = get_db()
                self._db_cache = db.get_all_tracks()
                logger.debug(
                    f"  -> add_track: cache DB cargada ({len(self._db_cache)} tracks)"
                )

            from utils.paths import normalize_path

            track_data = None
            if isinstance(self._db_cache, dict):
                normalized_path = normalize_path(path)
                track_data = self._db_cache.get(normalized_path)
            else:
                for t in self._db_cache:
                    if t.get("filepath") == path:
                        track_data = t
                        break

            if track_data:
                artist = track_data.get("artist", artist)
                title = track_data.get("title", title)
                genre = track_data.get("genre", "")
                stars = track_data.get("rating", 0) or 0
                duration = track_data.get("duration", 0)
                source = "db"
        except Exception:
            pass

        if not duration or duration <= 0:
            if not skip_file_read:
                try:
                    reader = MP3Reader(path)
                    mf = reader.read(True, False)
                    source = "file"
                    if mf and mf.metadata:
                        artist = mf.metadata.artist or artist
                        title = mf.metadata.title or title
                        genre = mf.metadata.genre or ""
                        stars = mf.metadata.rating or 0
                    if mf and mf.technical:
                        duration = mf.technical.duration
                except Exception:
                    pass
            else:
                source = "skip"

        if duration and duration > 0:
            dur = f"{int(duration // 60):02d}:{int(duration % 60):02d}"
        else:
            dur = "--:--"

        if playlist_order is None:
            playlist_order = r + 1
        num_item = QTableWidgetItem(f"{playlist_order:02d}")
        num_item.setData(Qt.ItemDataRole.UserRole, playlist_order)
        self.table.setItem(r, 0, num_item)

        w = RowPreviewPlayer(path)
        w.cueClicked.connect(
            lambda p_path, row_idx=r: self._on_cue_clicked(row_idx, p_path)
        )
        self.table.setCellWidget(r, 1, w)
        self.table.setItem(
            r, 2, QTableWidgetItem(str(self.play_counts_manager.get(path)))
        )
        self.table.setItem(r, 3, QTableWidgetItem(artist))
        ti = QTableWidgetItem(title)
        ti.setData(Qt.ItemDataRole.UserRole, path)
        self.table.setItem(r, 4, ti)
        self.table.setItem(r, 5, QTableWidgetItem(dur))
        self.table.setItem(r, 6, QTableWidgetItem(genre))
        ri = QTableWidgetItem(rating_to_stars(stars))
        ri.setForeground(QColor("gold"))
        self.table.setItem(r, 7, ri)

        if track_data:
            folder = os.path.dirname(track_data.get("filepath", path))
            bitrate = track_data.get("bitrate_real", 0) or track_data.get(
                "bitrate_header", 0
            )
            filesize = track_data.get("filesize", 0)
        else:
            folder = os.path.dirname(path)
            bitrate = 0
            try:
                filesize = os.path.getsize(path)
            except Exception:
                filesize = 0
        bitrate_str = f"{bitrate}" if bitrate else "?"
        size_str = f"{filesize / (1024 * 1024):.1f}M" if filesize else "?"
        self.table.setItem(r, 8, QTableWidgetItem(folder))
        self.table.setItem(r, 9, QTableWidgetItem(bitrate_str))
        self.table.setItem(r, 10, QTableWidgetItem(size_str))

        elapsed = time.perf_counter() - t0
        if elapsed > 0.1:
            logger.debug(
                f"  -> add_track slow: {elapsed:.3f}s, source={source}, path={os.path.basename(path)}"
            )

        if not self.is_master and not self._batch_adding:
            self._rebuild_all_tracks_from_table()

    def _add_track_from_db(self, track):
        """Añade una fila a la tabla desde un registro de la base de datos."""
        r = self.table.rowCount()
        self.table.insertRow(r)

        filepath = track["filepath"]
        artist = track.get("artist", "...")
        title = track.get("title", os.path.basename(filepath))
        genre = track.get("genre", "")
        duration = track.get("duration", 0)
        stars = track.get("rating", 0) or 0

        dur_str = "--:--"
        if duration and duration > 0:
            dur_str = f"{int(duration // 60):02d}:{int(duration % 60):02d}"

        w = RowPreviewPlayer(filepath)
        w.cueClicked.connect(
            lambda p_path, row_idx=r: self._on_cue_clicked(row_idx, p_path)
        )
        self.table.setCellWidget(r, 1, w)

        play_count = self.play_counts_manager.get(filepath)
        self.table.setItem(r, 2, QTableWidgetItem(str(play_count)))

        self.table.setItem(r, 3, QTableWidgetItem(artist))
        ti = QTableWidgetItem(title)
        ti.setData(Qt.ItemDataRole.UserRole, filepath)
        ti.setToolTip(filepath)
        self.table.setItem(r, 4, ti)

        self.table.setItem(r, 5, QTableWidgetItem(dur_str))
        self.table.setItem(r, 6, QTableWidgetItem(genre))
        ri = QTableWidgetItem(rating_to_stars(stars))
        ri.setForeground(QColor("gold"))
        self.table.setItem(r, 7, ri)

        folder = os.path.dirname(filepath)
        bitrate = track.get("bitrate_real", 0) or track.get("bitrate_header", 0)
        filesize = track.get("filesize", 0)
        bitrate_str = f"{bitrate}" if bitrate else "?"
        size_str = f"{filesize / (1024 * 1024):.1f}M" if filesize else "?"
        self.table.setItem(r, 8, QTableWidgetItem(folder))
        self.table.setItem(r, 9, QTableWidgetItem(bitrate_str))
        self.table.setItem(r, 10, QTableWidgetItem(size_str))
