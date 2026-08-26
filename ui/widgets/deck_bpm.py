import logging

logger = logging.getLogger(__name__)


class DeckBpmMixin:
    BPM_MANUAL_DEFAULT = 120.0
    BPM_MIN = 60.0

    def set_bpm(self, bpm):
        """Establece el BPM original de la pista (desde metadatos).
        Si no hay BPM, usa 120 como default."""
        logger.info(f"[{self.name}] set_bpm called with bpm={bpm}")
        self._original_bpm = bpm if bpm and bpm > 0 else None
        self.current_bpm = (
            self._original_bpm if self._original_bpm else self.BPM_MANUAL_DEFAULT
        )
        self.bpm_adjustment = 0
        self._update_bpm_display()
        if self.deck and hasattr(self.deck, "set_rate"):
            self.deck.set_rate(1.0)

    def adjust_bpm(self, delta):
        """Ajusta el BPM en incrementos delta (±1, ±5, ±10).
        Si no hay BPM previo, usa 120 como base para modo manual."""
        logger.info(
            f"[{self.name}] adjust_bpm: delta={delta}, current_bpm={self.current_bpm}, adjustment before={self.bpm_adjustment}"
        )
        if self.current_bpm is None or self.current_bpm <= 0:
            self.current_bpm = self.BPM_MANUAL_DEFAULT
            self.bpm_adjustment = 0
            logger.info(
                f"[{self.name}] adjust_bpm: no BPM, modo manual desde {self.BPM_MANUAL_DEFAULT}"
            )
        adj = self.current_bpm + self.bpm_adjustment + delta
        if adj < self.BPM_MIN:
            logger.info(
                f"[{self.name}] adjust_bpm ignored: result {adj} < min {self.BPM_MIN}"
            )
            return
        self.bpm_adjustment += delta
        self._update_bpm_display()
        adj = self.current_bpm + self.bpm_adjustment
        if adj > 0:
            rate = adj / self.current_bpm
            self.bpmAdjusted.emit(adj)
            logger.info(f"[{self.name}] bpmAdjusted emitted: {adj}, rate: {rate:.3f}")
            if self.deck and hasattr(self.deck, "set_rate"):
                self.deck.set_rate(rate)
                logger.info(f"[{self.name}] set_rate: {rate:.3f}")

    def _update_bpm_display(self):
        """Actualiza el label de BPM con valor ajustado y el rate indicator."""
        if self.current_bpm is not None and self.current_bpm > 0:
            adj = self.current_bpm + self.bpm_adjustment
            is_manual = self._original_bpm is None
            if self.bpm_adjustment == 0:
                self.lbl_bpm_display.setText(
                    f"BPM: {self.current_bpm:.0f}{'(M)' if is_manual else ''}"
                )
            else:
                sign = "+" if self.bpm_adjustment > 0 else ""
                self.lbl_bpm_display.setText(
                    f"BPM: {adj:.0f} ({sign}{self.bpm_adjustment:.0f}){'(M)' if is_manual else ''}"
                )
            color = "#ffcc00" if self.bpm_adjustment != 0 else "#aaa"
            self.lbl_bpm_display.setStyleSheet(
                f"color: {color}; font-size: 10px; margin: 0px; padding: 0px;"
            )
            # Rate indicator
            rate_pct = (adj / self.current_bpm) * 100
            if rate_pct > 100.5:
                rate_color = "#ff4444"
                rate_text = f"{rate_pct:.0f}%+"
            elif rate_pct < 99.5:
                rate_color = "#44ff44"
                rate_text = f"{rate_pct:.0f}%-"
            else:
                rate_color = "#aaa"
                rate_text = "100%"
            self.lbl_rate.setText(rate_text)
            self.lbl_rate.setStyleSheet(
                f"font-size: 8px; font-weight: bold; color: {rate_color}; background: #1a1a1a; border: 1px solid #333; border-radius: 3px;"
            )
        else:
            self.lbl_bpm_display.setText("BPM: --")
            self.lbl_bpm_display.setStyleSheet(
                "color: #aaa; font-size: 10px; margin: 0px; padding: 0px;"
            )
            self.lbl_rate.setText("100%")
            self.lbl_rate.setStyleSheet(
                "font-size: 8px; font-weight: bold; color: #555; background: #1a1a1a; border: 1px solid #333; border-radius: 3px;"
            )

    def _reset_bpm(self):
        """Reset BPM al valor original i velocitat a 1.0."""
        logger.info(f"[{self.name}] _reset_bpm called")
        self.bpm_adjustment = 0
        self.current_bpm = (
            self._original_bpm if self._original_bpm else self.BPM_MANUAL_DEFAULT
        )
        self._update_bpm_display()
        if self.deck and hasattr(self.deck, "set_rate"):
            self.deck.set_rate(1.0)

    def _update_beat_counter(self, pos_sec):
        """Actualiza el beat counter (1-2-3-4) basado en posicion y BPM."""
        if pos_sec < 0:
            for lbl in self._beat_labels:
                lbl.setStyleSheet(
                    "font-size: 9px; font-weight: bold; color: #555; background: #1a1a1a; border: 1px solid #333; border-radius: 3px;"
                )
            return
        bpm = self.BPM_MANUAL_DEFAULT
        if self.current_bpm and self.current_bpm > 0:
            bpm = self.current_bpm + self.bpm_adjustment
        elif self.bpm_adjustment != 0:
            bpm = self.BPM_MANUAL_DEFAULT + self.bpm_adjustment
        if bpm <= 0:
            return
        beat_duration = 60.0 / bpm
        pos_in_beats = pos_sec / beat_duration
        beat_index = int(pos_in_beats) % 4
        for i, lbl in enumerate(self._beat_labels):
            if i == beat_index:
                if i == 0:
                    bg = "#0078d4"
                    fg = "white"
                else:
                    bg = "#333"
                    fg = "#ddd"
            else:
                bg = "#1a1a1a"
                fg = "#555"
            lbl.setStyleSheet(
                f"font-size: 9px; font-weight: bold; color: {fg}; background: {bg}; border: 1px solid #333; border-radius: 3px;"
            )
