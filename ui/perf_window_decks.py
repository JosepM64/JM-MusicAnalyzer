import logging
import os

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtWidgets import QLabel, QMessageBox

from core.reader.mp3_reader import MP3Reader
from services.audio_hardware_service import AudioHardwareService
from ui.dialogs.audio_config_dialog import AudioConfigDialog

logger = logging.getLogger(__name__)


class PerfDeckMixin:
    def _load_hardware_settings(self):
        from ui.styles import load_audio_devices_from_settings

        load_audio_devices_from_settings(
            self.settings,
            master_widgets=[self.deck_a, self.deck_b],
            cue_widgets=[
                self.playlist_widget,
                self.second_playlist_widget,
                self.deck_a,
                self.deck_b,
            ],
        )
        self._update_audio_device_label()

    def _load_last_playlist(self):
        """Carga automáticamente la última playlist usada al abrir DJ Mode."""
        from services.playlist_manager import PlaylistManager

        pm = PlaylistManager()
        last_playlist = pm.get_last_playlist()
        if last_playlist and os.path.exists(last_playlist):
            logger.info(f"_load_last_playlist: cargando {last_playlist}")
            self.playlist_widget.load_m3u(last_playlist)

    def _update_audio_device_label(self):
        """Actualiza el label con los dispositivos de audio configurados."""
        master_name = "Predeterminado"
        cue_name = "Predeterminado"

        master_id = self.settings.get("master_device_id")
        cue_id = self.settings.get("cue_device_id")

        if master_id:
            dev = AudioHardwareService.find_device_by_id(master_id)
            if dev:
                if isinstance(dev, dict):
                    master_name = dev.get("name", "Unknown")
                else:
                    try:
                        master_name = dev.description()
                    except Exception:
                        master_name = "Dispositivo Audio"
                # Netejar nom - treure "Microphone" si existeix
                if "Microphone" in master_name or "Mic" in master_name:
                    master_name = (
                        master_name.replace("Microphone", "").replace("Mic", "").strip()
                    )
                master_name = master_name[:25]  # Limitar longitud

        if cue_id:
            dev = AudioHardwareService.find_device_by_id(cue_id)
            if dev:
                if isinstance(dev, dict):
                    cue_name = dev.get("name", "Unknown")
                else:
                    try:
                        cue_name = dev.description()
                    except Exception:
                        cue_name = "Dispositivo Audio"
                # Netejar nom - treure "Microphone" si existeix
                if "Microphone" in cue_name or "Mic" in cue_name:
                    cue_name = (
                        cue_name.replace("Microphone", "").replace("Mic", "").strip()
                    )
                cue_name = cue_name[:25]  # Limitar longitud

        if hasattr(self, "lbl_audio_devices"):
            self.lbl_audio_devices.setText(
                f"\U0001f50a {master_name} | \U0001f3a7 {cue_name}"
            )
        else:
            self.lbl_audio_devices = QLabel(
                f"\U0001f50a {master_name} | \U0001f3a7 {cue_name}"
            )
            self.lbl_audio_devices.setStyleSheet("color: #aaa; font-size: 10px;")
            self.lbl_audio_devices.setToolTip(
                "\U0001f50a = Master (Altificadores) | \U0001f3a7 = CUE (Auriculares)"
            )
            self.toolbar.addWidget(self.lbl_audio_devices)

    def _load_metadata_suggestions(self):
        """Carga sugerencias de géneros y artistas desde la base de datos."""
        try:
            from services.db import get_db

            db = get_db()
            genres = db.get_unique_genres()
            artists = db.get_unique_artists()
            self.genre_completer.setModel(QStringListModel(sorted(genres)))
            self.artist_completer.setModel(QStringListModel(sorted(artists)))
            logger.info(
                f"Sugerencias cargadas: {len(genres)} géneros, {len(artists)} artistas"
            )
        except Exception as e:
            logger.error(f"Error cargando sugerencias: {e}")

    def _is_deck_playing(self, deck_obj):
        if hasattr(deck_obj, "deck") and deck_obj.deck:
            return deck_obj.deck.is_playing
        return False

    def _on_track_loaded(self, p, d):
        # Prevent same song en ambos decks
        other_deck = "B" if d == "A" else "A"
        other_info = self._deck_tracks.get(other_deck)
        if other_info and other_info.get("path") == p:
            QMessageBox.warning(
                self, "Misma canción", f"Esa pista ya está en el deck {other_deck}."
            )
            return

        # Evitar cargar en el deck que está sonando (rompe el automix)
        playing_a = self.deck_a.player.playbackState() == 1  # PlayingState
        playing_b = self.deck_b.player.playbackState() == 1  # PlayingState

        if playing_a and not playing_b and d == "A":
            d = "B"  # Cambiar al deck silencioso
        elif playing_b and not playing_a and d == "B":
            d = "A"
        # Si ambos están sonando o ninguno, respetar el deck sugerido (alternancia)

        # Sincronizar el toggle interno de ambos playlist_widgets
        self.playlist_widget._last_load_deck = d
        self.second_playlist_widget._last_load_deck = d

        if d == "A":
            self.deck_a.load_file(p, False)
        else:
            self.deck_b.load_file(p, False)
        self.lbl_now_playing.setText(f"Cargado en {d}:\n{os.path.basename(p)}")

        # Guardar metadatos del track para BPM/Key/Genre y path para evitar duplicados
        try:
            track = self.metadata_service.get_track_by_path(p)
            if track:
                self._deck_tracks[d] = {
                    "path": p,
                    "bpm": getattr(track, "bpm", None),
                    "key": getattr(track, "key", None),
                    "genre": getattr(track, "genre", None),
                }
            else:
                self._deck_tracks[d] = {
                    "path": p,
                    "bpm": None,
                    "key": None,
                    "genre": None,
                }
        except Exception as e:
            logger.warning(f"Error obteniendo metadatos para BPM match: {e}")
            self._deck_tracks[d] = None

        self._update_bpm_match()

        # Actualizar display de género y tonalidad en el deck correspondiente
        genre = self._deck_tracks[d].get("genre") if self._deck_tracks[d] else None
        key = self._deck_tracks[d].get("key") if self._deck_tracks[d] else None
        bpm = self._deck_tracks[d].get("bpm") if self._deck_tracks[d] else None
        deck = self.deck_a if d == "A" else self.deck_b
        if hasattr(deck, "set_genre"):
            deck.set_genre(genre or "")
        if hasattr(deck, "set_key"):
            deck.set_key(key or "")
        if hasattr(deck, "set_bpm"):
            deck.set_bpm(bpm)

    def _on_track_selected_in_list(self, filepath):
        if not filepath:
            return
        self._current_info_filepath = filepath
        reader = MP3Reader(filepath)
        mf = reader.read(True, False)
        if mf.metadata:
            if mf.metadata.cover_data:
                self.cover_view.set_cover(
                    mf.metadata.cover_data, mf.metadata.cover_mime or "image/jpeg"
                )
            else:
                self.cover_view.clear()

            # Mostrar info
            title = mf.metadata.title or os.path.basename(filepath)
            artist = mf.metadata.artist or ""
            self.lbl_now_playing.setText(f"<b>{title}</b>\n{artist}")

            # Ruta del archivo
            self.lbl_file_path.setText(filepath)

            # Poblar campos editables
            self.edit_title.setText(mf.metadata.title or "")
            self.edit_artist.setText(mf.metadata.artist or "")
            self.edit_genre.setText(mf.metadata.genre or "")
            self.rating_edit.set_rating(mf.metadata.rating or 0)

            self.btn_save_metadata.setEnabled(True)
        else:
            self.cover_view.clear()
            self.lbl_now_playing.setText(os.path.basename(filepath))
            self.lbl_file_path.setText(filepath)
            self.edit_title.clear()
            self.edit_artist.clear()
            self.edit_genre.clear()
            self.rating_edit.set_rating(0)
            self.btn_save_metadata.setEnabled(True)

    def _on_playlist_ready(self):
        if self._automix_active:
            # Don't interrupt the playing deck - only load into the silent one
            playing = None
            if self._is_deck_playing(self.deck_a):
                playing = "A"
            elif self._is_deck_playing(self.deck_b):
                playing = "B"
            it_a = self.playlist_widget.table.item(0, 4)
            if it_a and playing != "A":
                self.deck_a.load_file(it_a.data(Qt.ItemDataRole.UserRole), False)
            it_b = self.playlist_widget.table.item(1, 4)
            if it_b and playing != "B":
                self.deck_b.load_file(it_b.data(Qt.ItemDataRole.UserRole), False)
        elif self.playlist_widget.table.rowCount() > 0:
            it_a = self.playlist_widget.table.item(0, 4)
            if it_a:
                self.deck_a.load_file(it_a.data(Qt.ItemDataRole.UserRole), False)
            if self.playlist_widget.table.rowCount() > 1:
                it_b = self.playlist_widget.table.item(1, 4)
                if it_b:
                    self.deck_b.load_file(it_b.data(Qt.ItemDataRole.UserRole), False)

        # Rebuild automix track list so new playlist is used for transitions
        self._playlist_tracks = []
        for row in range(self.playlist_widget.table.rowCount()):
            it = self.playlist_widget.table.item(row, 4)
            if it:
                p = it.data(Qt.ItemDataRole.UserRole)
                if p:
                    self._playlist_tracks.append(p)

        if self._automix_active and self._playlist_tracks:
            current_file = None
            if (
                hasattr(self.deck_a, "deck")
                and self.deck_a.deck
                and self.deck_a.deck.is_playing
            ):
                current_file = self.deck_a.current_file
            elif (
                hasattr(self.deck_b, "deck")
                and self.deck_b.deck
                and self.deck_b.deck.is_playing
            ):
                current_file = self.deck_b.current_file
            if current_file and current_file in self._playlist_tracks:
                self._playlist_index = self._playlist_tracks.index(current_file) + 1
            else:
                self._playlist_index = 0
            logger.info(
                f"[Automix] Playlist recargada: {len(self._playlist_tracks)} tracks, index={self._playlist_index}"
            )

    def _update_master_playlist_label(self):
        """Actualiza el label con el nombre de la playlist cargada."""
        logger.info("_update_master_playlist_label called")
        if hasattr(self, "lbl_master_playlist"):
            path = getattr(self.playlist_widget, "_current_playlist_path", None)
            logger.info(f"  _current_playlist_path = {path}")
            if path:
                playlist_name = os.path.basename(path)
                count = self.playlist_widget.table.rowCount()
                total_duration = self._get_playlist_duration(self.playlist_widget)
                duration_str = self._format_duration(total_duration)
                self.lbl_master_playlist.setText(
                    f"<b>\U0001f4dc MASTER PLAYLIST:</b> <span style='color:#00d4ff'>{playlist_name}</span> | <span style='color:#888'>{count} pistas ({duration_str})</span>"
                )
            else:
                count = self.playlist_widget.table.rowCount()
                total_duration = self._get_playlist_duration(self.playlist_widget)
                duration_str = self._format_duration(total_duration)
                self.lbl_master_playlist.setText(
                    f"<b>\U0001f4dc MASTER PLAYLIST:</b> <span style='color:#888'>{count} pistas ({duration_str})</span>"
                )
        else:
            logger.warning("lbl_master_playlist not found!")

    def _on_audio_config(self):
        dlg = AudioConfigDialog(self)
        if dlg.exec():
            cfg = dlg.get_config()
            if cfg["master"]:
                self.deck_a.setAudioDevice(cfg["master"])
                self.deck_b.setAudioDevice(cfg["master"])
            if cfg["cue"]:
                self.playlist_widget.setAudioDevice(cfg["cue"])
            self._update_audio_device_label()

    def _on_save_rating(self, path, stars):
        try:

            def release():
                if self.deck_a.current_file == path:
                    self.deck_a.release()
                if self.deck_b.current_file == path:
                    self.deck_b.release()

            self.metadata_service.save_rating(path, stars, release_player=release)
            self.playlist_widget.update_rating_in_table(path, stars)
            self.second_playlist_widget.update_rating_in_table(path, stars)
        except Exception:
            pass

    def _save_metadata_from_info_panel(self):
        """Guarda los metadatos editados desde el panel de info."""
        if (
            not hasattr(self, "_current_info_filepath")
            or not self._current_info_filepath
        ):
            QMessageBox.warning(
                self, "Sin archivo", "No hay ningún archivo seleccionado."
            )
            return

        filepath = self._current_info_filepath
        try:

            def release():
                if self.deck_a.current_file == filepath:
                    self.deck_a.release()
                if self.deck_b.current_file == filepath:
                    self.deck_b.release()

            data = {
                "title": self.edit_title.text().strip(),
                "artist": self.edit_artist.text().strip(),
                "genre": self.edit_genre.text().strip(),
                "rating": self.rating_edit.rating,
            }
            self.metadata_service.save_from_panel(
                filepath, data, release_player=release
            )

            self.playlist_widget.update_rating_in_table(
                filepath, self.rating_edit.rating
            )
            self.second_playlist_widget.update_rating_in_table(
                filepath, self.rating_edit.rating
            )

            QMessageBox.information(
                self, "Guardado", "Metadatos guardados correctamente."
            )

        except Exception as e:
            logger.error(f"Error guardando metadatos: {e}")
            QMessageBox.critical(
                self, "Error", f"No se pudieron guardar los metadatos:\n{e!s}"
            )

    def _add_track_to_master(self, path):
        """Añade un track de la segunda lista a la lista master."""
        if not path or not os.path.exists(path):
            logger.warning(f"[AddToMaster] Archivo no encontrado: {path}")
            return
        self.playlist_widget.add_track(path)
        self.playlist_widget._modified = True
        self.playlist_widget._update_row_numbers()
        logger.info(
            f"[AddToMaster] Añadido a master playlist: {os.path.basename(path)}"
        )
        try:
            self.statusBar().showMessage(
                f"Añadido a master playlist: {os.path.basename(path)}", 3000
            )
        except AttributeError:
            pass

    def _add_tracks_to_master(self, paths):
        """Añade múltiples tracks de la segunda lista a la lista master."""
        added = 0
        for path in paths:
            if not path or not os.path.exists(path):
                continue
            self.playlist_widget.add_track(path)
            added += 1
        if added > 0:
            self.playlist_widget._modified = True
            self.playlist_widget._update_row_numbers()
            logger.info(f"[AddToMaster] Añadidas {added} canciones a master playlist")
            try:
                self.statusBar().showMessage(
                    f"Añadidas {added} canciones a master playlist", 3000
                )
            except AttributeError:
                pass
