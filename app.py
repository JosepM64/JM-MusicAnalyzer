from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

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

        # Initialize Main Window
        self.main_window = MainWindow()
        self.main_window.show()
