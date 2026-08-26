import logging
import os

from PySide6.QtCore import QUrl

logger = logging.getLogger(__name__)


class DeckControlsMixin:
    def _on_vol_changed(self, value):
        volume = value / 100.0
        deck_id = None
        if self.deck_id is not None:
            deck_id = self.deck_id
        elif self.deck and hasattr(self.deck, "deck_id"):
            deck_id = self.deck.deck_id

        if deck_id is not None and self.master:
            self.master.set_deck_volume(deck_id, volume)

    def _on_cue_vol_changed(self, value):
        """Controla el volum del CUE player."""
        if self._cue_player:
            self._cue_player.setVolume(value / 100.0)

    def _on_seek_pressed(self):
        self._seeking = True
        self._seek_value = self.slider_progress.value()

    def _on_seek_moved(self, value):
        self._seek_value = value
        if self.deck and self.deck.is_loaded:
            total = self.deck.get_duration_samples()
            pos = int(value * total / 100)
            pos_sec = pos / self.deck.samplerate if self.deck.samplerate else 0
            total_sec = total / self.deck.samplerate if self.deck.samplerate else 0
            self.lbl_time.setText(
                f"{self._format_time(pos_sec)} / {self._format_time(total_sec)}"
            )

    def _on_seek_released(self):
        if self.deck and self.deck.is_loaded:
            value = self._seek_value
            total = self.deck.get_duration_samples()
            pos = int(value * total / 100)
            self.deck.seek(pos)
        self._seeking = False

    def setAudioDevice(self, device):
        """Compatibilidad - no usado en sounddevice"""

    def setCueAudioDevice(self, device):
        """Establece el dispositivo de audio para el CUE/preshoot."""
        if self._cue_player:
            # `device` puede ser un índice (int) o un dict con 'index'
            dev_index = device
            if isinstance(device, dict):
                dev_index = device.get("index")
            if dev_index is not None:
                self._cue_player.setDevice(dev_index)
                logger.info(f"Deck {self.name}: CUE device set to index={dev_index}")
            else:
                logger.warning(
                    f"Deck {self.name}: CUE device sin índice, usando default"
                )

    def play(self):
        """Reproduce"""
        try:
            if self.deck:
                logger.info(
                    f"[AudioEnginePlayer] play() called, deck.is_loaded={self.deck.is_loaded}"
                )
                self.deck.play()
        except Exception as e:
            logger.error(f"[AudioEnginePlayer] Error en play(): {e}")
            import traceback

            traceback.print_exc()

    def pause(self):
        """Pausa"""
        try:
            if self.deck:
                self.deck.pause()
        except Exception as e:
            logger.error(f"[AudioEnginePlayer] Error en pause(): {e}")

    def toggle_play_pause(self):
        """Alterna entre play y pause"""
        try:
            if self.deck and hasattr(self.deck, "is_playing"):
                if self.deck.is_playing:
                    self.pause()
                else:
                    self.play()
        except Exception as e:
            logger.error(f"[AudioEnginePlayer] Error en toggle_play_pause(): {e}")

    def stop(self):
        """Detiene"""
        try:
            if self.deck:
                self.deck.stop()
            self.vinyl.set_spinning(False)
            self.slider_progress.setValue(0)
            self._last_playing_state = False
        except Exception as e:
            logger.error(f"[AudioEnginePlayer] Error en stop(): {e}")
        self.lbl_time.setText("00:00 / 00:00")
        # Aturar CUE si està actiu
        self._stop_cue_internal()

    def _stop_cue_internal(self):
        """Atura el CUE internament."""
        if self._cue_player and self._cue_playing:
            try:
                self._cue_player.stop()
                self._cue_playing = False
                self.btn_cue.setStyleSheet(
                    "background-color: #222; color: #666; border: 1px solid #444; border-radius: 4px;"
                )
                self.btn_cue.setToolTip("CUE: Pre-escolta per auriculars")
            except Exception as e:
                logger.error(f"Error aturant CUE: {e}")

    def _toggle_cue(self):
        """Activa/desactiva la pre-escolta CUE."""
        if not self._cue_player:
            logger.error(
                f"Deck {self.name}: CUE player no disponible (CUEFallbackPlayer no creat)"
            )
            return
        if not self.current_file:
            logger.warning(
                f"Deck {self.name}: CUE no disponible perquè no hi ha fitxer carregat"
            )
            return

        try:
            if self._cue_playing:
                # Aturar CUE
                self._stop_cue_internal()
            else:
                # Iniciar CUE
                logger.info(
                    f"Deck {self.name}: CUE iniciant reproducció de {os.path.basename(self.current_file)}"
                )
                self._cue_player.setSource(QUrl.fromLocalFile(self.current_file))
                self._cue_player.play()
                self._cue_playing = True
                self.btn_cue.setStyleSheet(
                    "background-color: #0078d4; color: white; border: 2px solid #005a9e; border-radius: 4px;"
                )
                self.btn_cue.setToolTip(
                    "CUE: Reproduint per auriculars (click per aturar)"
                )
                logger.info(f"Deck {self.name}: CUE actiu")
        except Exception as e:
            logger.error(f"Deck {self.name}: Error en CUE: {e}")
            self._cue_playing = False
            self.btn_cue.setStyleSheet(
                "background-color: #222; color: #666; border: 1px solid #444; border-radius: 4px;"
            )

    def setVolume(self, volume_01):
        """Ajusta volumen (0.0 a 1.0)"""
        if self.master is None:
            return
        deck_id = (
            self.deck_id
            if self.deck_id is not None
            else (self.deck.deck_id if hasattr(self.deck, "deck_id") else None)
        )
        if deck_id is not None:
            self.master.set_deck_volume(deck_id, volume_01)

    def release(self):
        """Libera recursos"""
        if self.deck:
            self.deck.unload()
        deck_id = (
            self.deck_id
            if self.deck_id is not None
            else (self.deck.deck_id if hasattr(self.deck, "deck_id") else None)
        )
        if deck_id is not None and self.master:
            self.master.unregister_deck(deck_id)
            self.deck_id = None

    def _close_player(self):
        """Cierra el reproductor"""
        self.stop()
        self.release()
