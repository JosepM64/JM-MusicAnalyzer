import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMenu, QMessageBox

from ui.widgets.file_list_data import rating_to_stars

logger = logging.getLogger(__name__)


class PlaylistContextMenuMixin:
    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        it = self.table.item(row, 4)
        if not it:
            return
        p = it.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        selected_rows = set()
        for sel_item in self.table.selectedItems():
            selected_rows.add(sel_item.row())

        multi = len(selected_rows) > 1

        if multi:
            paths = []
            for r in sorted(selected_rows):
                it2 = self.table.item(r, 4)
                if it2:
                    fp = it2.data(Qt.ItemDataRole.UserRole)
                    if fp:
                        paths.append(fp)
            menu.addAction(
                f"💿 Deck A ({os.path.basename(p)})",
                lambda: self.trackLoaded.emit(p, "A"),
            )
            menu.addAction(
                f"💿 Deck B ({os.path.basename(p)})",
                lambda: self.trackLoaded.emit(p, "B"),
            )
            if not self.is_master and paths:
                menu.addAction(
                    f"➕ Añadir {len(paths)} canciones a lista master",
                    lambda ps=paths: self.batchAddToMaster.emit(ps),
                )
            menu.addSeparator()
            menu.addAction(
                f"🗑 Quitar {len(paths)} canciones", self._remove_selected_rows
            )
        else:
            menu.addAction("💿 Deck A", lambda: self.trackLoaded.emit(p, "A"))
            menu.addAction("💿 Deck B", lambda: self.trackLoaded.emit(p, "B"))
            if not self.is_master:
                menu.addAction(
                    "➕ Añadir a lista master", lambda: self.trackAddToMaster.emit(p)
                )
            menu.addSeparator()
            menu.addAction("⬆ Mover arriba", lambda: self._move_row_up(row))
            menu.addAction("⬇ Mover abajo", lambda: self._move_row_down(row))
            menu.addAction(
                "🔢 Mover a posición...", lambda: self._move_to_position(row)
            )
            menu.addSeparator()
            menu.addAction("🗑 Quitar", self._remove_selected_rows)
            menu.addAction("🔄 Reset Plays", lambda: self._reset_plays(p))
            menu.addAction("✏️ Editar metadatos...", lambda: self._edit_metadata(row, p))
            rat = menu.addMenu("⭐ Rating")
            rating_options = [
                "Sin",
                "★",
                "★½",
                "★★",
                "★★½",
                "★★★",
                "★★★½",
                "★★★★",
                "★★★★½",
                "★★★★★",
            ]
            for i, label in enumerate(rating_options):
                rat.addAction(label, lambda v=i / 2.0: self.ratingChanged.emit(p, v))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _edit_metadata(self, row, path):
        """Abre diálogo para editar metadatos de la pista."""
        from services.db import get_db
        from ui.dialogs.track_edit_dialog import TrackEditDialog

        artist_item = self.table.item(row, 3)
        title_item = self.table.item(row, 4)
        genre_item = self.table.item(row, 6)
        rating_item = self.table.item(row, 7)
        artist = artist_item.text() if artist_item else ""
        title = title_item.text() if title_item else ""
        genre = genre_item.text() if genre_item else ""
        rating = 0
        if rating_item:
            rating_text = rating_item.text()
            rating = rating_text.count("★") + (0.5 if "½" in rating_text else 0)

        db = get_db()
        dlg = TrackEditDialog(artist, title, genre, rating, db, self)
        if dlg.exec() != 1:
            return

        data = dlg.get_data()
        new_title, new_artist = data["title"], data["artist"]
        new_genre, new_rating = data["genre"], data["rating"]

        if title_item:
            title_item.setText(new_title)
        if artist_item:
            artist_item.setText(new_artist)
        if genre_item:
            genre_item.setText(new_genre)
        if rating_item:
            rating_item.setText(rating_to_stars(new_rating))
            rating_item.setForeground(QColor("gold"))

        from services.metadata_service import MetadataService

        MetadataService().save_from_panel(path, data)

        self.ratingChanged.emit(path, new_rating)
        if not self.is_master:
            self._update_track_in_all_tracks(
                path, new_title, new_artist, new_genre, new_rating
            )
        self.metadataChanged.emit(path, data)

    def _update_track_in_all_tracks(self, path, title, artist, genre, rating):
        """Actualiza la entrada en all_tracks para reflejar cambios en metadatos."""
        for track in self.all_tracks:
            if track.get("filepath") == path:
                track["title"] = title
                track["artist"] = artist
                track["genre"] = genre
                track["rating"] = rating
                break
        if not self.is_master:
            self._update_genre_filter_from_all_tracks()
            self._apply_filters(reset_page=False)

    def _update_track_rating_in_all_tracks(self, path, rating):
        """Actualiza solo el rating en all_tracks."""
        for track in self.all_tracks:
            if track.get("filepath") == path:
                track["rating"] = rating
                break
        if not self.is_master:
            self._apply_filters(reset_page=False)

    def update_rating_in_table(self, path, stars):
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 4)
            if it and it.data(Qt.ItemDataRole.UserRole) == path:
                s_it = self.table.item(r, 7)
                if s_it:
                    s_it.setText(rating_to_stars(stars))
                break
        if not self.is_master:
            self._update_track_rating_in_all_tracks(path, stars)
        from services.metadata_service import MetadataService

        ms = MetadataService()
        ms.save_field(path, rating=stars)

    def _on_recent_selected(self, index):
        p = self.cb_recent.itemData(index)
        if p and os.path.exists(p):
            if self.is_master and self.is_modified():
                reply = QMessageBox.question(
                    self,
                    "Playlist modificada",
                    "La playlist principal tiene cambios sin guardar.\n"
                    "¿Qué deseas hacer?",
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Save:
                    self._on_save_clicked()
                elif reply == QMessageBox.StandardButton.Cancel:
                    return
            self.load_m3u(p)

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            it = self.table.item(rows[0].row(), 4)
            if it:
                self.trackSelected.emit(it.data(Qt.ItemDataRole.UserRole))

    def _reset_plays(self, path):
        self.play_counts_manager.reset(path)
        self._refresh_play_count_in_table(path)

    def _on_double_click(self, idx):
        self._last_load_deck = "B" if self._last_load_deck == "A" else "A"
        it = self.table.item(idx.row(), 4)
        if it:
            self.trackLoaded.emit(
                it.data(Qt.ItemDataRole.UserRole), self._last_load_deck
            )
