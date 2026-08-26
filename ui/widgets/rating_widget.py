import math

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPolygonF
from PySide6.QtWidgets import QWidget


class RatingWidget(QWidget):
    ratingChanged = Signal(float)

    def __init__(self, rating=0, star_size=24, editable=True):
        super().__init__()
        self.rating = float(rating) if rating is not None else 0.0
        self.star_size = star_size
        self.max_stars = 5
        self.editable = editable
        self.hover_rating = -1  # Para mostrar preview
        self.setMouseTracking(True)
        # Hacer el widget más grande para mejor usabilidad
        self.setFixedSize(
            QSize(self.star_size * self.max_stars + 20, self.star_size + 16)
        )
        if self.editable:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def set_rating(self, rating):
        self.rating = float(rating) if rating is not None else 0.0
        self.update()

    def enterEvent(self, event):
        if self.editable:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def leaveEvent(self, event):
        self.hover_rating = -1
        self.update()

    def mouseMoveEvent(self, event):
        if not self.editable:
            return
        try:
            x = event.position().x() - 10  # Margen
        except Exception:
            x = event.x() - 10

        half_star = self.star_size / 2
        self.hover_rating = max(0, min(5, round(x / half_star) / 2))
        self.update()

    def mousePressEvent(self, event):
        if not self.editable:
            return

        try:
            x = event.position().x() - 10  # Margen
        except Exception:
            x = event.x() - 10

        # Calcular rating basado en posición
        if x < 0:
            new_rating = 0.0
        else:
            # Dividir en 10 partes (5 estrellas * 2 mitades)
            new_rating = round(x / (self.star_size / 2)) / 2
            new_rating = max(0.0, min(5.0, new_rating))

        # Click en la misma estrella = borrar rating
        if abs(new_rating - self.rating) < 0.1:
            new_rating = 0.0

        self.set_rating(new_rating)
        self.ratingChanged.emit(self.rating)
        self.hover_rating = -1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Usar rating actual o hover si está disponible
        display_rating = self.hover_rating if self.hover_rating >= 0 else self.rating

        for i in range(self.max_stars):
            star_value = i + 1
            filled = star_value <= display_rating
            half_filled = not filled and (star_value - 0.5) <= display_rating

            x_pos = 10 + i * self.star_size  # Margen de 10px
            if filled:
                self._draw_star(painter, x_pos, 8, True)
            elif half_filled:
                self._draw_half_star(painter, x_pos, 8)
            else:
                self._draw_star(painter, x_pos, 8, False)

    def _draw_star(self, painter, x, y, filled):
        if filled:
            color = QColor("#FFD700")
        else:
            color = QColor("#444444")
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen if filled else QColor("#666666"))

        points = QPolygonF()
        center = QPointF(x + self.star_size / 2, y + self.star_size / 2)
        radius = self.star_size / 2 * 0.85
        inner_radius = radius * 0.4
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            r = radius if i % 2 == 0 else inner_radius
            points.append(
                QPointF(
                    center.x() + r * math.cos(angle), center.y() + r * math.sin(angle)
                )
            )
        painter.drawPolygon(points)

    def _draw_half_star(self, painter, x, y):
        half_width = self.star_size / 2
        center = QPointF(x + half_width, y + self.star_size / 2)
        radius = self.star_size / 2 * 0.85
        inner_radius = radius * 0.4

        painter.setBrush(QColor("#FFD700"))
        painter.setPen(Qt.PenStyle.NoPen)

        points_left = QPolygonF()
        points_left.append(QPointF(center.x(), center.y() - radius))
        for i in range(1, 10):
            angle = i * math.pi / 5 - math.pi / 2
            r = radius if i % 2 == 0 else inner_radius
            px = center.x() + r * math.cos(angle)
            if px <= center.x():
                points_left.append(QPointF(px, center.y() + r * math.sin(angle)))
        points_left.append(QPointF(center.x(), center.y() + radius))
        painter.drawPolygon(points_left)

        points_right = QPolygonF()
        points_right.append(QPointF(center.x(), center.y() - radius))
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            r = radius if i % 2 == 0 else inner_radius
            px = center.x() + r * math.cos(angle)
            if px >= center.x():
                points_right.append(QPointF(px, center.y() + r * math.sin(angle)))
        points_right.append(QPointF(center.x(), center.y() + radius))

        painter.setBrush(QColor("#444444"))
        painter.drawPolygon(points_right)
