import logging
import os

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from PySide6.QtWidgets import QDialog

logger = logging.getLogger(__name__)


class PlaylistSourceLoaderMixin:
    def _load_recent(self):
        import time

        t0 = time.perf_counter()

        self.cb_recent.blockSignals(True)
        self.cb_recent.clear()
        for r in self.pm.get_recent_playlists():
            if os.path.exists(r):
                self.cb_recent.addItem(os.path.basename(r), r)
        logger.debug(
            f"  -> _load_recent: cargar combos: {time.perf_counter() - t0:.3f}s"
        )

        last = self.pm.get_last_playlist()
        if (
            last
            and os.path.exists(last)
            and self.settings.get("auto_load_last_playlist", True)
        ):
            try:
                t1 = time.perf_counter()
                self.load_m3u(last)
                logger.debug(
                    f"  -> _load_recent: load_m3u({os.path.basename(last)}): {time.perf_counter() - t1:.3f}s"
                )
                idx = self.cb_recent.findData(last)
                if idx >= 0:
                    self.cb_recent.setCurrentIndex(idx)
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Error cargando última playlist: {e}"
                )
                self._current_playlist_path = None
        elif last:
            idx = self.cb_recent.findData(last)
            if idx >= 0:
                self.cb_recent.setCurrentIndex(idx)
        self.cb_recent.blockSignals(False)
        QTimer.singleShot(0, self.playlistReady.emit)

        logger.debug(f"  -> _load_recent TOTAL: {time.perf_counter() - t0:.3f}s")

    def _load_recent_combobox_only(self):
        """Carga el combobox de playlists recientes sin cargar ninguna playlist automáticamente."""
        import time

        t0 = time.perf_counter()

        self.cb_recent.blockSignals(True)
        self.cb_recent.clear()
        for r in self.pm.get_recent_playlists():
            if os.path.exists(r):
                self.cb_recent.addItem(os.path.basename(r), r)
        logger.debug(
            f"  -> _load_recent_combobox_only: cargar combos: {time.perf_counter() - t0:.3f}s"
        )

        last = self.pm.get_last_playlist()
        if last:
            idx = self.cb_recent.findData(last)
            if idx >= 0:
                self.cb_recent.setCurrentIndex(idx)

        self.cb_recent.blockSignals(False)

        logger.debug(
            f"  -> _load_recent_combobox_only TOTAL: {time.perf_counter() - t0:.3f}s"
        )

    def _add_to_recent_combo(self, playlist_path):
        """Afegeix una playlist al combobox de recent si no existeix."""
        self.cb_recent.blockSignals(True)

        existing_idx = self.cb_recent.findData(playlist_path)
        if existing_idx >= 0:
            self.cb_recent.removeItem(existing_idx)

        self.cb_recent.insertItem(0, os.path.basename(playlist_path), playlist_path)
        self.cb_recent.setCurrentIndex(0)

        self.cb_recent.blockSignals(False)

    def _refresh_favorites_combo(self):
        """Actualiza el combobox de carpetas favoritas."""
        if self.is_master:
            return
        self.cb_favorites.blockSignals(True)
        self.cb_favorites.clear()
        favorites = self.bm.load_bookmarks()
        for fav in favorites:
            path = fav.get("path", fav) if isinstance(fav, dict) else fav
            recursive = fav.get("recursive", True) if isinstance(fav, dict) else True
            icon = "📂" if recursive else "📁"
            self.cb_favorites.addItem(f"{icon} {os.path.basename(path)}", path)
        self.cb_favorites.blockSignals(False)

    def _update_source_label(self, text, color):
        """Actualiza el indicador visual de origen (Biblioteca/Favorito)."""
        if self.is_master or not hasattr(self, "lbl_source"):
            return
        self.lbl_source.setText(text)
        self.lbl_source.setStyleSheet(f"""
            color: {color};
            font-weight: bold;
            font-size: 11px;
            padding: 3px 8px;
            border: 1px solid {color};
            border-radius: 3px;
            background-color: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1);
        """)

    def _on_load_library_clicked(self):
        """Carga toda la biblioteca desde la base de datos."""
        if self.is_master:
            return
        self.load_from_favorites()

    def _on_load_favorite_clicked(self):
        """Carga los tracks de la carpeta favorita seleccionada, amb selecció de subcarpeta."""
        if self.is_master:
            return
        index = self.cb_favorites.currentIndex()
        if index < 0:
            QMessageBox.information(
                self,
                "Seleccionar favorito",
                "Selecciona una carpeta favorita de la lista.",
            )
            return
        folder_path = self.cb_favorites.itemData(index)
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(
                self, "Carpeta no existe", "La carpeta favorita seleccionada no existe."
            )
            return
        selected = self._select_subfolder_dialog(folder_path)
        if selected is None:
            return
        self.load_from_favorite_folder(selected)

    def _get_subfolders(self, folder_path):
        """Retorna llista de subcarpetes dins d'una carpeta."""
        try:
            return sorted(
                [
                    os.path.join(folder_path, d)
                    for d in os.listdir(folder_path)
                    if os.path.isdir(os.path.join(folder_path, d))
                ]
            )
        except PermissionError:
            return []
        except Exception as e:
            logger.warning(f"Error llegint subcarpetes de {folder_path}: {e}")
            return []

    def _select_subfolder_dialog(self, folder_path):
        """Dialeg per seleccionar una subcarpeta dins d'una carpeta favorita."""
        subfolders = self._get_subfolders(folder_path)
        if not subfolders:
            return folder_path

        dlg = QDialog(self)
        dlg.setWindowTitle("Seleccionar subcarpeta")
        dlg.setMinimumWidth(400)
        dlg.setStyleSheet("""
            QDialog { background-color: #2b2b2b; }
            QLabel { color: #eee; font-size: 11px; }
            QListWidget { background-color: #1a1a1a; color: #ccc; font-size: 11px;
                           border: 1px solid #444; }
            QListWidget::item:selected { background-color: #004a80; }
            QPushButton { background-color: #333; color: white; border: 1px solid #444;
                          padding: 6px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #444; }
        """)

        layout = QVBoxLayout(dlg)
        folder_name = os.path.basename(folder_path) or folder_path
        lbl = QLabel(f"<b>{folder_name}</b> conté subcarpetes. Selecciona una:")
        layout.addWidget(lbl)

        list_widget = QListWidget()
        list_widget.addItem("📁 [CARPETA ENTERA]")
        for sf in subfolders:
            list_widget.addItem(f"📂 {os.path.basename(sf)}")
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel·lar")
        btn_select = QPushButton("Seleccionar")
        btn_select.setStyleSheet("background-color: #6a1b9a; color: white;")
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_select)
        layout.addLayout(btn_row)

        result = [None]

        def on_accept():
            row = list_widget.currentRow()
            if row <= 0:
                result[0] = folder_path
            else:
                result[0] = subfolders[row - 1]
            dlg.accept()

        btn_select.clicked.connect(on_accept)
        btn_cancel.clicked.connect(dlg.reject)
        list_widget.doubleClicked.connect(on_accept)

        if dlg.exec():
            return result[0]
        return None

    def _show_load_options(self):
        """Dialeg per triar com afegir contingut a Llista 2 (playlist, arxius, carpeta)."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Afegir a Llista 2")
        dlg.setMinimumWidth(380)
        dlg.setStyleSheet("""
            QDialog { background-color: #2b2b2b; }
            QLabel { color: #eee; font-size: 11px; }
            QPushButton { background-color: #333; color: white; border: 1px solid #444;
                          padding: 8px 16px; border-radius: 4px; font-size: 12px;
                          text-align: left; }
            QPushButton:hover { background-color: #444; }
        """)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)

        lbl = QLabel("<b>Què vols carregar a la Llista 2?</b>")
        layout.addWidget(lbl)

        btn_playlist = QPushButton("📋  Carregar playlist (.m3u)")
        btn_files = QPushButton("🎵  Afegir arxius d'àudio")
        btn_folder = QPushButton("📁  Afegir carpeta (recursiu)")
        btn_cancel = QPushButton("Cancel·lar")

        layout.addWidget(btn_playlist)
        layout.addWidget(btn_files)
        layout.addWidget(btn_folder)
        layout.addWidget(btn_cancel)

        def on_playlist():
            dlg.accept()
            default_dir = str(self.settings.get("default_playlist_dir", ""))
            p, _ = QFileDialog.getOpenFileName(
                self, "Carregar Playlist", default_dir, "Playlist (*.m3u)"
            )
            if p:
                self.load_m3u(p)

        def on_files():
            dlg.accept()
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Seleccionar arxius d'àudio",
                "",
                "Audio (*.mp3 *.flac *.ogg *.wav *.m4a *.wma *.aac);;Tots els arxius (*)",
            )
            if files:
                self._batch_adding = True
                for f in files:
                    self.add_track(f, silent=True)
                self._batch_adding = False
                if not self.is_master:
                    self._rebuild_all_tracks_from_table()
                    self._apply_filters()

        def on_folder():
            dlg.accept()
            folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
            if folder:
                self._load_folder_to_list(folder)

        btn_playlist.clicked.connect(on_playlist)
        btn_files.clicked.connect(on_files)
        btn_folder.clicked.connect(on_folder)
        btn_cancel.clicked.connect(dlg.reject)

        dlg.exec()

    def _load_folder_to_list(self, folder_path):
        """Carrega tots els arxius d'àudio d'una carpeta (recursiu) a la llista."""
        import time

        t0 = time.perf_counter()

        self._batch_adding = True
        audio_exts = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".wma", ".aac"}
        count = 0

        for root, dirs, files in os.walk(folder_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in audio_exts:
                    filepath = os.path.join(root, f)
                    self.add_track(filepath, silent=True)
                    count += 1

        self._batch_adding = False
        if not self.is_master:
            self._rebuild_all_tracks_from_table()
            self._apply_filters()

        elapsed = time.perf_counter() - t0
        logger.info(
            f"_load_folder_to_list: {count} tracks from {folder_path} in {elapsed:.2f}s"
        )
        if not self.is_master:
            self._update_source_label(
                f"📁 {os.path.basename(folder_path)} ({count} tracks)", "#ff9800"
            )
            self._current_source = f"folder:{folder_path}"

    def _on_refresh_favorites_clicked(self):
        """Actualiza la lista desde la base de datos."""
        if self.is_master:
            return
        current_source = getattr(self, "_current_source", None)
        if current_source:
            if current_source == "biblioteca":
                self.load_from_favorites()
            elif current_source.startswith("favorito:"):
                folder_path = current_source.replace("favorito:", "")
                self.load_from_favorite_folder(folder_path)
            elif current_source.startswith("playlist:"):
                playlist_path = current_source.replace("playlist:", "")
                self.load_m3u(playlist_path)
        else:
            self.load_from_favorites()

    def _on_load_playlist_clicked(self):
        """Carga una playlist en la segunda lista."""
        if self.is_master:
            return
        default_dir = str(self.settings.get("default_playlist_dir", ""))
        p, _ = QFileDialog.getOpenFileName(
            self, "Cargar Playlist", default_dir, "Playlist (*.m3u)"
        )
        if p:
            self.load_m3u(p)

    def _on_recargar_clicked(self):
        """Recarga la playlist actual desde su archivo fuente."""
        if (
            not hasattr(self, "_current_playlist_path")
            or not self._current_playlist_path
            or not os.path.isfile(self._current_playlist_path)
        ):
            QMessageBox.information(
                self, "Recargar", "No hay una playlist cargada para recargar."
            )
            return
        if self.is_master and self.is_modified():
            reply = QMessageBox.question(
                self,
                "Playlist modificada",
                "La playlist principal tiene cambios sin guardar.\n¿Qué deseas hacer?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._on_save_clicked()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.load_m3u(self._current_playlist_path)

    def load_from_favorite_folder(self, folder_path):
        """Carga todos los tracks de una carpeta favorita desde la base de datos (async)."""
        if self.is_master:
            return

        logger.debug(f"[FAVORIT] load_from_favorite_folder: {folder_path}")
        logger.debug(f"[FAVORIT] folder exists: {os.path.exists(folder_path)}")

        self._db_cache = None

        folder_name = os.path.basename(folder_path) or folder_path
        self._update_source_label(f"📁 Carregant {folder_name}...", "#ff9800")
        self._current_source = f"favorito:{folder_path}"

        if self._current_preview_row >= 0:
            self.cue_player.stop()
            self._reset_row_highlight(self._current_preview_row)
            self._current_preview_row = -1

        self.table.setRowCount(0)
        self.all_tracks = []
        self._current_playlist_path = None

        from services.db import get_db

        class LoadFolderWorker(QObject):
            finished = Signal(object)
            error = Signal(str)

            def __init__(self, folder_path, folder_name):
                super().__init__()
                self._folder_path = folder_path
                self._folder_name = folder_name

            def run(self):
                try:
                    db = get_db()
                    logger.debug(
                        f"[FAVORIT WORKER] Carregant tracks de: {self._folder_path}"
                    )
                    tracks = db.get_tracks_by_folder(self._folder_path, recursive=True)
                    logger.debug(f"[FAVORIT WORKER] Trobats {len(tracks)} tracks")
                    self.finished.emit((tracks, self._folder_name))
                except Exception as e:
                    logger.error(f"[FAVORIT WORKER] Error: {e}")
                    import traceback

                    traceback.print_exc()
                    self.error.emit(str(e))

        self._load_thread = QThread()
        self._load_worker = LoadFolderWorker(folder_path, folder_name)
        self._load_worker.moveToThread(self._load_thread)

        self._load_thread.started.connect(self._load_worker.run)
        self._load_worker.finished.connect(
            self._on_folder_loaded, Qt.ConnectionType.QueuedConnection
        )
        self._load_worker.error.connect(
            self._on_folder_load_error, Qt.ConnectionType.QueuedConnection
        )
        self._load_worker.finished.connect(self._load_thread.quit)
        self._load_worker.finished.connect(self._load_worker.deleteLater)
        self._load_thread.finished.connect(self._load_thread.deleteLater)

        self._load_thread.start()

    def _on_folder_loaded(self, result):
        """Callback quan els tracks del folder s'han carregat (executat al thread UI)."""
        if isinstance(result, tuple) and len(result) == 2:
            tracks, folder_name = result
        else:
            tracks = result
            folder_name = folder_name

        logger.debug(
            f"[FAVORIT UI] _on_folder_loaded: {len(tracks)} tracks, folder: {folder_name}"
        )

        self.all_tracks = tracks
        self.filtered_tracks = []
        self._current_page = 0

        if not tracks:
            self._update_source_label(f"📁 {folder_name} (buit)", "#888888")
            return

        self._update_source_label(f"📁 {folder_name} ({len(tracks)} tracks)", "#ff9800")
        self._update_genre_filter_from_all_tracks()
        self._apply_filters()

    def _on_folder_load_error(self, error_msg):
        """Callback cuando hay error al cargar folder."""
        logger.error(f"Error carregant carpeta: {error_msg}")
        self._update_source_label("📁 Error carregant", "#ff0000")
        QMessageBox.critical(self, "Error", f"Error carregant carpeta: {error_msg}")

    def load_from_favorites(self):
        """Carga todos los tracks de la base de datos en la segunda lista (async)."""
        if self.is_master:
            return

        self._db_cache = None

        self._update_source_label("📚 Carregant biblioteca...", "#00d4ff")
        self._current_source = "biblioteca"

        if self._current_preview_row >= 0:
            self.cue_player.stop()
            self._reset_row_highlight(self._current_preview_row)
            self._current_preview_row = -1

        self.table.setRowCount(0)
        self.all_tracks = []
        self._current_playlist_path = None

        from services.db import get_db

        class LoadTracksWorker(QObject):
            finished = Signal(list)
            error = Signal(str)

            def run(self):
                try:
                    db = get_db()
                    tracks = db.get_all_tracks()
                    self.finished.emit(tracks)
                except Exception as e:
                    self.error.emit(str(e))

        self._load_thread = QThread()
        self._load_worker = LoadTracksWorker()
        self._load_worker.moveToThread(self._load_thread)

        self._load_thread.started.connect(self._load_worker.run)
        self._load_worker.finished.connect(
            self._on_tracks_loaded, Qt.ConnectionType.QueuedConnection
        )
        self._load_worker.error.connect(
            self._on_tracks_load_error, Qt.ConnectionType.QueuedConnection
        )
        self._load_worker.finished.connect(self._load_thread.quit)
        self._load_worker.finished.connect(self._load_worker.deleteLater)
        self._load_thread.finished.connect(self._load_thread.deleteLater)

        self._load_thread.start()

    def _on_tracks_loaded(self, tracks):
        """Callback cuando los tracks se han cargado."""
        if not tracks:
            self._update_source_label("📚 Biblioteca buida", "#888888")
            QMessageBox.information(
                self,
                "Biblioteca buida",
                "No hi ha cançons analitzades a la base de dades.",
            )
            return

        import os

        if os.environ.get("JM_DEBUG"):
            tracks = tracks[:100]
            logger.debug(f"DEBUG: limitado a {len(tracks)} tracks")

        self.all_tracks = tracks

        self._update_source_label(f"📚 Biblioteca ({len(tracks)} tracks)", "#00d4ff")

        if tracks:
            logger.debug(f"Primer track keys: {list(tracks[0].keys())}")
            logger.debug(
                f"Géneros únicos encontrados: {len(set(t.get('genre', '') for t in tracks if t.get('genre', '')))}"
            )

        self._update_genre_filter_from_all_tracks()
        self._apply_filters()

    def _on_tracks_load_error(self, error_msg):
        """Callback cuando hay error al cargar tracks."""
        logger.error(f"Error carregant tracks: {error_msg}")
        self._update_source_label("📚 Error carregant", "#ff0000")
        QMessageBox.critical(self, "Error", f"Error carregant tracks: {error_msg}")
