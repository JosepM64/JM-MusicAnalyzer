import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QPushButton, QTableWidgetItem, QWidget

logger = logging.getLogger(__name__)


def rating_to_stars(rating):
    if not rating:
        return ""
    stars = int(rating)
    half = (rating - stars) >= 0.5
    result = "★" * stars
    if half:
        result += "½"
    return result


class InteractiveRatingWidget(QWidget):
    ratingChanged = Signal(float)

    def __init__(self, rating=0.0, parent=None):
        super().__init__(parent)
        self._rating = rating
        self._hover_rating = -1
        self.setFixedSize(70, 15)
        self.setMouseTracking(True)
        self.setStyleSheet("background: transparent;")

    def get_rating(self):
        return self._rating

    def set_rating(self, rating):
        self._rating = rating
        self.update()

    def _get_star_at_position(self, x):
        width = self.width()
        star_width = width / 5.0
        star_index = int(x / star_width)
        if star_index < 0:
            return 0.0
        star_index = min(star_index, 4)
        pos_in_star = (x - star_index * star_width) / star_width
        if pos_in_star < 0.4:
            return star_index + 0.5
        return star_index + 1.0

    def enterEvent(self, event):
        self.setMouseTracking(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_rating = -1
        self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        new_hover = self._get_star_at_position(event.position().x())
        if new_hover != self._hover_rating:
            self._hover_rating = new_hover
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        new_rating = self._get_star_at_position(event.position().x())
        if new_rating != self._rating:
            self._rating = new_rating
            self.ratingChanged.emit(self._rating)
            self.update()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        star_width = width / 5.0
        font = QFont()
        font.setPixelSize(12)
        painter.setFont(font)

        display_rating = self._hover_rating if self._hover_rating >= 0 else self._rating

        for i in range(5):
            x = i * star_width
            star_value = i + 1
            half_star_value = i + 0.5

            if display_rating >= star_value:
                color = QColor("#FFD700")
                text = "★"
            elif display_rating >= half_star_value:
                color = QColor("#FFD700")
                text = "½"
            else:
                color = QColor("#555555")
                text = "☆"

            painter.setPen(color)
            painter.drawText(int(x + 2), 12, text)


class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            user_role_self = self.data(Qt.ItemDataRole.UserRole)
            user_role_other = other.data(Qt.ItemDataRole.UserRole)
            if user_role_self is not None and user_role_other is not None:
                try:
                    return float(user_role_self) < float(user_role_other)
                except Exception:
                    pass
            val_self = (
                self.text()
                .replace("k", "")
                .replace("??", "-1")
                .replace(" MB", "")
                .replace(" KB", "")
                .replace(" GB", "")
                .replace(" B", "")
            )
            val_other = (
                other.text()
                .replace("k", "")
                .replace("??", "-1")
                .replace(" MB", "")
                .replace(" KB", "")
                .replace(" GB", "")
                .replace(" B", "")
            )
            return float(val_self) < float(val_other)
        except Exception:
            return self.text() < other.text()


def _format_file_size(size_bytes):
    if not size_bytes or size_bytes <= 0:
        return "-"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class FileListDataMixin:
    """Data loading (add_file_row, load_tracks_from_db, search/filter)."""

    def _get_path_at_row(self, row):
        item = self.item(row, 7)
        if item:
            fp = item.data(Qt.ItemDataRole.UserRole)
            if fp:
                return str(fp)
        logger.warning(f"[_get_path_at_row] No filepath found at row {row}, col 7")
        return None

    def is_file_duplicate(self, filepath: str) -> bool:
        return filepath in self._added_paths

    def add_file_row(
        self,
        filepath: str,
        subfolder: str = "",
        create_rating_widget: bool = True,
        index: int | None = None,
        highlight_new: bool = False,
    ):
        if filepath in self._added_paths:
            return None

        self._added_paths.add(filepath)
        row = index if index is not None else self.rowCount()
        self.insertRow(row)
        filename = os.path.basename(filepath)

        if not subfolder:
            subfolder = os.path.dirname(filepath)

        btn = QPushButton("??")
        btn.setFixedSize(24, 15)
        btn.setToolTip(f"Pre-escoltar: {filename}")
        btn.clicked.connect(lambda checked, fp=filepath: self._toggle_cue_preview(fp))
        self.setCellWidget(row, 0, btn)
        self._cue_buttons[filepath] = btn

        item_file = QTableWidgetItem(filename)
        item_file.setData(Qt.ItemDataRole.UserRole, filepath)
        if highlight_new:
            item_file.setForeground(QColor("#ffb347"))
            item_file.setToolTip("🆕 Descarregada recentment")

        item_folder = QTableWidgetItem(subfolder)
        item_folder.setForeground(QColor("#888"))
        item_folder.setToolTip(subfolder)

        self.setItem(row, 6, item_folder)
        self.setItem(row, 7, item_file)

        for i in [1, 2, 3, 5, 8, 9, 10]:
            self.setItem(row, i, QTableWidgetItem("-"))

        rating_item = NumericTableWidgetItem("")
        rating_item.setData(Qt.ItemDataRole.UserRole, 0.0)
        self.setItem(row, 4, rating_item)

        rating_widget = InteractiveRatingWidget(0.0)
        rating_widget.ratingChanged.connect(
            lambda r, fp=filepath: self._on_rating_changed(fp, r)
        )
        self.setCellWidget(row, 4, rating_widget)
        self._rating_widgets[filepath] = rating_widget

        return row

    def update_file_result(self, row: int, music_file, is_modified: bool = False):
        if row is None or row < 0:
            logger.warning("update_file_result: row is None or < 0, skipping")
            return

        filepath = getattr(music_file, "filepath", "unknown")
        meta = getattr(music_file, "metadata", None)
        tech = getattr(music_file, "technical", None)
        logger.debug(f"update_file_result: row={row}, filepath={filepath}")
        if meta:
            logger.debug(
                f"  artist={meta.artist}, title={meta.title}, genre={meta.genre}"
            )
        if tech:
            logger.debug(f"  duration={tech.duration}")

        if is_modified:
            self._modified_rows.add(row)
        elif row in self._modified_rows:
            self._modified_rows.discard(row)

        tech = music_file.technical
        meta = music_file.metadata

        bg_color = QColor("#3d3d20") if is_modified else None

        btn = self._cue_buttons.get(filepath)
        if btn:
            if tech and tech.bitrate and tech.bitrate > 0:
                btn.setToolTip(f"Pre-escoltar: {os.path.basename(filepath)}")
                btn.setStyleSheet("")
            else:
                btn.setToolTip(
                    f"Pre-escoltar: {os.path.basename(filepath)} (sense bitrate)"
                )
                btn.setStyleSheet("QPushButton { color: #888; }")

        if tech:
            item_br = NumericTableWidgetItem(f"{tech.bitrate or '??'}")
            if bg_color:
                item_br.setBackground(bg_color)
            self.setItem(row, 8, item_br)

            if tech and tech.file_size:
                size_str = _format_file_size(tech.file_size)
                item_size = NumericTableWidgetItem(size_str)
                item_size.setData(Qt.ItemDataRole.UserRole, tech.file_size)
                if bg_color:
                    item_size.setBackground(bg_color)
                self.setItem(row, 9, item_size)

            dur = 0
            try:
                if tech:
                    dur = float(tech.duration) if tech.duration else 0
            except Exception:
                dur = 0
            if dur > 0:
                mins = int(dur // 60)
                secs = int(dur % 60)
                dur_str = f"{mins:02d}:{secs:02d}"
            else:
                dur_str = "-"
            item_dur = NumericTableWidgetItem(dur_str)
            if bg_color:
                item_dur.setBackground(bg_color)
            self.setItem(row, 3, item_dur)

        if meta:
            filepath = music_file.filepath
            if filepath in self._rating_widgets:
                self._rating_widgets[filepath].set_rating(meta.rating or 0.0)

            rating_item = self.item(row, 4)
            if rating_item:
                rating_item.setData(Qt.ItemDataRole.UserRole, meta.rating or 0.0)

            item_artist = QTableWidgetItem(meta.artist or "Desconocido")
            if bg_color:
                item_artist.setBackground(bg_color)
            self.setItem(row, 1, item_artist)

            item_title = QTableWidgetItem(meta.title or "Sin título")
            if bg_color:
                item_title.setBackground(bg_color)
            self.setItem(row, 2, item_title)

            item_genre = QTableWidgetItem(meta.genre or "-")
            if bg_color:
                item_genre.setBackground(bg_color)
            self.setItem(row, 5, item_genre)

            bpm = getattr(meta, "bpm", None)
            item_bpm = NumericTableWidgetItem(str(bpm) if bpm else "-")
            if bpm:
                item_bpm.setData(Qt.ItemDataRole.UserRole, int(bpm))
            if bg_color:
                item_bpm.setBackground(bg_color)
            self.setItem(row, 10, item_bpm)

        self.viewport().update()

    def update_track_in_row(self, music_file):
        for row in range(self.rowCount()):
            filepath_item = self.item(row, 7)
            if filepath_item:
                fp = (
                    filepath_item.data(Qt.ItemDataRole.UserRole) or filepath_item.text()
                )
                if fp == music_file.filepath:
                    self.update_file_result(row, music_file)
                    return
        row = self.add_file_row(music_file.filepath)
        if row is not None:
            self.update_file_result(row, music_file)

    def clear_all(self):
        self._stop_cue_preview()
        self.setRowCount(0)
        self._added_paths.clear()
        self._modified_rows.clear()
        self._rating_widgets.clear()
        self._cue_buttons.clear()
        self._last_filters = None

    def load_tracks_from_db(self, tracks: list):
        try:
            was_sorting_enabled = self.isSortingEnabled()
            if was_sorting_enabled:
                self.setSortingEnabled(False)

            self.clear_all()
            total = len(tracks)
            self.setRowCount(total)

            for row, track in enumerate(tracks):
                filepath = track.get("filepath", "")
                if not filepath or filepath in self._added_paths:
                    continue

                self._added_paths.add(filepath)
                filename = os.path.basename(filepath)
                subfolder = os.path.dirname(filepath)

                btn = QPushButton("🎧")
                btn.setFixedSize(24, 15)
                btn.setToolTip(f"Pre-escoltar: {filename}")
                btn.clicked.connect(
                    lambda checked, fp=filepath: self._toggle_cue_preview(fp)
                )
                self.setCellWidget(row, 0, btn)
                self._cue_buttons[filepath] = btn

                item_file = QTableWidgetItem(filename)
                item_file.setData(Qt.ItemDataRole.UserRole, filepath)

                item_folder = QTableWidgetItem(subfolder)
                item_folder.setForeground(QColor("#888"))
                item_folder.setToolTip(subfolder)

                artist = track.get("artist", "...")
                item_artist = QTableWidgetItem(artist if artist else "...")
                self.setItem(row, 1, item_artist)

                title = track.get("title", filename)
                item_title = QTableWidgetItem(title if title else filename)
                self.setItem(row, 2, item_title)

                duration = track.get("duration", 0)
                dur_str = (
                    f"{int(duration // 60):02d}:{int(duration % 60):02d}"
                    if duration and duration > 0
                    else "--:--"
                )
                item_duration = NumericTableWidgetItem(dur_str)
                self.setItem(row, 3, item_duration)

                genre = track.get("genre", "")
                item_genre = QTableWidgetItem(genre if genre else "...")

                rating = track.get("rating", 0) or 0
                rating_item = NumericTableWidgetItem("")
                rating_item.setData(
                    Qt.ItemDataRole.UserRole, float(rating) if rating else 0.0
                )
                self.setItem(row, 4, rating_item)
                self.setItem(row, 5, item_genre)
                self.setItem(row, 6, item_folder)
                self.setItem(row, 7, item_file)

                bitrate = track.get("bitrate_header", 0) or 0
                item_br = NumericTableWidgetItem(str(bitrate) if bitrate else "??")
                self.setItem(row, 8, item_br)

                file_size = track.get("file_size", 0) or 0
                size_str = _format_file_size(file_size) if file_size else "??"
                item_size = NumericTableWidgetItem(size_str)
                item_size.setData(Qt.ItemDataRole.UserRole, file_size)
                self.setItem(row, 9, item_size)

                bpm = track.get("bpm", 0) or 0
                item_bpm = NumericTableWidgetItem(str(bpm) if bpm else "-")
                if bpm:
                    item_bpm.setData(Qt.ItemDataRole.UserRole, int(bpm))
                self.setItem(row, 10, item_bpm)

                rating_widget = InteractiveRatingWidget(
                    float(rating) if rating else 0.0
                )
                rating_widget.ratingChanged.connect(
                    lambda r, fp=filepath: self._on_rating_changed(fp, r)
                )
                self.setCellWidget(row, 4, rating_widget)
                self._rating_widgets[filepath] = rating_widget

            self.resizeColumnsToContents()
            self.setColumnWidth(0, 40)
            self.setColumnWidth(1, 160)
            self.setColumnWidth(2, 190)
            self.setColumnWidth(3, 50)
            self.setColumnWidth(4, 65)
            self.setColumnWidth(5, 80)
            self.setColumnWidth(6, 250)
            self.setColumnWidth(7, 180)
            self.setColumnWidth(8, 55)
            self.setColumnWidth(9, 70)
            self.setColumnWidth(10, 45)

            if was_sorting_enabled:
                self.setSortingEnabled(True)

            rows = self.rowCount()
            logger.info(f"load_tracks_from_db finished: {rows} rows in table")
        except Exception as e:
            if was_sorting_enabled:
                self.setSortingEnabled(True)
            logger.error(f"ERROR in load_tracks_from_db: {e}", exc_info=True)
            import traceback

            traceback.print_exc()
