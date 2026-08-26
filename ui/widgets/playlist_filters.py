import logging
import math
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ui.styles import DARK_DIALOG_ACCENT_STYLE, DARK_DIALOG_STYLE

logger = logging.getLogger(__name__)


class PlaylistFilterMixin:
    def _update_genre_filter_from_all_tracks(self):
        """Actualiza el combo de géneros a partir de all_tracks."""
        if self.is_master or not self.all_tracks:
            return

        genres = set()
        for t in self.all_tracks:
            genre = t.get("genre", "")
            if genre:
                genres.add(genre)

        self.cb_genre_filter.blockSignals(True)
        self.cb_genre_filter.clear()
        self.cb_genre_filter.addItem("Todos", "")
        for genre in sorted(genres):
            self.cb_genre_filter.addItem(genre, genre)
        self.cb_genre_filter.blockSignals(False)

    def _rebuild_all_tracks_from_table(self):
        """Reconstruye all_tracks a partir del contenido actual de la tabla."""
        if self.is_master:
            return

        self.all_tracks = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 4)
            if not item:
                continue
            filepath = item.data(Qt.ItemDataRole.UserRole)

            artist_item = self.table.item(r, 3)
            artist = artist_item.text() if artist_item else ""

            title = item.text()

            genre_item = self.table.item(r, 6)
            genre = genre_item.text() if genre_item else ""

            rating_item = self.table.item(r, 7)
            rating = 0
            if rating_item:
                rating_text = rating_item.text()
                rating = rating_text.count("★")

            dur_item = self.table.item(r, 5)
            duration = 0
            if dur_item:
                dur_str = dur_item.text()
                if dur_str != "--:--":
                    try:
                        parts = dur_str.split(":")
                        if len(parts) == 2:
                            minutes = int(parts[0])
                            seconds = int(parts[1])
                            duration = minutes * 60 + seconds
                    except ValueError:
                        pass

            self.all_tracks.append(
                {
                    "filepath": filepath,
                    "artist": artist,
                    "title": title,
                    "genre": genre,
                    "rating": rating,
                    "duration": duration,
                }
            )

        self._update_genre_filter_from_all_tracks()

    def _apply_filters(self, reset_page=True):
        """Aplica los filtros de género, rating y búsqueda a la lista de tracks."""
        if self.is_master:
            return
        if not self.all_tracks and self.table.rowCount() > 0:
            self._rebuild_all_tracks_from_table()
        if not self.all_tracks:
            return

        genre_filter = self.cb_genre_filter.currentData()
        min_rating = self.cb_rating_filter.currentData()
        search_text = self.edit_search.text().strip().lower()

        filtered = []
        for t in self.all_tracks:
            if genre_filter and t.get("genre", "") != genre_filter:
                continue

            rating = t.get("rating", 0) or 0
            if min_rating is not None and rating < min_rating:
                continue

            if search_text:
                artist = (t.get("artist") or "").lower()
                title = (t.get("title") or "").lower()
                if search_text not in artist and search_text not in title:
                    continue

            filtered.append(t)

        self.filtered_tracks = filtered

        if reset_page:
            self.current_page = 1

        self.total_pages = max(1, math.ceil(len(filtered) / self.page_size))

        self.current_page = min(self.current_page, self.total_pages)

        self._update_table_page()

        self._update_pagination_display()

    def _update_table_page(self):
        """Muestra solo los tracks de la página actual en la tabla."""
        if self._current_preview_row >= 0:
            self.cue_player.stop()
            self._reset_row_highlight(self._current_preview_row)
            self._current_preview_row = -1

        if not self.filtered_tracks:
            self.table.setRowCount(0)
            self._update_row_numbers()
            self._refresh_all_widgets()
            return

        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.filtered_tracks))
        page_tracks = self.filtered_tracks[start_idx:end_idx]

        self.table.setRowCount(0)
        for t in page_tracks:
            self._add_track_from_db(t)

        self._update_row_numbers()
        self._refresh_all_widgets()

    def _update_pagination_display(self):
        """Actualiza la información de paginación y estado de botones."""
        if self.is_master:
            return

        self.lbl_page_info.setText(f"{self.current_page} / {self.total_pages}")

        self.btn_page_first.setEnabled(self.current_page > 1)
        self.btn_page_prev.setEnabled(self.current_page > 1)
        self.btn_page_next.setEnabled(self.current_page < self.total_pages)
        self.btn_page_last.setEnabled(self.current_page < self.total_pages)

        if hasattr(self, "spin_page_size"):
            if self.spin_page_size.value() != self.page_size:
                self.spin_page_size.setValue(self.page_size)

    def _go_to_page(self, page):
        """Navega a una página específica."""
        if self.is_master:
            return
        page = int(page)
        if page < 1 or page > self.total_pages:
            return
        self.current_page = page
        self._update_table_page()
        self._update_pagination_display()

    def _on_page_size_changed(self, new_size):
        """Cambia el número de tracks por página."""
        if self.is_master:
            return
        self.page_size = new_size
        self.current_page = 1
        self._apply_filters(reset_page=False)

    def cleanup_missing_files(self):
        """Elimina de la lista los tracks que ya no existen en disco o están dañados."""
        dlg = QDialog(self)
        dlg.setWindowTitle("🧹 Eliminar Pistas Muertas")
        dlg.setMinimumWidth(400)
        dlg.setStyleSheet(DARK_DIALOG_STYLE)
        layout = QVBoxLayout(dlg)
        lbl = QLabel(
            "🧹 Se van a ELIMINAR de la lista las pistas borradas del disco.\n\n"
            "Esta función busca y elimina canciones que:\n"
            "• Ya no existen en el disco (fueron movidas/eliminadas)\n"
            "• Estan corruptas o no se pueden leer\n\n"
            "⚠️ NOTA: Solo elimina las entradas de la LISTA, no los archivos del disco.\n\n"
            "¿Buscar pistas muertas?"
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        btns = QHBoxLayout()
        btn_no = QPushButton("No")
        btn_yes = QPushButton("Sí")
        btn_yes.setStyleSheet("background-color: #d32f2f;")
        btns.addStretch()
        btns.addWidget(btn_no)
        btns.addWidget(btn_yes)
        layout.addLayout(btns)

        btn_no.clicked.connect(dlg.reject)
        btn_yes.clicked.connect(dlg.accept)

        if not dlg.exec():
            return

        rows_to_remove = []
        for r in range(self.table.rowCount() - 1, -1, -1):
            item = self.table.item(r, 4)
            if item:
                path = item.data(Qt.ItemDataRole.UserRole)
                if not os.path.exists(path):
                    logger.debug(f"🧹 cleanup: no existe en disco -> {path}")
                    rows_to_remove.append(r)
                else:
                    try:
                        with open(path, "rb") as f:
                            f.read(100)
                    except Exception as e:
                        logger.debug(f"🧹 cleanup: error de lectura -> {path} : {e}")
                        rows_to_remove.append(r)

        if not rows_to_remove:
            QMessageBox.information(
                self,
                "✨ Lista Limpia",
                "✅ No se encontraron archivos faltantes o dañados.\n\n"
                "Tu lista está actualizada.",
            )
            return

        count = len(rows_to_remove)
        logger.debug(f"🧹 cleanup: {count} pista(s) marcades per eliminar")
        reply = QMessageBox.question(
            self,
            "Limpieza",
            f"🗑 Se encontraron {count} pista(s) que no existen o están dañadas.\n\n"
            "Solo se eliminarán de la LISTA, los archivos NO se borrarán del disco.\n\n"
            "¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return

        for r in rows_to_remove:
            if self._current_preview_row == r:
                self.cue_player.stop()
                self._reset_row_highlight(r)
                self._current_preview_row = -1
            elif self._current_preview_row > r:
                self._current_preview_row -= 1

        for r in rows_to_remove:
            self.table.removeRow(r)

        self._refresh_all_widgets()

        dlg = QDialog(self)
        dlg.setWindowTitle("🧹 Limpieza Completada")
        dlg.setMinimumWidth(350)
        dlg.setStyleSheet(DARK_DIALOG_ACCENT_STYLE)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(5)

        if count > 0:
            layout.addWidget(QLabel(f"🗑️ Se eliminaron {count} pista(s) de la lista."))
            layout.addWidget(QLabel("Los archivos han sido quitados de la lista."))
            layout.addWidget(QLabel("(No se han eliminado del disco)."))
        else:
            layout.addWidget(QLabel("✨ No se encontraron pistas muertas."))
            layout.addWidget(QLabel("Tu lista está actualizada."))

        btn = QPushButton("Aceptar")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec()
