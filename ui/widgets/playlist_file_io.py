import logging
import os
import subprocess

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QMenu, QMessageBox

from services.playlist_manager import PlaylistManager

logger = logging.getLogger(__name__)


class PlaylistFileIOMixin:
    def load_m3u(self, p):
        import time

        t0 = time.perf_counter()

        self._db_cache = None

        if self._current_preview_row >= 0:
            self.cue_player.stop()
            self._reset_row_highlight(self._current_preview_row)
            self._current_preview_row = -1

        if not self.is_master:
            playlist_name = os.path.basename(p)
            self._update_source_label(f"📋 {playlist_name}", "#9c27b0")
            self._current_source = f"playlist:{p}"

        self.table.setRowCount(0)
        self._batch_adding = True
        self._current_playlist_path = p
        self._playlist_order_index = 0

        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)

        t1 = time.perf_counter()
        track_paths = list(PlaylistManager.read_m3u(p))
        logger.debug(
            f"  -> load_m3u: leer playlist: {time.perf_counter() - t1:.3f}s ({len(track_paths)} tracks)"
        )

        t2 = time.perf_counter()
        if track_paths:
            from services.db import get_db

            db = get_db()
            self._db_cache = db.get_tracks_by_filepaths(track_paths)
            logger.debug(
                f"  -> load_m3u: cargar {len(self._db_cache)} tracks de DB: {time.perf_counter() - t2:.3f}s"
            )

        t3 = time.perf_counter()
        for idx, t in enumerate(track_paths):
            self.add_track(t, silent=True, skip_file_read=True, playlist_order=idx + 1)

        logger.debug(f"  -> load_m3u: add_track loop: {time.perf_counter() - t3:.3f}s")

        self._batch_adding = False
        self.pm.record_playlist_usage(p)

        if self.is_master:
            self._add_to_recent_combo(p)

        if not self.is_master:
            self.table.setSortingEnabled(sorting_enabled)

        self._db_cache = None

        if not self.is_master:
            t4 = time.perf_counter()
            self._rebuild_all_tracks_from_table()
            self._apply_filters()
            logger.debug(
                f"  -> load_m3u: rebuild+filtros: {time.perf_counter() - t4:.3f}s"
            )

        logger.debug(f"  -> load_m3u TOTAL: {time.perf_counter() - t0:.3f}s")

        QTimer.singleShot(0, self.playlistReady.emit)
        self._modified = False

    def _on_load_clicked(self):
        if self.is_master:
            if self.is_modified():
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
            default_dir = str(self.settings.get("default_playlist_dir", ""))
            p, _ = QFileDialog.getOpenFileName(
                self, "Cargar", default_dir, "Playlist (*.m3u)"
            )
            if p:
                self.load_m3u(p)
        else:
            self._show_load_options()

    def _on_save_clicked(self):
        if hasattr(self, "_current_playlist_path") and self._current_playlist_path:
            default_file = self._current_playlist_path
        else:
            default_file = ""

        if default_file:
            self._save_playlist_to_path(default_file)
        else:
            self._on_save_as_clicked()

    def _on_save_as_clicked(self):
        """Guardar playlist con nombre nuevo."""
        default_dir = str(self.settings.get("default_playlist_dir", ""))
        p, _ = QFileDialog.getSaveFileName(
            self, "Guardar como", default_dir, "Playlist (*.m3u)"
        )
        if p:
            self._save_playlist_to_path(p)

    def _on_save_context_menu(self, pos):
        """Menú contextual para el botón guardar."""
        menu = QMenu(self)
        if hasattr(self, "_current_playlist_path") and self._current_playlist_path:
            menu.addAction("💾 Guardar (sobreescribir)", self._on_save_clicked)
        menu.addAction("📥 Guardar como...", self._on_save_as_clicked)
        menu.exec(self.btn_save.mapToGlobal(pos))

    def _save_playlist_to_path(self, p):
        """Guarda la playlist en la ruta especificada."""
        ts = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 4)
            if item:
                ts.append(item.data(Qt.ItemDataRole.UserRole))
        PlaylistManager.save_m3u(p, ts)
        self.pm.record_playlist_usage(p)
        self._current_playlist_path = p
        self._modified = False

    def _edit_playlist_file(self):
        if not self._current_playlist_path or not os.path.isfile(
            self._current_playlist_path
        ):
            return

        subprocess.Popen(["notepad.exe", self._current_playlist_path])
