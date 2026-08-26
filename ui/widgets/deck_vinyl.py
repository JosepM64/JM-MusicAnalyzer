import logging

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

logger = logging.getLogger(__name__)

# Colores Camelot Wheel (12 posiciones, A=mayor brillante, B=minor más oscuro)
CAMELOT_COLORS = {
    "1A": "#ff6666",
    "1B": "#cc0000",  # Rojo
    "2A": "#ff9933",
    "2B": "#cc5500",  # Naranja
    "3A": "#ffcc00",
    "3B": "#cccc00",  # Amarillo
    "4A": "#66ff66",
    "4B": "#00cc00",  # Verde lima
    "5A": "#00ccff",
    "5B": "#0099cc",  # Cyan
    "6A": "#6666ff",
    "6B": "#0000cc",  # Azul
    "7A": "#9966ff",
    "7B": "#6600cc",  # Púrpura
    "8A": "#ff66ff",
    "8B": "#cc00cc",  # Magenta
    "9A": "#ff66b2",
    "9B": "#cc0088",  # Rosa
    "10A": "#66ffcc",
    "10B": "#00aacc",  # Turquesa
    "11A": "#ccff66",
    "11B": "#88cc00",  # Verde amarillento
    "12A": "#ff9966",
    "12B": "#cc6600",  # Melocotón
}


class VinylWidget(QWidget):
    def __init__(self, size=160):
        super().__init__()
        self.setMinimumSize(max(size // 2, 80), max(size // 2, 80))
        self.setMaximumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.angle = 0.0
        self._pixmap = None
        self._is_spinning = False
        self._cached_scaled = None
        self._cached_diameter = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(33)

    def set_cover(self, data):
        if not data:
            self._pixmap = None
        else:
            img = QImage.fromData(data)
            self._pixmap = QPixmap.fromImage(img)
        self._cached_scaled = None
        self.update()

    def set_spinning(self, spinning: bool):
        self._is_spinning = spinning

    def _update_animation(self):
        if self._is_spinning:
            self.angle = (self.angle + 3.0) % 360  # 3 grados por frame = más fluido
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()
        diameter = min(rect.width(), rect.height())
        radius = diameter // 2
        center = rect.center()
        painter.setBrush(QBrush(QColor(10, 10, 10)))
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.drawEllipse(center, radius, radius)
        grad = QConicalGradient(QPointF(center), self.angle)
        grad.setColorAt(0, QColor(255, 255, 255, 20))
        grad.setColorAt(1, QColor(255, 255, 255, 20))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)
        label_radius = radius * 0.95  # Caràtula gairebé 100%
        painter.save()
        painter.translate(center)
        painter.rotate(self.angle)
        if self._pixmap and not self._pixmap.isNull():
            diam = int(label_radius * 2)
            if self._cached_scaled is None or self._cached_diameter != diam:
                self._cached_scaled = self._pixmap.scaled(
                    diam,
                    diam,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._cached_diameter = diam
            clip_path = QPainterPath()
            clip_path.addEllipse(QPointF(0, 0), label_radius, label_radius)
            painter.setClipPath(clip_path)
            painter.drawPixmap(
                int(-label_radius), int(-label_radius), self._cached_scaled
            )
        else:
            painter.setBrush(QColor(40, 40, 40))
            painter.drawEllipse(QPointF(0, 0), label_radius, label_radius)
        painter.restore()


class GenreLabel(QLabel):
    """Label de gènere amb gradient animat dinàmic."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._hue = 0  # Hue per canviar colors dinàmicament
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_gradient)
        self._timer.start(2000)  # Canvia cada 2 segons
        self._update_style()

    def _update_gradient(self):
        """Actualitza el gradient amb nous colors."""
        self._hue = (self._hue + 60) % 360  # Rota el hue
        self._update_style()

    def _update_style(self):
        """Actualitza l'estil amb nous colors basats en el hue."""
        # Genera colors basats en el hue actual
        color1 = QColor.fromHsl(self._hue % 360, 200, 180)
        color2 = QColor.fromHsl((self._hue + 180) % 360, 200, 180)

        self.setStyleSheet(f"""
            QLabel {{
                font-weight: bold; 
                font-size: 14px;
                padding: 6px 12px;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color1.name()}, stop:1 {color2.name()});
            }}
        """)

    def setText(self, text):
        super().setText(text.upper() if text else "")
        self._update_style()


GENRE_COLORS = {
    "swing": "#ff6600",
    "blues": "#0066ff",
    "disco": "#ff00ff",
    "jazz": "#6600ff",
    "rock": "#00aaff",
    "pop": "#ff00aa",
    "techno": "#00ff00",
    "house": "#aa00ff",
}


class DeckVinylMixin:
    def set_genre(self, genre):
        if not genre:
            self.lbl_genre_big.setText("")
            self.lbl_genre_big.setFixedHeight(0)
        else:
            color = GENRE_COLORS.get(genre.lower(), "#aaaaaa")
            self.lbl_genre_big.setText(
                f"<span style='color:{color}'>{genre.upper()}</span>"
            )
            self.lbl_genre_big.setFixedHeight(22)

    def set_key(self, key):
        if not key:
            self.lbl_key_big.setText("")
            self.lbl_key_big.setFixedHeight(0)
        else:
            key_str = str(key).upper().strip()
            letra = key_str[-1] if key_str[-1] in "AB" else ""
            numero = key_str[:-1] if letra else key_str
            camelot_key = f"{numero}{letra}" if letra else key_str
            color = CAMELOT_COLORS.get(camelot_key, "#aaaaaa")
            self.lbl_key_big.setText(f"<span style='color:{color}'>{key_str}</span>")
            self.lbl_key_big.setFixedHeight(18)
