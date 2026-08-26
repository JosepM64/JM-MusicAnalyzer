import logging

logger = logging.getLogger(__name__)


class PlaylistAutomixMixin:
    def _on_automix_clicked(self):
        """Toggle del botón LANZAR MIX."""
        is_active = self.btn_automix.isChecked()
        self._update_automix_button_style(is_active)
        self.automixToggled.emit(is_active)

    def _update_automix_button_style(self, active):
        """Actualiza el estilo del botón según el estado."""
        if active:
            self.btn_automix.setText("⏹ PARAR MIX")
            self.btn_automix.setStyleSheet("""
                QPushButton {
                    background-color: #228b22; color: white; font-weight: bold;
                    border-radius: 4px; padding: 4px 12px;
                }
                QPushButton:hover { background-color: #2ea02e; }
            """)
        else:
            self.btn_automix.setText("▶ LANZAR MIX")
            self.btn_automix.setStyleSheet("""
                QPushButton {
                    background-color: #555; color: #aaa; font-weight: bold;
                    border-radius: 4px; padding: 4px 12px;
                }
                QPushButton:hover { background-color: #666; color: #ccc; }
            """)
