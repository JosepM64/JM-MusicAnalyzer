import logging

logger = logging.getLogger(__name__)


class PerfBpmMixin:
    def _update_bpm_match(self):
        """Actualiza el indicador de diferencia BPM entre decks."""
        track_a = self._deck_tracks.get("A")
        track_b = self._deck_tracks.get("B")
        if (
            track_a
            and track_b
            and track_a.get("bpm") is not None
            and track_b.get("bpm") is not None
        ):
            diff = abs(track_a["bpm"] - track_b["bpm"])
            if diff <= 3:
                color = "#00ff00"  # verde
            elif diff <= 8:
                color = "#ffff00"  # amarillo
            else:
                color = "#ff0000"  # rojo
            self.lbl_bpm_match.setText(f"BPM: \u00b1{diff}")
            self.lbl_bpm_match.setStyleSheet(
                f"color: {color}; font-size: 10px; font-weight: bold;"
            )
            self.lbl_bpm_match.setVisible(True)
        else:
            self.lbl_bpm_match.setVisible(False)

    def _on_bpm_adjusted(self, deck_letter, bpm):
        """Maneja ajustes de BPM desde los botones Quick BPM."""
        logger.info(f"[PerformanceWindow] BPM adjusted on deck {deck_letter}: {bpm}")
        if self._deck_tracks.get(deck_letter):
            self._deck_tracks[deck_letter]["bpm"] = bpm
        self._update_bpm_match()

    def _get_playlist_duration(self, playlist_widget):
        """Calcula la duración total de la playlist en segundos."""
        total = 0
        table = playlist_widget.table
        for row in range(table.rowCount()):
            item = table.item(row, 5)  # Columna duración
            if item:
                dur_text = item.text()
                try:
                    if ":" in dur_text:
                        parts = dur_text.split(":")
                        total += int(parts[0]) * 60 + int(parts[1])
                    elif dur_text != "--:--":
                        total += float(dur_text)
                except Exception:
                    pass
        return total

    def _format_duration(self, seconds):
        """Formatea segundos a string legible (1h 30m o 45m)."""
        if seconds < 60:
            return f"{int(seconds)}s"
        if seconds < 3600:
            mins = int(seconds // 60)
            return f"{mins}m"
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"
