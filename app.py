from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.tokens import (
    BG_400,
    BG_500,
    BG_600,
    BG_700,
    BG_800,
    BG_900,
    PRIMARY,
    TEXT_40,
    TEXT_80,
    TEXT_100,
)

try:
    import JM_MusicAnalizer

    APP_VERSION = getattr(JM_MusicAnalizer, "APP_VERSION", "4.43.0")

    if not APP_VERSION or APP_VERSION.startswith("${"):
        APP_VERSION = "4.43.0"
except (ImportError, ModuleNotFoundError):
    APP_VERSION = "4.43.0"


class MusicAnalyzerApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self.setApplicationName("JM-MusicAnalyzer")
        self.setApplicationVersion(APP_VERSION)
        self._apply_dark_palette()

        # Initialize Main Window
        self.main_window = MainWindow()
        self.main_window.show()

    def _apply_dark_palette(self):
        """Paleta fosca propia: la app es veu igual amb Windows en mode clar o fosc.

        El QSS global (APP_GLOBAL_QSS) cobreix els widgets principals, però la resta
        (arbres, scrollbars, desplegables, tooltips...) agafarien el tema del Windows
        d'origen — en un PC en mode clar sortien files blanques i text fosc.
        """
        self.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        roles = QPalette.ColorRole
        palette = QPalette()
        palette.setColor(roles.Window, QColor(BG_900))
        palette.setColor(roles.WindowText, QColor(TEXT_80))
        palette.setColor(roles.Base, QColor(BG_800))
        palette.setColor(roles.AlternateBase, QColor(BG_700))
        palette.setColor(roles.Text, QColor(TEXT_80))
        palette.setColor(roles.Button, QColor(BG_400))
        palette.setColor(roles.ButtonText, QColor(TEXT_80))
        palette.setColor(roles.Highlight, QColor(PRIMARY))
        palette.setColor(roles.HighlightedText, QColor(TEXT_100))
        palette.setColor(roles.ToolTipBase, QColor(BG_600))
        palette.setColor(roles.ToolTipText, QColor(TEXT_100))
        palette.setColor(roles.PlaceholderText, QColor(TEXT_40))
        palette.setColor(roles.Link, QColor(PRIMARY))
        palette.setColor(roles.Light, QColor(BG_500))
        palette.setColor(roles.Mid, QColor(BG_500))
        palette.setColor(roles.Dark, QColor(BG_600))
        palette.setColor(roles.Shadow, QColor("#000000"))
        for role in (roles.Text, roles.WindowText, roles.ButtonText):
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(TEXT_40))
        self.setPalette(palette)
