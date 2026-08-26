import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

try:
    import JM_MusicAnalizer

    __version__ = getattr(JM_MusicAnalizer, "APP_VERSION", "4.43.0")

    if not __version__ or __version__.startswith("${"):
        __version__ = "4.43.0"
except (ImportError, ModuleNotFoundError):
    __version__ = "4.43.0"


class AboutDialog(QDialog):
    """
    Diálogo 'Acerca de' con información de la aplicación.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de JM-MusicAnalyzer")
        self.resize(500, 550)
        self.setMinimumSize(450, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(25, 20, 25, 20)

        # Foto centrada (grande)
        photo_container = QHBoxLayout()
        photo_container.addStretch()
        try:
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                base_path = sys._MEIPASS
                image_path = os.path.join(base_path, "resources", "JM_DJ.jpg")
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(script_dir))
                image_path = os.path.join(project_root, "resources", "JM_DJ.jpg")

            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    180,
                    180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                photo = QLabel()
                photo.setPixmap(pixmap)
                photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
                photo.setFixedSize(180, 180)
                photo.setStyleSheet("""
                    border: 2px solid #6a1b9a;
                    border-radius: 12px;
                    padding: 3px;
                """)
                photo_container.addWidget(photo)
        except Exception:
            placeholder = QLabel("🎵")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setFixedSize(180, 180)
            placeholder.setStyleSheet("""
                border: 2px solid #6a1b9a;
                border-radius: 12px;
                font-size: 60px;
                color: #6a1b9a;
                background-color: #252525;
            """)
            photo_container.addWidget(placeholder)
        photo_container.addStretch()
        layout.addLayout(photo_container)

        # Título
        title = QLabel("JM-MusicAnalyzer")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #ffffff; margin-top: 5px;")
        layout.addWidget(title)

        # JM DJ ENGINE
        dj_engine = QLabel("JM DJ ENGINE")
        dj_font = QFont()
        dj_font.setPointSize(12)
        dj_font.setBold(True)
        dj_engine.setFont(dj_font)
        dj_engine.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dj_engine.setStyleSheet("color: #6a1b9a; margin-bottom: 5px;")
        layout.addWidget(dj_engine)

        # Versión
        version = QLabel(f"Versión {__version__}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet(
            "color: #00d4ff; font-size: 13px; font-weight: bold; margin-bottom: 3px;"
        )
        layout.addWidget(version)

        # Autor
        author = QLabel("Desarrollado por JM")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        layout.addWidget(author)

        # Web
        web = QLabel(
            '<a href="https://www.posicionamientowebysem.com/" style="color: #ff9800; text-decoration: none;">www.posicionamientowebysem.com</a>'
        )
        web.setAlignment(Qt.AlignmentFlag.AlignCenter)
        web.setOpenExternalLinks(True)
        web.setStyleSheet("font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(web)

        # Descripción
        desc = QLabel(
            "Analizador y gestor de música para DJ.<br>"
            "Herramienta profesional para análisis de audio,<br>"
            "gestión de bibliotecas y modo performance."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #888888; font-size: 11px; line-height: 1.4;")
        layout.addWidget(desc)

        # Tecnologías
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        try:
            from PySide6.QtCore import __version__ as pyside_ver
        except ImportError:
            pyside_ver = "6.x"
        tech = QLabel(
            f"<span style='color: #666666; font-size: 10px;'>"
            f"Python {py_ver} • PySide6 {pyside_ver}<br>"
            f"NumPy • Mutagen • Requests • SoundDevice • SoundFile<br>"
            f"MusicBrainz • AcoustID • Chromaprint • SQLite"
            f"</span>"
        )
        tech.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tech)

        # Copyright
        credits = QLabel("© 2025-2026 JM MusicAnalyzer - Todos los derechos reservados")
        credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits.setStyleSheet("color: #555555; font-size: 10px; margin-top: 5px;")
        layout.addWidget(credits)

        layout.addStretch()

        # Botón Cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedWidth(100)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
