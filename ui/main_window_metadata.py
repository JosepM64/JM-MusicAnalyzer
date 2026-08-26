import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QInputDialog,
    QMessageBox,
)
from core.models import MetadataInfo, MusicFile
from core.reader.mp3_reader import MP3Reader
from ui.dialogs.metadata_comparison_dialog import MetadataComparisonDialog

logger = logging.getLogger(__name__)


class MainWindowMetadataMixin:
    def _on_file_selected(self, filepath, auto_play: bool = False):
        if not filepath:
            return
        self._state.selected_filepath = filepath

        self.player_widget.load_file(filepath, auto_play=auto_play)

        try:
            reader = MP3Reader(filepath)
            music_file = reader.read(use_cache=True, save_db=False)
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            music_file = None

        if music_file:
            if music_file.metadata:
                self.metadata_panel.update_data(music_file.metadata, filepath)
                self.metadata_panel.set_filepath(filepath)
                count = len(self.file_list.selectionModel().selectedRows())
                self.metadata_panel.set_batch_count(count)
            if music_file.technical:
                self.technical_panel.update_data(music_file.technical)
            if music_file.metadata and music_file.metadata.cover_data:
                self.cover_widget.set_cover(
                    music_file.metadata.cover_data,
                    music_file.metadata.cover_mime or "image/jpeg",
                )
            else:
                self.cover_widget.clear()
        else:
            self.metadata_panel.clear()
            self.technical_panel.clear()
            self.cover_widget.clear()

    def _on_rating_changed(self, filepath, rating):
        try:
            self.metadata_service.save_rating(filepath, rating)
            self._update_row_in_grid(
                self._make_music_file_stub(filepath, rating=rating)
            )
        except Exception as e:
            logger.error(f"Error guardando rating: {e}")
            QMessageBox.warning(self, "Error", f"No se pudo guardar el rating:\n{e}")

    def _make_music_file_stub(self, filepath, **kwargs):
        mf = MusicFile(filepath)
        if "rating" in kwargs:
            if mf.metadata is None:
                from core.models import MetadataInfo

                mf.metadata = MetadataInfo()
            mf.metadata.rating = kwargs["rating"]
        return mf

    def _on_force_read_metadata(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return
        try:
            if hasattr(self, "player_widget"):
                self.player_widget.stop()
            reader = MP3Reader(filepath)
            music_file = reader.read(use_cache=False, save_db=True)
            self._update_row_in_grid(music_file)
            if filepath == self._state.selected_filepath:
                self._on_file_selected(filepath)
            self.statusBar().showMessage(
                f"Metadata forzada: {os.path.basename(filepath)}", 3000
            )
        except Exception as e:
            logger.error(f"Error forzando lectura: {e}")
            QMessageBox.warning(self, "Error", f"Error leyendo metadata:\n{e}")

    def _on_force_read_selected(self):
        filepath = self._state.selected_filepath
        if filepath:
            self._on_force_read_metadata(filepath)

    def _on_batch_genre_change(self, filepaths):
        if not filepaths:
            return
        genres = self.db_manager.get_unique_genres()
        genre, ok = QInputDialog.getItem(
            self,
            "Cambiar Genero",
            f"Seleccionar genero para {len(filepaths)} archivos:",
            [g for g in genres if g and g != "-"] + ["Otro..."],
            0,
            False,
        )
        if not ok or not genre:
            return
        if genre == "Otro...":
            genre, ok = QInputDialog.getText(self, "Nuevo Genero", "Genero:")
            if not ok or not genre:
                return
        try:
            self.metadata_service.batch_update_field(filepaths, genre=genre)
            self._refresh_current_view()
            self.statusBar().showMessage(
                f"Genero cambiado a '{genre}' para {len(filepaths)} archivos", 3000
            )
        except Exception as e:
            logger.error(f"Error cambiando genero: {e}")
            QMessageBox.warning(self, "Error", f"No se pudo cambiar el genero:\n{e}")

    def _get_selected_filepaths(self):
        selection = self.file_list.selectionModel().selectedRows()
        filepaths = []
        for idx in selection:
            row = idx.row()
            item = self.file_list.item(row, 7)
            if item:
                fp = item.data(Qt.ItemDataRole.UserRole)
                if fp:
                    filepaths.append(str(fp))
        return filepaths

    def _on_save_metadata(self, data):
        filepaths = self._get_selected_filepaths()
        if not filepaths:
            return
        try:
            if hasattr(self, "player_widget"):
                self.player_widget.stop()
            for fp in filepaths:
                self.metadata_service.save_from_panel(fp, data)
            self._refresh_current_view()
            count = len(filepaths)
            self.statusBar().showMessage(
                f"Metadatos guardados ({count} archivo{'s' if count > 1 else ''})", 3000
            )
        except Exception as e:
            logger.error(f"Error guardando metadatos: {e}")
            QMessageBox.warning(
                self, "Error", f"No se pudieron guardar los metadatos:\n{e}"
            )

    def _on_identify(self):
        filepath = self._state.selected_filepath
        if not filepath:
            return
        try:
            reader = MP3Reader(filepath)
            music_file = reader.read(use_cache=True, save_db=False)
        except Exception:
            music_file = None
        if not music_file or not music_file.metadata:
            QMessageBox.information(
                self, "Identificar", "No hay metadata local para buscar."
            )
            return
        artist = music_file.metadata.artist
        title = music_file.metadata.title
        duration = music_file.technical.duration if music_file.technical else None
        self.statusBar().showMessage("Buscando en MusicBrainz/iTunes...", 0)
        QApplication.processEvents()
        try:
            result = self.online_service.search_by_text(artist, title, duration)
            if result:
                local_data = {
                    "title": music_file.metadata.title,
                    "artist": music_file.metadata.artist,
                    "album": music_file.metadata.album,
                    "genre": music_file.metadata.genre,
                    "year": music_file.metadata.year,
                }
                local_cover = (
                    music_file.metadata.cover_data if music_file.metadata else None
                )
                dlg = MetadataComparisonDialog(
                    local_data, result, self, local_cover_data=local_cover
                )
                if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
                    self.metadata_panel.update_data(
                        MetadataInfo(
                            title=dlg.result_data.get("title", ""),
                            artist=dlg.result_data.get("artist", ""),
                            album=dlg.result_data.get("album", ""),
                            genre=dlg.result_data.get("genre", ""),
                            year=dlg.result_data.get("year", ""),
                        ),
                        filepath,
                    )
                    self.statusBar().showMessage("Metadatos online aplicados", 3000)
            else:
                QMessageBox.information(
                    self, "Identificar", "No se encontraron resultados online."
                )
        except Exception as e:
            logger.error(f"Error en identificacion: {e}")
            QMessageBox.warning(self, "Error", f"Error buscando metadatos:\n{e}")
        finally:
            self.statusBar().showMessage("Listo", 3000)

    def _on_fingerprint_requested(self, filepath):
        self._do_fingerprint_identify([filepath])

    def _on_fingerprint_from_panel(self, filepath):
        self._do_fingerprint_identify([filepath])

    def _on_batch_fingerprint(self, filepaths):
        self._do_fingerprint_identify(filepaths)

    def _do_fingerprint_identify(self, filepaths):
        for filepath in filepaths:
            if not filepath or not os.path.exists(filepath):
                continue
            self.statusBar().showMessage(
                f"Identificando por fingerprint: {os.path.basename(filepath)}...", 0
            )
            QApplication.processEvents()
            try:
                result, status_msg = self.online_service.identify_by_fingerprint(
                    filepath
                )
                if result:
                    try:
                        reader = MP3Reader(filepath)
                        music_file = reader.read(use_cache=True, save_db=False)
                    except Exception:
                        music_file = None
                    local_data = {
                        "title": music_file.metadata.title
                        if music_file and music_file.metadata
                        else "",
                        "artist": music_file.metadata.artist
                        if music_file and music_file.metadata
                        else "",
                        "album": music_file.metadata.album
                        if music_file and music_file.metadata
                        else "",
                        "genre": music_file.metadata.genre
                        if music_file and music_file.metadata
                        else "",
                        "year": music_file.metadata.year
                        if music_file and music_file.metadata
                        else "",
                    }
                    local_cover = (
                        music_file.metadata.cover_data
                        if music_file and music_file.metadata
                        else None
                    )
                    dlg = MetadataComparisonDialog(
                        local_data, result, self, local_cover_data=local_cover
                    )
                    if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
                        self.metadata_service.save_from_panel(filepath, dlg.result_data)
                        self._refresh_current_view()
                        self.statusBar().showMessage(
                            f"Identificado: {status_msg}", 3000
                        )
                else:
                    QMessageBox.information(
                        self, "Fingerprint", f"No identificado:\n{status_msg}"
                    )
            except Exception as e:
                logger.error(f"Error fingerprint: {e}")
                QMessageBox.warning(self, "Error", f"Error en fingerprint:\n{e}")
        self.statusBar().showMessage("Listo", 3000)

    def _on_file_deleted(self, filepath):
        try:
            self.db_manager.delete_track(filepath)
        except Exception as e:
            logger.error(f"Error deleting track from DB: {e}")
        self._refresh_current_view()
        self.statusBar().showMessage(
            f"Archivo eliminado: {os.path.basename(filepath)}", 3000
        )

    def _on_file_moved(self, old_path, new_path):
        try:
            self.db_manager.delete_track(old_path)
        except Exception as e:
            logger.error(f"Error updating moved track: {e}")
        self._refresh_current_view()
        self.statusBar().showMessage("Archivo movido", 3000)

    def _on_file_delete_requested(self, filepath):
        if hasattr(self, "player_widget"):
            self.player_widget.stop()
        if hasattr(self, "file_list"):
            self.file_list._stop_cue_preview()

    def _on_file_move_requested(self, filepath):
        if hasattr(self, "player_widget"):
            self.player_widget.stop()
        if hasattr(self, "file_list"):
            self.file_list._stop_cue_preview()

    def _update_row_in_grid(self, music_file):
        self.file_list.update_track_in_row(music_file)

    def _refresh_current_view(self):
        if self._current_folder:
            tracks = self.db_manager.get_tracks_by_folder(self._current_folder)
            self.file_list.load_tracks_from_db(tracks)
        else:
            self._apply_filters()
