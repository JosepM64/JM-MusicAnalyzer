import logging
import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class CoverWidget(QWidget):
    """
    Widget especialitzat en mostrar i gestionar la carátula del àlbum.

    Fase D (v4.3.0) - Millorat amb botons d'acció:
    - Guardar carátula a disc
    - Obrir carátula al visor del sistema
    - El botó de guardar només apareix si hi ha carátula

    Senyals:
    - coverSaveRequested: l'usuari vol guardar la carátula
    - coverOpenRequested: l'usuari vol obrir la carátula externament
    """

    coverSaveRequested = Signal()
    coverOpenRequested = Signal()

    def __init__(self, size=150):
        super().__init__()
        self.cover_size = size
        self._cover_data = None
        self._mime_type = "image/jpeg"
        self._setup_ui()

    def _setup_ui(self):
        v_layout = QVBoxLayout(self)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)

        self.lbl_image = QLabel()
        self.lbl_image.setFixedSize(QSize(self.cover_size, self.cover_size))
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 2px dashed #3f3f3f;
                border-radius: 4px;
                color: #555555;
                font-size: 9px;
            }
        """)
        self.lbl_image.setText("SIN\nCAR\u00c1TULA")
        v_layout.addWidget(self.lbl_image)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(2)

        self.btn_save = QPushButton("\U0001f4be")
        self.btn_save.setToolTip("Guardar car\u00e1tula como imagen")
        self.btn_save.setFixedSize(24, 18)
        self.btn_save.setStyleSheet(
            "QPushButton { font-size: 9px; background: #444; border-radius: 2px; border: none; } QPushButton:hover { background: #666; }"
        )
        self.btn_save.setVisible(False)
        self.btn_save.clicked.connect(self._on_save_cover)
        btn_row.addWidget(self.btn_save)

        self.btn_open = QPushButton("\U0001f50d")
        self.btn_open.setToolTip("Abrir car\u00e1tula en visor externo")
        self.btn_open.setFixedSize(24, 18)
        self.btn_open.setStyleSheet(
            "QPushButton { font-size: 9px; background: #444; border-radius: 2px; border: none; } QPushButton:hover { background: #666; }"
        )
        self.btn_open.setVisible(False)
        self.btn_open.clicked.connect(self._on_open_cover)
        btn_row.addWidget(self.btn_open)

        btn_row.addStretch()
        v_layout.addLayout(btn_row)

    def set_cover(self, data: bytes, mime_type: str = "image/jpeg"):
        if not data:
            self.clear()
            return
        try:
            image = QImage()
            if not image.loadFromData(data):
                self.clear()
                return
            self._cover_data = data
            self._mime_type = mime_type
            pixmap = QPixmap.fromImage(image)
            scaled_pixmap = pixmap.scaled(
                self.cover_size,
                self.cover_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_image.setPixmap(scaled_pixmap)
            self.lbl_image.setStyleSheet(
                "border: 1px solid #3f3f3f; background-color: #000; border-radius: 4px;"
            )
            self.btn_save.setVisible(True)
            self.btn_open.setVisible(True)
        except Exception as e:
            logger.error(f"Error al procesar car\u00e1tula: {e}")
            self.clear()

    def clear(self):
        self._cover_data = None
        if self.lbl_image:
            self.lbl_image.setPixmap(QPixmap())
            self.lbl_image.setText("SIN\nCAR\u00c1TULA")
            self.lbl_image.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    border: 2px dashed #3f3f3f;
                    border-radius: 4px;
                    color: #555555;
                    font-size: 9px;
                }
            """)
        self.btn_save.setVisible(False)
        self.btn_open.setVisible(False)

    def _on_save_cover(self):
        if not self._cover_data:
            return
        from services.cover_art_service import CoverArtService

        fmt = CoverArtService.detect_image_format(self._cover_data)
        ext = fmt if fmt != "unknown" else "jpg"
        default_name = f"cover.{ext}"
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar car\u00e1tula",
            default_name,
            f"Im\u00e1genes (*.{ext});;Todos los archivos (*)",
        )
        if dest:
            if CoverArtService.save_to_file(self._cover_data, dest):
                QMessageBox.information(
                    self, "Guardado", f"Car\u00e1tula guardada en:\n{dest}"
                )
            else:
                QMessageBox.warning(
                    self, "Error", "No se pudo guardar la car\u00e1tula."
                )

    def _on_open_cover(self):
        if not self._cover_data:
            return
        import tempfile

        from services.cover_art_service import CoverArtService

        fmt = CoverArtService.detect_image_format(self._cover_data)
        ext = fmt if fmt != "unknown" else "jpg"
        tmp = os.path.join(tempfile.gettempdir(), f"jm_cover_preview.{ext}")
        if CoverArtService.save_to_file(self._cover_data, tmp):
            os.startfile(tmp)
