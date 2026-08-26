import logging

logger = logging.getLogger(__name__)


class PerfCrossfaderMixin:
    def _on_master_vol_changed(self, value):
        # Actualizar etiqueta
        if value > 100:
            self.lbl_master_vol.setText(f"+{value - 100}%")
            self.lbl_master_vol.setStyleSheet(
                "color: #ff4444; font-weight: bold; font-size: 12px;"
            )
            # CLIP activo en rojo
            self.lbl_clip.setStyleSheet("""
                background-color: #ff0000; color: white; 
                font-weight: bold; font-size: 9px;
                border-radius: 2px;
            """)
        else:
            self.lbl_master_vol.setText(f"{value}%")
            self.lbl_master_vol.setStyleSheet(
                "color: cyan; font-weight: bold; font-size: 12px;"
            )
            # CLIP inactivo en gris oscuro
            self.lbl_clip.setStyleSheet("""
                background-color: #222; color: #444; 
                font-weight: bold; font-size: 9px;
                border-radius: 2px;
            """)
        self._on_crossfader_changed(self.crossfader.value())

    def _on_crossfader_changed(self, value):
        master = self.vol_master.value() / 100.0

        # Si tenim el SimpleAudioEngine, aplicar gain
        if self._use_simple_engine and self.simple_engine:
            self.simple_engine.set_gain(master)
            logger.info(f"SimpleAudioEngine gain: {master}")

        # Aplicar gain i crossfader al MasterEngine (sounddevice)
        if self._use_audio_engine and self.master_engine:
            self.master_engine.set_master_gain(master)
            self.master_engine.set_crossfader(value)
            logger.info(f"MasterEngine gain: {master}, crossfader: {value}")

        # Curva equal-power para crossfade suave (estándar DJ profesional)
        import math

        x = (value + 100) / 200.0  # Normalizar a 0-1
        vol_a = math.cos(x * math.pi / 2.0)
        vol_b = math.sin(x * math.pi / 2.0)

        # Aplicar volum als decks
        if self._use_audio_engine:
            # En mode audio engine, el master gain ja s'aplica globalment
            effective_vol_a = vol_a
            effective_vol_b = vol_b
        else:
            # En mode QMediaPlayer, cal multiplicar per master
            effective_vol_a = vol_a * master
            effective_vol_b = vol_b * master

        self.deck_a.setVolume(effective_vol_a)
        self.deck_b.setVolume(effective_vol_b)

    def _update_vu_meters(self):
        """Actualiza los medidores VU"""
        try:
            var_a = 0.0
            var_b = 0.0

            if self.master_engine:
                try:
                    deck_a = getattr(self.deck_a, "deck", None)
                    deck_b = getattr(self.deck_b, "deck", None)

                    if (
                        deck_a
                        and hasattr(deck_a, "get_level")
                        and getattr(deck_a, "is_playing", False)
                    ):
                        level_a = deck_a.get_level()
                        vol_a = self.deck_a.slider_vol.value() / 100.0
                        cf_factor_a = (100 - self.crossfader.value()) / 100.0
                        var_a = min(
                            level_a
                            * vol_a
                            * self.master_engine.master_gain
                            * cf_factor_a,
                            1.0,
                        )

                    if (
                        deck_b
                        and hasattr(deck_b, "get_level")
                        and getattr(deck_b, "is_playing", False)
                    ):
                        level_b = deck_b.get_level()
                        vol_b = self.deck_b.slider_vol.value() / 100.0
                        cf_factor_b = (100 + self.crossfader.value()) / 100.0
                        var_b = min(
                            level_b
                            * vol_b
                            * self.master_engine.master_gain
                            * cf_factor_b,
                            1.0,
                        )

                except Exception:
                    pass

            if hasattr(self, "vu_left") and self.vu_left:
                self.vu_left.setValue(int(var_a * 100))
            if hasattr(self, "vu_right") and self.vu_right:
                self.vu_right.setValue(int(var_b * 100))
        except Exception:
            pass

    def _get_simulated_vu_levels(self):
        """Genera niveles simulados para VU meters (fallback)"""
        import random

        vol_a = getattr(self, "_last_vol_a", 0.8)
        vol_b = getattr(self, "_last_vol_b", 0.0)

        deck_vol_a = (
            self.deck_a.slider_vol.value() / 100.0
            if hasattr(self.deck_a, "slider_vol")
            else 1.0
        )
        deck_vol_b = (
            self.deck_b.slider_vol.value() / 100.0
            if hasattr(self.deck_b, "slider_vol")
            else 1.0
        )

        vol_a *= deck_vol_a
        vol_b *= deck_vol_b

        playing_a = (
            self.deck_a.player.playbackState() == 1
            if hasattr(self.deck_a, "player")
            else False
        )
        playing_b = (
            self.deck_b.player.playbackState() == 1
            if hasattr(self.deck_b, "player")
            else False
        )

        if playing_a:
            var_a = vol_a * (0.5 + random.random() * 0.5)
        else:
            var_a = 0.0

        if playing_b:
            var_b = vol_b * (0.5 + random.random() * 0.5)
        else:
            var_b = 0.0

        return var_a, var_b
