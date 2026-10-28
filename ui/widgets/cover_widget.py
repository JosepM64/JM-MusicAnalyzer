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

from ui.styles import icon_btn_qss

logger = logging.getLogger(__name__)


class CoverWidget(QWidget):
    """
    Widget especialitzat en mostrar i gestionar la carátula del àlbum.

    Fase D (v4.3.0) - Millorat amb botons d'acció:
    - Guardar carátula a disc
    - Obrir carátula al visor del sistema
    - El botó de guardar només apareix si hi ha carátula
    - Afegir/canviar carátula des d'un JPG/PNG (només mode edició)
    """

    coverChanged = Signal()

    def __init__(self, size=150, editable=True):
        super().__init__()
        self.cover_size = size
        self.editable = editable
        self._cover_data = None
        self._mime_type = "image/jpeg"
        self._pending_cover = False
        self._removed = False
        self._setup_ui()
        self._update_edit_buttons()

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
            icon_btn_qss(9, "background: #444; border-radius: 2px; border: none;")
            + "QPushButton:hover { background: #666; }"
        )
        self.btn_save.setVisible(False)
        self.btn_save.clicked.connect(self._on_save_cover)
        btn_row.addWidget(self.btn_save)

        self.btn_open = QPushButton("\U0001f50d")
        self.btn_open.setToolTip("Abrir car\u00e1tula en visor externo")
        self.btn_open.setFixedSize(24, 18)
        self.btn_open.setStyleSheet(
            icon_btn_qss(9, "background: #444; border-radius: 2px; border: none;")
            + "QPushButton:hover { background: #666; }"
        )
        self.btn_open.setVisible(False)
        self.btn_open.clicked.connect(self._on_open_cover)
        btn_row.addWidget(self.btn_open)

        self.btn_add = QPushButton("\U0001f4c2")
        self.btn_add.setToolTip("Añadir / cambiar carátula desde imagen (JPG/PNG)")
        self.btn_add.setFixedSize(24, 18)
        self.btn_add.setStyleSheet(
            icon_btn_qss(9, "background: #444; border-radius: 2px; border: none;")
            + "QPushButton:hover { background: #666; }"
        )
        self.btn_add.clicked.connect(self._on_add_cover)
        btn_row.addWidget(self.btn_add)

        self.btn_remove = QPushButton("\U0001f5d1")
        self.btn_remove.setToolTip("Quitar carátula (se aplica al GUARDAR)")
        self.btn_remove.setFixedSize(24, 18)
        self.btn_remove.setStyleSheet(
            icon_btn_qss(9, "background: #444; border-radius: 2px; border: none;")
            + "QPushButton:hover { background: #666; }"
        )
        self.btn_remove.clicked.connect(self._on_remove_cover)
        btn_row.addWidget(self.btn_remove)

        btn_row.addStretch()
        v_layout.addLayout(btn_row)

    def _update_edit_buttons(self):
        show_add = self.editable
        show_remove = self.editable and bool(self._cover_data)
        self.btn_add.setVisible(show_add)
        self.btn_remove.setVisible(show_remove)

    def has_pending_cover(self) -> bool:
        return self._pending_cover and bool(self._cover_data)

    def is_removed(self) -> bool:
        return self._removed

    def pending_cover_data(self):
        return (self._cover_data, self._mime_type) if self.has_pending_cover() else (None, None)

    def clear_pending_flag(self):
        self._pending_cover = False
        self._removed = False

    def set_editable(self, editable: bool):
        self.editable = editable
        self._update_edit_buttons()

    def set_cover(self, data: bytes, mime_type: str = "image/jpeg", from_user: bool = False):
        if not data:
            self.clear()
            return
        try:
            image = QImage()
            if not image.loadFromData(data):
                if not from_user:
                    self.clear()
                return
            self._cover_data = data
            self._mime_type = mime_type
            if from_user:
                self._pending_cover = True
                self._removed = False
            else:
                self._pending_cover = False
                self._removed = False
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
            self._update_edit_buttons()
            if from_user:
                self.coverChanged.emit()
        except Exception as e:
            logger.error(f"Error al procesar car\u00e1tula: {e}")
            if not from_user:
                self.clear()

    def set_cover_from_file(self, path: str) -> bool:
        """Carga una carátula desde un JPG/PNG de disco (preview, pendiente de GUARDAR)."""
        try:
            if not path or not os.path.exists(path):
                return False
            with open(path, "rb") as f:
                data = f.read()
            if not data:
                return False
            image = QImage()
            if not image.loadFromData(data):
                return False
            ext = os.path.splitext(path)[1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            self.set_cover(data, mime, from_user=True)
            return True
        except Exception as e:
            logger.error(f"Error cargando carátula desde {path}: {e}")
            return False

    def clear(self, from_user: bool = False):
        if from_user:
            # Marcar para borrar al GUARDAR, pero mantener preview "SIN CARÁTULA"
            self._removed = True
            self._pending_cover = False
        else:
            self._removed = False
            self._pending_cover = False
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
        self._update_edit_buttons()
        if from_user:
            self.coverChanged.emit()

    def _on_add_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar carátula",
            "",
            "Imágenes (*.jpg *.jpeg *.png);;JPEG (*.jpg *.jpeg);;PNG (*.png);;Todos (*)",
        )
        if not path:
            return
        if not self.set_cover_from_file(path):
            QMessageBox.warning(
                self, "Carátula", "No se pudo leer la imagen seleccionada."
            )

    def _on_remove_cover(self):
        if not self._cover_data:
            return
        self.clear(from_user=True)

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
