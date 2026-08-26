import logging
import os
import shutil

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import (
    QMenu,
)

logger = logging.getLogger(__name__)


class FileListActionsMixin:
    """Context menus, file operations (delete, move, open), metadata panel."""

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return

        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            selected_rows = [item.row()]

        filepaths = []
        for row_ref in selected_rows:
            row = row_ref.row() if hasattr(row_ref, "row") else row_ref
            fp = self._get_path_at_row(row)
            if fp:
                filepaths.append((row, fp))

        if not filepaths:
            return

        is_multi = len(filepaths) > 1
        first_filepath = filepaths[0][1]

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #0078d4; }"
        )

        if is_multi:
            menu.addAction(
                f"🗑 Eliminar {len(filepaths)} archivos de Disco..."
            ).triggered.connect(lambda: self._delete_files_confirm(filepaths))
            menu.addSeparator()
            menu.addAction("📋 Copiar Rutas al Portapapeles").triggered.connect(
                lambda: self._copy_paths_to_clipboard([fp for _, fp in filepaths])
            )
            menu.addSeparator()

            genre_act = QAction("🏷️ Cambiar Género...", self)
            genre_act.triggered.connect(
                lambda: self.batchGenreChangeRequested.emit([fp for _, fp in filepaths])
            )
            menu.addAction(genre_act)

            add_to_playlist_act = QAction("🎧 Añadir a Master Playlist (DJ)", self)
            add_to_playlist_act.triggered.connect(
                lambda: self.batchAddToDjMaster.emit([fp for _, fp in filepaths])
            )
            menu.addAction(add_to_playlist_act)

            menu.addSeparator()

            fp_act = QAction("🎵 Identificar por Fingerprint (selección)", self)
            fp_act.triggered.connect(
                lambda: self.batchFingerprintRequested.emit([fp for _, fp in filepaths])
            )
            menu.addAction(fp_act)
        else:
            open_folder_act = QAction("📂 Abrir en Explorador", self)
            open_folder_act.triggered.connect(
                lambda: os.startfile(os.path.dirname(first_filepath))
            )

            copy_path_act = QAction("📋 Copiar Ruta", self)
            copy_path_act.triggered.connect(
                lambda: self._copy_to_clipboard(first_filepath)
            )

            copy_file_act = QAction("📑 Duplicar Archivo", self)
            copy_file_act.triggered.connect(
                lambda: self._copy_file_physical(first_filepath)
            )

            copy_to_folder_act = QAction("📋 Copiar a Carpeta...", self)
            copy_to_folder_act.triggered.connect(
                lambda: self._copy_to_folder_dialog(first_filepath)
            )

            menu.addSeparator()

            move_act = QAction("🚚 Mover Archivo...", self)
            move_act.triggered.connect(
                lambda: self._move_file_dialog(first_filepath, filepaths[0][0])
            )

            delete_act = QAction("🗑 Eliminar de Disco", self)
            delete_act.triggered.connect(
                lambda: self._delete_file_confirm(first_filepath, filepaths[0][0])
            )

            menu.addAction(open_folder_act)
            menu.addAction(copy_path_act)

            force_meta_act = QAction("🔄 Forçar Lectura Metadades", self)
            force_meta_act.triggered.connect(
                lambda: self.forceReadMetadataRequested.emit(first_filepath)
            )
            menu.addAction(force_meta_act)

            fingerprint_act = QAction("🎵 Identificar por Fingerprint", self)
            fingerprint_act.triggered.connect(
                lambda: self.fingerprintRequested.emit(first_filepath)
            )
            menu.addAction(fingerprint_act)

            playlist_menu = QMenu("➕ Añadir a Playlist", menu)
            playlist_menu.setStyleSheet(
                "QMenu { background-color: #333; color: white; } QMenu::item:selected { background-color: #0078d4; }"
            )

            add_to_dj_master = QAction("🎧 Añadir a Master Playlist (DJ)", self)
            add_to_dj_master.triggered.connect(
                lambda: self._add_to_dj_master(first_filepath)
            )

            create_playlist = QAction("📁 Crear nueva playlist...", self)
            create_playlist.triggered.connect(
                lambda: self._create_new_playlist(first_filepath)
            )

            playlist_menu.addAction(add_to_dj_master)
            playlist_menu.addAction(create_playlist)

            menu.addMenu(playlist_menu)

            menu.addAction(copy_file_act)
            menu.addSeparator()
            menu.addAction(move_act)
            menu.addAction(delete_act)

        menu.exec(self.viewport().mapToGlobal(pos))

    def _copy_paths_to_clipboard(self, paths):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText("\n".join(paths))

    def _delete_files_confirm(self, filepaths_with_rows):
        from PySide6.QtWidgets import QMessageBox

        count = len(filepaths_with_rows)
        file_list = "\n".join(
            f"• {os.path.basename(fp)}" for _, fp in filepaths_with_rows[:15]
        )
        if count > 15:
            file_list += f"\n... y {count - 15} más"

        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar {count} archivos del disco?\n\n{file_list}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._delete_files_batch(filepaths_with_rows)

    def _delete_files_batch(self, filepaths_with_rows):
        import time

        from PySide6.QtWidgets import QMessageBox, QProgressDialog

        total = len(filepaths_with_rows)
        progress = QProgressDialog("Eliminando archivos...", "Cancelar", 0, total, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        deleted = 0
        errors = []
        in_use = []

        for i, (row, filepath) in enumerate(filepaths_with_rows):
            if progress.wasCanceled():
                break
            progress.setValue(i)

            try:
                self.fileDeleteRequested.emit(filepath)
                max_attempts = 3
                success = False
                for attempt in range(max_attempts):
                    try:
                        os.remove(filepath)
                        success = True
                        break
                    except PermissionError:
                        if attempt < max_attempts - 1:
                            time.sleep(0.5)
                        else:
                            in_use.append(os.path.basename(filepath))
                            continue

                if success:
                    self._added_paths.discard(filepath)
                    self.fileDeleted.emit(filepath)
                    deleted += 1
            except Exception as e:
                errors.append(f"{os.path.basename(filepath)}: {e}")

        progress.setValue(total)

        msg = f"Eliminados: {deleted}/{total}"
        if in_use:
            msg += f"\n\nEn uso ({len(in_use)}):\n" + "\n".join(
                f"• {n}" for n in in_use[:10]
            )
        if errors:
            msg += f"\n\nErrores ({len(errors)}):\n" + "\n".join(
                f"• {e}" for e in errors[:10]
            )

        QMessageBox.information(self, "Eliminación completada", msg)

        for row, fp in reversed(filepaths_with_rows):
            if fp not in self._added_paths:
                try:
                    self.removeRow(row)
                except Exception:
                    pass

    def _add_to_playlist(self, filepath):
        self.addToPlaylist.emit(filepath)

    def _add_to_current_list(self, filepath):
        self.addToCurrentList.emit(filepath)

    def _add_to_dj_master(self, filepath):
        self.addToDjMaster.emit(filepath)

    def _create_new_playlist(self, filepath):
        self.createPlaylistAndAdd.emit(filepath)

    def _copy_file_physical(self, filepath):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        filename = os.path.basename(filepath)
        current_dir = os.path.dirname(filepath)
        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar copia como...",
            os.path.join(current_dir, filename),
            "Audio (*.mp3)",
        )
        if dest_path:
            try:
                shutil.copy2(filepath, dest_path)
                QMessageBox.information(self, "Éxito", "Copia creada correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo copiar: {e}")

    def _copy_to_folder_dialog(self, filepath):
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        from services.settings_manager import SettingsManager

        current_dir = os.path.dirname(filepath)
        settings = SettingsManager()
        recent_paths = settings.get_recent_move_paths()

        menu = QMenu(self)

        browse_action = QAction("📂 Elegir carpeta...", self)
        browse_action.triggered.connect(lambda: self._do_copy_to_folder(filepath, None))
        menu.addAction(browse_action)

        menu.addSeparator()
        menu.addAction("📌 Destinos recientes:") if recent_paths else menu.addAction(
            "📌 Sin destinos recientes"
        )

        for path in recent_paths[:10]:
            if os.path.exists(path):
                action = QAction(os.path.basename(path) or path, self)
                action.triggered.connect(
                    lambda checked, p=path: self._do_copy_to_folder(filepath, p)
                )
                menu.addAction(action)

        if recent_paths:
            existing = [p for p in recent_paths[:10] if os.path.exists(p)]
            if not existing:
                menu.addAction("  (ninguna carpeta existe)")

        menu.exec(QCursor.pos())

    def _do_copy_to_folder(self, filepath, selected_dir):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from services.settings_manager import SettingsManager

        if not selected_dir:
            selected_dir = QFileDialog.getExistingDirectory(
                self, "Seleccionar destino", os.path.dirname(filepath)
            )
            if not selected_dir:
                return

        settings = SettingsManager()
        settings.add_recent_move_path(selected_dir)

        filename = os.path.basename(filepath)
        dest_path = os.path.join(selected_dir, filename)

        if os.path.exists(dest_path):
            reply = QMessageBox.question(
                self,
                "Archivo existente",
                "El archivo ya existe en esa carpeta.\n\n¿Sobrescribir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            shutil.copy2(filepath, dest_path)
            QMessageBox.information(
                self, "Éxito", f"Archivo copiado a:\n{selected_dir}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo copiar: {e}")

    def _copy_to_clipboard(self, text):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(text)

    def _delete_file_confirm(self, filepath, row):
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar este archivo?\n\n{filepath}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.fileDeleteRequested.emit(filepath)

            import time

            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    os.remove(filepath)
                    self.removeRow(row)
                    self._added_paths.discard(filepath)
                    self.fileDeleted.emit(filepath)
                    return
                except PermissionError:
                    if attempt < max_attempts - 1:
                        time.sleep(0.5)
                    else:
                        QMessageBox.warning(
                            self,
                            "Archivo en uso",
                            "No se pudo eliminar porque el archivo está siendo usado por otro proceso.\n\n"
                            "Cierra cualquier aplicación que esté usando el archivo (reproductor, etc.) e intenta de nuevo.",
                        )
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")
                    return

    def _move_file_dialog(self, filepath, row):
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        from services.settings_manager import SettingsManager

        current_dir = os.path.dirname(filepath)
        settings = SettingsManager()
        recent_paths = settings.get_recent_move_paths()

        menu = QMenu(self)

        browse_action = QAction("📂 Elegir carpeta...", self)
        browse_action.triggered.connect(lambda: self._do_move_file(filepath, row, None))
        menu.addAction(browse_action)

        menu.addSeparator()
        menu.addAction(
            "📌 Destinos recientes (sin historial)"
        ) if not recent_paths else menu.addAction("📌 Destinos recientes:")

        for path in recent_paths[:10]:
            if os.path.exists(path):
                action = QAction(os.path.basename(path) or path, self)
                action.triggered.connect(
                    lambda checked, p=path: self._do_move_file(filepath, row, p)
                )
                menu.addAction(action)

        if recent_paths:
            existing = [p for p in recent_paths[:10] if os.path.exists(p)]
            if not existing:
                menu.addAction("  (ninguna carpeta existe)")

        menu.exec(QCursor.pos())

    def _do_move_file(self, filepath, row, selected_dir):
        self.fileMoveRequested.emit(filepath)

        if not selected_dir:
            from PySide6.QtWidgets import QFileDialog, QMessageBox

            selected_dir = QFileDialog.getExistingDirectory(
                self, "Seleccionar destino", os.path.dirname(filepath)
            )
            if not selected_dir:
                return

        new_path = os.path.join(selected_dir, os.path.basename(filepath))
        try:
            shutil.move(filepath, new_path)

            self.removeRow(row)
            self._added_paths.discard(filepath)
            self.fileMoved.emit(filepath, new_path)

            from services.settings_manager import SettingsManager

            settings = SettingsManager()
            settings.add_recent_move_path(selected_dir)

            QMessageBox.information(self, "Éxito", "Archivo movido correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo mover: {e}")

    def _toggle_cue_preview(self, filepath):
        if self._current_preview_path == filepath:
            self._stop_cue_preview()
            return
        self._stop_cue_preview()
        self._current_preview_path = filepath
        btn = self._cue_buttons.get(filepath)
        self._cue_player.setSource(filepath)
        self._cue_player.play()
        if btn:
            btn.setText("■")
            btn.setStyleSheet("QPushButton { color: #ff4444; }")
        text = self._get_display_for_filepath(filepath)
        self.cuePreviewChanged.emit(text)

    def _stop_cue_preview(self):
        if self._current_preview_path:
            old_btn = self._cue_buttons.get(self._current_preview_path)
            if old_btn:
                old_btn.setText("🎧")
                old_btn.setStyleSheet("")
        self._cue_player.stop()
        self._current_preview_path = None
        self.cuePreviewChanged.emit("")

    def _on_cue_state_changed(self, state):
        if state == 0 and self._current_preview_path:
            btn = self._cue_buttons.get(self._current_preview_path)
            if btn:
                btn.setText("🎧")
                btn.setStyleSheet("")
            self._current_preview_path = None
            self.cuePreviewChanged.emit("")

    def _get_display_for_filepath(self, filepath):
        for row in range(self.rowCount()):
            if self._get_path_at_row(row) == filepath:
                artist = self.item(row, 1)
                title = self.item(row, 2)
                if artist and title and artist.text() and title.text():
                    return f"{artist.text()} - {title.text()}"
                return os.path.basename(filepath)
        return os.path.basename(filepath)

    def _on_selection_changed(self):
        if self._suppress_selection_signal:
            return

        selected_rows = self.selectionModel().selectedRows()
        logger.debug(f"[SELECCIO] Files seleccionades: {len(selected_rows)}")

        if not selected_rows:
            return

        row = selected_rows[0].row()

        if row < 0 or row >= self.rowCount():
            logger.warning(
                f"[SELECCIO] Fila {row} fora de rang (total: {self.rowCount()})"
            )
            return

        filepath = self._get_path_at_row(row)
        logger.debug(f"[SELECCIO] Fila {row}: filepath={filepath}")

        if filepath:
            if self.isVisible() and self.isEnabled():
                from PySide6.QtCore import QTimer

                QTimer.singleShot(0, lambda fp=filepath: self._emit_file_selected(fp))
            else:
                logger.debug(
                    "[SELECCIO] Widget no visible/deshabilitat, retardant emissió"
                )
        else:
            logger.warning(f"[SELECCIO] No s'ha trobat filepath a la fila {row}")

    def _emit_file_selected(self, filepath):
        logger.debug(f"[SELECCIO] Emetent fileSelected: {filepath}")
        self.fileSelected.emit(filepath)

    def _on_rating_changed(self, filepath, rating):
        if filepath in self._rating_widgets:
            self._rating_widgets[filepath].set_rating(rating)
        for row in range(self.rowCount()):
            filepath_item = self.item(row, 7)
            if filepath_item:
                fp = (
                    filepath_item.data(Qt.ItemDataRole.UserRole) or filepath_item.text()
                )
                if fp == filepath:
                    rating_item = self.item(row, 4)
                    if rating_item:
                        rating_item.setData(Qt.ItemDataRole.UserRole, rating)
                    break
        self.ratingChanged.emit(filepath, rating)
