import logging
import multiprocessing
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMainWindow,
    QMessageBox,
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import JM_MusicAnalizer

    APP_VERSION = getattr(JM_MusicAnalizer, "APP_VERSION", "4.43.0")

    if not APP_VERSION or APP_VERSION.startswith("${"):
        APP_VERSION = "4.43.0"
except (ImportError, ModuleNotFoundError):
    APP_VERSION = "4.43.0"

from app_state import AppState
from core.filter_criteria import FilterCriteria
from services.db import get_db
from services.metadata_service import MetadataService
from services.online_metadata_service import OnlineMetadataService
from services.settings_manager import SettingsManager
from ui.main_window_menu import MainWindowMenuMixin
from ui.main_window_metadata import MainWindowMetadataMixin
from ui.main_window_scan import MainWindowScanMixin
from ui.performance_window import PerformanceWindow

logger = logging.getLogger(__name__)


class MainWindow(
    MainWindowMenuMixin, MainWindowScanMixin, MainWindowMetadataMixin, QMainWindow
):
    def __init__(self):
        super().__init__()
        self._num_cores = max(2, multiprocessing.cpu_count() - 2)
        self.setWindowTitle(
            f"JM-MusicAnalyzer v{APP_VERSION} - Editor Mode ({self._num_cores} cores)"
        )
        self.setWindowIcon(QIcon("resources/icons/JM_MusicAnalyzer.ico"))
        self.resize(1100, 650)

        self.settings = SettingsManager()
        self.online_service = OnlineMetadataService()
        self._state = AppState()
        self._current_folder = None
        self.db_manager = get_db()
        self.metadata_service = MetadataService()
        self._perf_window = None
        self._last_scanned_paths = []
        self.worker = None
        self._pending_files = []
        self._batch_timer = QTimer()
        self._batch_timer.setInterval(80)
        self._batch_timer.timeout.connect(self._process_pending_files)

        self._main_playing_text = ""
        self._cue_text = ""

        self._setup_ui()
        self._setup_connections()

        # Defer loading tracks to after show() so window appears instantly
        QTimer.singleShot(0, self._load_initial_state)

    def _setup_connections(self):
        self.file_list.fileSelected.connect(self._on_file_selected)
        self.file_list.ratingChanged.connect(self._on_rating_changed)
        self.file_list.forceReadMetadataRequested.connect(self._on_force_read_metadata)
        self.file_list.batchGenreChangeRequested.connect(self._on_batch_genre_change)
        self.file_list.addToDjMaster.connect(self._on_add_to_dj_master)
        self.file_list.batchAddToDjMaster.connect(self._on_batch_add_to_dj_master)
        self.file_list.createPlaylistAndAdd.connect(self._create_playlist_and_add)
        self.file_list.fileDeleteRequested.connect(self._on_file_delete_requested)
        self.file_list.fileDeleted.connect(self._on_file_deleted)
        self.file_list.fileMoved.connect(self._on_file_moved)
        self.file_list.fileMoveRequested.connect(self._on_file_move_requested)
        self.file_list.fingerprintRequested.connect(self._on_fingerprint_requested)
        self.file_list.batchFingerprintRequested.connect(self._on_batch_fingerprint)

        self.player_widget.requestNext.connect(self._on_play_next_in_list)
        self.player_widget.requestPrev.connect(self._on_play_prev_in_list)
        self.player_widget.nowPlayingChanged.connect(self._on_player_now_playing)
        self.file_list.cuePreviewChanged.connect(self._on_cue_preview_changed)
        self.player_widget.requestDelete.connect(self._on_delete_current_file)

        self.metadata_panel.saveRequested.connect(self._on_save_metadata)
        self.metadata_panel.identifyRequested.connect(self._on_identify)
        self.metadata_panel.fingerprintRequested.connect(
            self._on_fingerprint_from_panel
        )
        self.metadata_panel.bookmarkSelected.connect(
            self._on_bookmark_selected_for_play
        )
        self.metadata_panel.addFolderRequested.connect(self._on_scan_folder)

        self.file_tree.folderClicked.connect(self._on_tree_folder_clicked)
        self.file_tree.rescanFolder.connect(self._on_rescan_folder)

        self.combo_genre.currentIndexChanged.connect(self._apply_filters)
        self.combo_rating.currentIndexChanged.connect(self._apply_filters)
        self.combo_bpm.currentIndexChanged.connect(self._apply_filters)
        self.search_field.returnPressed.connect(self._on_global_search_enter)

    def _load_initial_state(self):
        from services.bookmarks_manager import BookmarksManager

        bm = BookmarksManager()
        bookmarks = bm.load_bookmarks()
        if bookmarks:
            self.file_tree.load_favorites_tree(bookmarks)
        self._load_genre_combo()
        self._apply_filters()

    def _load_genre_combo(self):
        genres = self.db_manager.get_unique_genres()
        self.combo_genre.blockSignals(True)
        self.combo_genre.clear()
        self.combo_genre.addItem("Genero")
        self.combo_genre.addItem("(Sense genere)")
        for g in genres:
            if g and g != "-":
                self.combo_genre.addItem(g)
        self.combo_genre.blockSignals(False)

    def _on_bookmark_selected_for_play(self, path):
        if not path or not os.path.isdir(path):
            return
        tracks = self.db_manager.get_tracks_by_folder(path)
        self.file_list.load_tracks_from_db(tracks)
        self.file_tree.load_folder_tree(path)
        self.statusBar().showMessage(
            f"Carpeta: {os.path.basename(path)} ({len(tracks)} pistas)", 3000
        )

    def _apply_filters(self):
        self._current_folder = None
        genre = self.combo_genre.currentText()
        if genre == "Genero":
            genre = None
        elif genre == "(Sense genere)":
            genre = ""
        rating_text = self.combo_rating.currentText()
        min_rating = float(rating_text) if rating_text not in ("Rating", "") else 0.0

        bpm_min = bpm_max = None
        bpm_missing = False
        bpm_text = self.combo_bpm.currentText()
        if bpm_text == "Sense BPM":
            bpm_missing = True
        elif bpm_text.startswith("<"):
            bpm_min, bpm_max = None, int(bpm_text[1:]) - 1
        elif bpm_text.endswith("+"):
            bpm_min, bpm_max = int(bpm_text[:-1]), None
        elif "-" in bpm_text and bpm_text != "BPM":
            lo, hi = bpm_text.split("-")
            bpm_min, bpm_max = int(lo), int(hi)

        criteria = FilterCriteria(
            genre=genre,
            min_rating=min_rating,
            status=None,
            search=None,
            folder=None,
            limit=500,
            bpm_min=bpm_min,
            bpm_max=bpm_max,
            bpm_missing=bpm_missing,
        )

        tracks = self.db_manager.search_tracks_filtered(criteria)
        self.file_list.load_tracks_from_db(tracks)

    def _on_global_search_enter(self):
        query = self.search_field.text().strip()
        if len(query) < 2:
            return
        self._current_folder = None
        tracks = self.db_manager.search_tracks(query)
        self.file_list.load_tracks_from_db(tracks)
        self.statusBar().showMessage(f"Busqueda: {len(tracks)} resultados", 3000)

    def _on_search_reset(self):
        self._current_folder = None
        self.combo_genre.setCurrentIndex(0)
        self.combo_rating.setCurrentIndex(0)
        self.combo_bpm.setCurrentIndex(0)
        self.search_field.clear()
        self._apply_filters()

    def _on_tree_folder_clicked(self, path):
        if not path:
            return
        self._current_folder = path
        self.combo_genre.blockSignals(True)
        self.combo_genre.setCurrentIndex(0)
        self.combo_genre.blockSignals(False)
        self.combo_rating.setCurrentIndex(0)
        self.combo_bpm.setCurrentIndex(0)
        self.search_field.clear()
        tracks = self.db_manager.get_tracks_by_folder(path)
        self.file_list.load_tracks_from_db(tracks)
        self.statusBar().showMessage(
            f"Carpeta: {os.path.basename(path)} ({len(tracks)} pistas)", 3000
        )

    def _on_play_next_in_list(self):
        selected = self.file_list.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        next_row = row + 1
        if next_row < self.file_list.rowCount():
            self.file_list._suppress_selection_signal = True
            self.file_list.selectRow(next_row)
            self.file_list._suppress_selection_signal = False
            filepath = self.file_list._get_path_at_row(next_row)
            if filepath:
                self._on_file_selected(filepath, auto_play=True)

    def _on_player_now_playing(self, text):
        self._main_playing_text = text
        self._update_now_playing_label()

    def _on_cue_preview_changed(self, text):
        self._cue_text = text
        self._update_now_playing_label()

    def _update_now_playing_label(self):
        if self._cue_text:
            self.lbl_now_playing.setText(f"\U0001f3a7 {self._cue_text}")
            self.lbl_now_playing.setStyleSheet(
                "color: #ffa500; font-size: 11px; font-weight: bold; padding: 0 8px; border: none;"
            )
        elif self._main_playing_text:
            self.lbl_now_playing.setText(self._main_playing_text)
            self.lbl_now_playing.setStyleSheet(
                "color: #00d4ff; font-size: 11px; font-weight: bold; padding: 0 8px; border: none;"
            )
        else:
            self.lbl_now_playing.setText("")

    def _on_play_prev_in_list(self):
        selected = self.file_list.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        prev_row = row - 1
        if prev_row >= 0:
            self.file_list._suppress_selection_signal = True
            self.file_list.selectRow(prev_row)
            self.file_list._suppress_selection_signal = False
            filepath = self.file_list._get_path_at_row(prev_row)
            if filepath:
                self._on_file_selected(filepath, auto_play=True)

    def _on_delete_current_file(self):
        filepath = self._state.selected_filepath
        if filepath:
            self._on_file_delete_requested(filepath)

    def _ensure_dj_window(self):
        from ui.performance_window import PerformanceWindow

        if self._perf_window is None:
            self._perf_window = PerformanceWindow()
            self._perf_window.closed.connect(self._on_performance_closed)
        return self._perf_window

    def _on_add_to_dj_master(self, filepath):
        perf = self._ensure_dj_window()
        perf.playlist_widget.add_track(filepath, silent=True)
        self.statusBar().showMessage(
            f"Añadido a DJ Master: {os.path.basename(filepath)}", 3000
        )

    def _on_batch_add_to_dj_master(self, filepaths):
        perf = self._ensure_dj_window()
        for fp in filepaths:
            perf.playlist_widget.add_track(fp, silent=True)
        self.statusBar().showMessage(
            f"Añadidos {len(filepaths)} archivos a DJ Master", 3000
        )

    def _create_playlist_and_add(self, filepath):
        perf = self._ensure_dj_window()
        pw = perf.playlist_widget
        # Netejar playlist sense diàleg de confirmació
        if pw._current_preview_row >= 0:
            pw.cue_player.stop()
            pw._current_preview_row = -1
        pw.table.setRowCount(0)
        pw._modified = True
        pw.add_track(filepath, silent=True)
        self.statusBar().showMessage(
            f"Playlist creada con: {os.path.basename(filepath)}", 3000
        )

    def _on_switch_to_performance(self):
        if self._perf_window is None:
            try:
                self._perf_window = PerformanceWindow()
            except Exception as e:
                logger.error(f"Error creant PerformanceWindow: {e}")
                import traceback

                traceback.print_exc()
                self._perf_window = None
                return
            self._perf_window.closed.connect(self._on_performance_closed)
        try:
            self._perf_window.show()
            self._perf_window.raise_()
            self._perf_window.activateWindow()
        except RuntimeError:
            self._perf_window = None
            self._on_switch_to_performance()
            return
        self.hide()

    def _on_performance_closed(self):
        self._perf_window = None
        self.show()

    def _on_clear_database(self):
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Estás seguro de que quieres limpiar toda la base de datos?\n\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = get_db()
                db.clear_database()
                self.file_list.clear_all()
                self._load_genre_combo()
                self.statusBar().showMessage("Base de datos limpiada", 3000)
            except Exception as e:
                logger.error(f"Error clearing database: {e}")
                QMessageBox.critical(
                    self, "Error", f"No se pudo limpiar la base de datos:\n{e}"
                )

    def _on_optimize_database(self):
        try:
            self.statusBar().showMessage("Optimizando base de datos...", 0)
            QApplication.processEvents()
            db = get_db()
            result = db.optimize_database()
            if result["success"]:
                msg = "Base de datos optimizada correctamente.\n\n"
                msg += f"Tamaño: {result['size_mb']:.1f} MB\n"
                msg += f"Espacio liberado: {result['freed_mb']:.2f} MB"
                self.statusBar().showMessage(
                    f"BD optimizada: {result['freed_mb']:.2f} MB liberados", 3000
                )
                QMessageBox.information(self, "Optimización completada", msg)
            else:
                QMessageBox.critical(
                    self, "Error", "No se pudo optimizar la base de datos."
                )
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
            QMessageBox.critical(self, "Error", f"Error optimizando:\n{e}")

    def _on_delete_nonexistent_tracks(self):
        try:
            db = get_db()
            result = db.delete_nonexistent_tracks()
            deleted = result.get("deleted", 0)
            if deleted > 0:
                self._refresh_current_view()
                self._load_genre_combo()
            QMessageBox.information(
                self,
                "Limpieza completada",
                f"Se eliminaron {deleted} pistas inexistentes del disco de la base de datos.",
            )
        except Exception as e:
            logger.error(f"Error deleting nonexistent tracks: {e}")
            QMessageBox.critical(
                self, "Error", f"Error eliminando pistas inexistentes:\n{e}"
            )

    def _on_backup_database(self):
        try:
            db = get_db()
            result = db.backup_database()
            if "error" in result:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo crear la copia de seguridad:\n{result['error']}",
                )
            else:
                QMessageBox.information(
                    self,
                    "Copia de Seguridad",
                    f"Copia creada correctamente.\n\n"
                    f"Archivo: {os.path.basename(result['path'])}\n"
                    f"Tamaño: {result['size_mb']:.2f} MB",
                )
        except Exception as e:
            logger.error(f"Error en backup: {e}")
            QMessageBox.critical(
                self, "Error", f"Error creando copia de seguridad:\n{e}"
            )

    def _on_restore_database(self):
        try:
            db = get_db()
            backups = db.get_backups()
            if not backups:
                QMessageBox.information(
                    self, "Restaurar", "No hay copias de seguridad disponibles."
                )
                return

            items = []
            for b in backups:
                date_fmt = f"{b['date'][:4]}-{b['date'][4:6]}-{b['date'][6:8]} {b['date'][9:11]}:{b['date'][11:13]}:{b['date'][13:15]}"
                items.append(f"{date_fmt}  ({b['size_mb']:.2f} MB)")

            choice, ok = QInputDialog.getItem(
                self,
                "Restaurar Copia de Seguridad",
                "Selecciona la copia a restaurar:\n\n⚠️ Se reemplazará la base de datos actual.",
                items,
                0,
                False,
            )
            if not ok or not choice:
                return

            idx = items.index(choice)
            backup = backups[idx]

            reply = QMessageBox.warning(
                self,
                "Confirmar Restauración",
                f"¿Restaurar la copia del {choice}?\n\n"
                f"⚠️ La base de datos actual se reemplazará.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            if db.restore_database(backup["path"]):
                self.file_list.clear_all()
                self._refresh_current_view()
                self._load_genre_combo()
                QMessageBox.information(
                    self,
                    "Restauración completada",
                    "Base de datos restaurada correctamente.",
                )
            else:
                QMessageBox.critical(
                    self, "Error", "No se pudo restaurar la copia de seguridad."
                )
        except Exception as e:
            logger.error(f"Error restaurando backup: {e}")
            QMessageBox.critical(
                self, "Error", f"Error restaurando copia de seguridad:\n{e}"
            )

    def _on_rebuild_database(self):
        reply = QMessageBox.question(
            self,
            "Reconstruir Base de Datos",
            "¿Re-escanear pistas con metadatos incompletos?\n\n"
            "Esto volverá a leer los archivos que tengan datos vacíos\n"
            "(título, artista, duración o bitrate).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.statusBar().showMessage("Reconstruyendo base de datos...", 0)
            QApplication.processEvents()

            db = get_db()
            result = db.rebuild_database()

            if result["total"] == 0:
                self.statusBar().showMessage(
                    "No hay pistas con datos incompletos", 3000
                )
                return

            self._refresh_current_view()

            msg = f"Reconstruidas: {result['rebuilt']} de {result['total']} pistas"
            if result["errors"]:
                msg += f"\n\nErrores: {len(result['errors'])}"
                if len(result["errors"]) <= 5:
                    for err in result["errors"]:
                        msg += f"\n  • {err}"
                else:
                    for err in result["errors"][:5]:
                        msg += f"\n  • {err}"
                    msg += f"\n  ... y {len(result['errors']) - 5} más"

            self.statusBar().showMessage(
                f"Reconstrucción completada: {result['rebuilt']}/{result['total']}",
                5000,
            )
            QMessageBox.information(self, "Reconstrucción completada", msg)
        except Exception as e:
            logger.error(f"Error en rebuild: {e}")
            QMessageBox.critical(
                self, "Error", f"Error reconstruyendo base de datos:\n{e}"
            )

    def _on_cue_vol_changed(self, value):
        if hasattr(self.file_list, "_cue_player") and self.file_list._cue_player:
            self.file_list._cue_player.setVolume(value / 100.0)

    def closeEvent(self, event):
        logger.info("Cerrando aplicación...")

        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            logger.info("Deteniendo worker de análisis...")
            self.worker.stop()
            self.worker.wait(3000)
            if self.worker.isRunning():
                self.worker.terminate()

        if hasattr(self, "player_widget"):
            self.player_widget.stop()

        if hasattr(self, "_perf_window") and self._perf_window:
            try:
                self._perf_window.close()
            except Exception:
                pass

        event.accept()
        logger.info("Aplicación cerrada.")
