import logging
import os

from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
)
from services.db import get_db
from workers.analyze_worker import AnalyzeWorker

logger = logging.getLogger(__name__)


class MainWindowScanMixin:
    def _on_scan_folder(self, recursive=True):
        from PySide6.QtWidgets import QFileDialog

        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if path:
            self._last_scanned_paths = [path]
            self.start_batch_analysis([path], recursive=recursive)

    def _on_rescan_folder(self, path, recursive=True):
        if not path or not os.path.isdir(path):
            return
        self._last_scanned_paths = [path]
        self.start_batch_analysis([path], recursive=recursive)

    def start_batch_analysis(self, paths, recursive=True):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
            if self.worker.isRunning():
                self.worker.terminate()

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.statusBar().showMessage(f"Escaneando {len(paths)} carpeta(s)...")

        self.worker = AnalyzeWorker(paths, recursive=recursive)
        self.worker.total_files.connect(self._on_total_files)
        self.worker.file_started.connect(self._on_file_started)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.scan_progress.connect(self._on_scan_progress)
        self.worker.all_finished.connect(self._on_scan_finished_batch)
        self.worker.error.connect(self._on_scan_error)
        self.worker.new_files_detected.connect(self._on_new_files_detected)
        self.worker.start()

    def _on_total_files(self, count):
        self.progress_bar.setMaximum(count)
        self.statusBar().showMessage(f"Analizando {count} archivos...")

    def _on_file_started(self, filepath, idx):
        self._pending_files.append(filepath)
        if not self._batch_timer.isActive():
            self._batch_timer.start()

    def _process_pending_files(self):
        if not self._pending_files:
            self._batch_timer.stop()
            return
        batch = self._pending_files[:50]
        self._pending_files = self._pending_files[50:]
        self.file_list.setUpdatesEnabled(False)
        for fp in batch:
            self.file_list.add_file_row(fp)
        self.file_list.setUpdatesEnabled(True)
        if self._pending_files:
            self._batch_timer.start()
        else:
            self._batch_timer.stop()

    def _on_file_finished(self, music_file, idx):
        if music_file and not music_file.error:
            self._update_row_in_grid(music_file)
        n = idx + 1
        self.progress_bar.setValue(n)
        self.statusBar().showMessage(
            f"Progreso: {n}/{self.progress_bar.maximum()} archivos"
        )

    def _on_scan_progress(self, processed, total):
        self.progress_bar.setValue(processed)
        self.statusBar().showMessage(f"Progreso: {processed}/{total} archivos")

    def _on_scan_finished_batch(self):
        self._batch_timer.stop()
        self._process_pending_files()
        self.progress_bar.setVisible(False)
        # Mantenir visible la carpeta que s'estava escanejant (p.ex. la de
        # descàrrega de YouTube): _apply_filters canvia a la llista global.
        folder = self._current_folder or (self._last_scanned_paths or [None])[0]
        self.statusBar().showMessage("Analisis completado", 3000)
        self._load_genre_combo()
        self._apply_filters()
        if folder:
            tracks = self.db_manager.get_tracks_by_folder(folder)
            self.file_list.load_tracks_from_db(tracks)
        result = self.db_manager.auto_optimize_if_needed()
        if result:
            logger.info(f"Auto-optimizacion: {result}")

    def _on_scan_error(self, msg):
        logger.error(f"Error en analisis: {msg}")
        self.statusBar().showMessage(f"Error: {msg}", 5000)

    def _on_new_files_detected(self, new_files):
        count = len(new_files)
        if not count:
            return
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Archivos nuevos: {count}")
        dlg.resize(800, 420)
        layout = QVBoxLayout(dlg)

        header = QLabel(
            f'<b style="font-size:14px">{count} archivo(s) nuevo(s) detectado(s)</b>'
        )
        header.setStyleSheet("padding: 4px 0;")
        layout.addWidget(header)

        folders = sorted(set(f["folder"] for f in new_files if f.get("folder")))
        if folders:
            folders_str = ", ".join(folders)
            layout.addWidget(QLabel(f"\U0001f4c1 {folders_str}"))

        table = QTableWidget(count, 5)
        table.setHorizontalHeaderLabels(["Título", "Artista", "Género", "Carpeta", ""])
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(4, 70)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        for i, f in enumerate(new_files):
            title = (
                f.get("title")
                or os.path.splitext(os.path.basename(f.get("filepath", "")))[0]
            )
            table.setItem(i, 0, QTableWidgetItem(title))
            table.setItem(i, 1, QTableWidgetItem(f.get("artist") or "?"))
            table.setItem(i, 2, QTableWidgetItem(f.get("genre") or "?"))
            table.setItem(i, 3, QTableWidgetItem(f.get("folder") or "?"))

            row_widget = QWidget()
            row_lay = QHBoxLayout(row_widget)
            row_lay.setContentsMargins(2, 1, 2, 1)
            row_lay.setSpacing(2)
            btn_edit = QPushButton("✏️")
            btn_edit.setFixedSize(30, 22)
            btn_edit.setToolTip("Editar etiquetas básicas")
            btn_edit.clicked.connect(
                lambda checked=False, fp=f.get("filepath", ""), row=i: self._edit_new_file(fp, row, table)
            )
            btn_fp = QPushButton("🔍")
            btn_fp.setFixedSize(30, 22)
            btn_fp.setToolTip("Buscar en MusicBrainz (fingerprint)")
            btn_fp.clicked.connect(
                lambda checked=False, fp=f.get("filepath", ""), row=i: self._fingerprint_new_file(fp, row, table)
            )
            row_lay.addWidget(btn_edit)
            row_lay.addWidget(btn_fp)
            table.setCellWidget(i, 4, row_widget)

        layout.addWidget(table)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.setFixedWidth(80)
        btn_ok.clicked.connect(dlg.accept)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)
        dlg.exec()

    def _edit_new_file(self, filepath, row, table):
        """Obre l'editor d'etiquetes bàsiques per un fitxer acabat de baixar."""
        if not filepath or not os.path.exists(filepath):
            return
        from services.db import get_db
        from services.metadata_service import MetadataService
        from ui.dialogs.track_edit_dialog import TrackEditDialog

        try:
            from core.reader.mp3_reader import MP3Reader

            music_file = MP3Reader(filepath).read(use_cache=True, save_db=False)
            meta = music_file.metadata if music_file and music_file.metadata else None
        except Exception:
            meta = None

        dlg = TrackEditDialog(
            (meta.artist if meta and meta.artist else "") or "",
            (meta.title if meta and meta.title else "") or "",
            (meta.genre if meta and meta.genre else "") or "",
            (meta.rating if meta and meta.rating else 0) or 0,
            get_db(),
            self,
        )
        if dlg.exec() != 1:
            return

        MetadataService().save_from_panel(filepath, dlg.get_data())
        self._refresh_dialog_row(table, row, filepath)
        self._refresh_current_view()
        self.statusBar().showMessage(
            f"Metadatos guardados: {os.path.basename(filepath)}", 3000
        )

    def _fingerprint_new_file(self, filepath, row, table):
        """Cerca MusicBrainz/AcoustID per un fitxer acabat de baixar."""
        if not filepath or not os.path.exists(filepath):
            return
        self._on_fingerprint_requested(filepath)
        self._refresh_dialog_row(table, row, filepath)

    def _refresh_dialog_row(self, table, row, filepath):
        try:
            from core.reader.mp3_reader import MP3Reader

            music_file = MP3Reader(filepath).read(use_cache=True, save_db=False)
            meta = music_file.metadata if music_file and music_file.metadata else None
        except Exception:
            meta = None
        title = meta.title if meta and meta.title else os.path.basename(filepath)
        artist = meta.artist if meta and meta.artist else "?"
        genre = meta.genre if meta and meta.genre else "?"
        if table.item(row, 0):
            table.item(row, 0).setText(title)
        if table.item(row, 1):
            table.item(row, 1).setText(artist)
        if table.item(row, 2):
            table.item(row, 2).setText(genre)

    def _on_quick_scan(self):
        from services.bookmarks_manager import BookmarksManager
        from ui.dialogs.quick_scan_dialog import QuickScanDialog

        bm = BookmarksManager()
        favs = bm.load_bookmarks()

        if not favs:
            QMessageBox.information(
                self,
                "Sin Favoritos",
                "No hay carpetas en favoritos.\nAñade carpetas a favoritos primero.",
            )
            return

        dlg = QuickScanDialog(favs, self)
        if dlg.exec() != QDialog.Accepted:
            return

        if dlg.is_scan_all():
            paths = dlg.get_all_paths()
            self.statusBar().showMessage(
                f"Escaneo rápido de {len(paths)} carpetas...", 3000
            )
            self.start_batch_analysis(paths)
        else:
            selected_path = dlg.get_selected_path()
            if selected_path and os.path.exists(selected_path):
                self.statusBar().showMessage(
                    f"Escaneo rápido de {os.path.basename(selected_path)}...", 3000
                )
                self.start_batch_analysis([selected_path], recursive=True)
            else:
                QMessageBox.warning(
                    self, "Error", f"La carpeta no existe:\n{selected_path}"
                )

    def _on_show_duplicates(self):
        try:
            from ui.dialogs.duplicate_dialog import DuplicateDialog

            db = get_db()
            rows = db.get_all_tracks()
            if not rows:
                QMessageBox.information(
                    self, "Duplicados", "No hay archivos en la base de datos."
                )
                return

            analyzed = {}
            for row in rows:
                fp = row.get("filepath", "")
                if fp:
                    analyzed[fp] = row

            dlg = DuplicateDialog(analyzed, self)
            dlg.setWindowTitle("\U0001f50d Archivos Duplicados")
            dlg.exec()
        except Exception as e:
            logger.error(f"Error showing duplicates: {e}")

    def _on_duplicates_in_all_favorites(self):
        try:
            from services.bookmarks_manager import BookmarksManager
            from ui.dialogs.duplicate_dialog import DuplicateDialog

            bm = BookmarksManager()
            bookmarks = bm.load_bookmarks()
            if not bookmarks:
                QMessageBox.information(
                    self, "Sin Favoritos", "No hay carpetas en favoritos."
                )
                return

            fav_paths = set()
            for b in bookmarks:
                p = b.get("path", b) if isinstance(b, dict) else b
                fav_paths.add(os.path.normpath(p).lower())

            db = get_db()
            rows = db.get_all_tracks()
            if not rows:
                QMessageBox.information(
                    self,
                    "Duplicados en Favoritos",
                    "No hay archivos en la base de datos.",
                )
                return

            analyzed = {}
            for row in rows:
                fp = row.get("filepath", "")
                if fp and any(
                    os.path.normpath(fp).lower().startswith(fp_fav)
                    for fp_fav in fav_paths
                ):
                    analyzed[fp] = row

            if not analyzed:
                QMessageBox.information(
                    self,
                    "Duplicados en Favoritos",
                    "No se encontraron archivos en carpetas favoritas.",
                )
                return

            dlg = DuplicateDialog(analyzed, self)
            dlg.setWindowTitle("\U0001f50d Duplicados en Favoritos")
            dlg.exec()
        except Exception as e:
            logger.error(f"Error showing duplicates in favorites: {e}")

    def _on_show_low_quality(self):
        from ui.dialogs.tracks_inspector_dialog import TracksInspectorDialog

        tracks = self.db_manager.get_low_quality_tracks(128)
        dlg = TracksInspectorDialog(
            self,
            "Pistas de Baja Calidad",
            "\u26a0\ufe0f",
            tracks,
            TracksInspectorDialog.MODE_LOW_QUALITY,
            self.db_manager,
        )
        dlg.exec()

    def _on_show_corrupted(self):
        from ui.dialogs.tracks_inspector_dialog import TracksInspectorDialog

        tracks = self.db_manager.get_corrupted_tracks()
        dlg = TracksInspectorDialog(
            self,
            "Pistas Corruptas",
            "\u274c",
            tracks,
            TracksInspectorDialog.MODE_CORRUPTED,
            self.db_manager,
        )
        dlg.exec()
