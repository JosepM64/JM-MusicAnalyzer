from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class VuMeterWidget(QWidget):
    levelChanged = Signal(float)

    def __init__(self, orientation=Qt.Orientation.Vertical, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self._level = 0.0
        self._peak = 0.0
        self._peak_hold = 0
        self.setMinimumSize(12, 80)
        self.setUpdatesEnabled(True)

        # Use QProgressBar as fallback for exe compatibility
        self._progress = QProgressBar()
        self._progress.setOrientation(
            Qt.Orientation.Vertical
            if orientation == Qt.Orientation.Vertical
            else Qt.Orientation.Horizontal
        )
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                background-color: #0a0a0a;
                }
            QProgressBar::chunk {
                background-color: #00ff00;
                }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._progress)

        # Timer for forced repaint (fix for PyInstaller/PySide6 bug)
        self._repaint_timer = QTimer(self)
        self._repaint_timer.timeout.connect(self._force_repaint)
        self._repaint_timer.start(50)  # 20fps force repaint

    def _force_repaint(self):
        self._progress.repaint()

    @Slot(float)
    def _updateLevel(self, level):
        self._level = max(0.0, min(1.0, level))
        if self._level > self._peak:
            self._peak = self._level
            self._peak_hold = 15
        elif self._peak_hold > 0:
            self._peak_hold -= 1
        else:
            self._peak = max(self._level, self._peak * 0.92)
        self._progress.setValue(int(self._level * 100))
        self._progress.repaint()

    def setLevel(self, level):
        # Direct update to avoid signal/slot issues in exe
        self._level = max(0.0, min(1.0, level))
        if self._level > self._peak:
            self._peak = self._level
            self._peak_hold = 15
        elif self._peak_hold > 0:
            self._peak_hold -= 1
        else:
            self._peak = max(self._level, self._peak * 0.92)

        self._progress.setValue(int(self._level * 100))

        # Canviar color segons nivell
        if self._level > 0.9:
            color = "#ff0000"  # Vermell (clip)
        elif self._level > 0.7:
            color = "#ff8800"  # Taronja
        elif self._level > 0.5:
            color = "#ffff00"  # Groc
        else:
            color = "#00ff00"  # Verd

        self._progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #333;
                background-color: #0a0a0a;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor(15, 15, 15))

        num_segments = 15
        gap = 1

        seg_h = seg_w = x = y_pos = x_pos = 0
        if self.orientation == Qt.Orientation.Vertical:
            seg_h = (h - gap * (num_segments - 1)) / num_segments
            seg_w = w - 2
            x = 1
        else:
            seg_w = (w - gap * (num_segments - 1)) / num_segments
            seg_h = h - 2
            x_pos = 0
            y_pos = 1

        active = int(self._level * num_segments)
        peak_idx = int(self._peak * num_segments)

        for i in range(num_segments):
            if self.orientation == Qt.Orientation.Vertical:
                y_pos = h - (i + 1) * (seg_h + gap)
                x_pos = x
            else:
                x_pos = i * (seg_w + gap)
                y_pos = 1

            pct = (i + 1) / num_segments

            if i < active or (i == peak_idx - 1 and self._peak > 0.05):
                if pct >= 0.93:
                    color = QColor(220, 20, 20)
                elif pct >= 0.80:
                    color = QColor(255, 140, 0)
                elif pct >= 0.60:
                    color = QColor(255, 220, 0)
                else:
                    color = QColor(0, 180, 0)
            else:
                color = QColor(25, 25, 25)

            if self.orientation == Qt.Orientation.Vertical:
                painter.fillRect(int(x), int(y_pos), int(seg_w), int(seg_h), color)
            else:
                painter.fillRect(int(x_pos), int(y_pos), int(seg_w), int(seg_h), color)

        painter.setPen(QPen(QColor(40, 40, 40), 1))
        painter.drawRect(0, 0, w - 1, h - 1)


class StereoVuMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)

        left_box = QVBoxLayout()
        left_box.setSpacing(0)
        lbl_l = QLabel("L")
        lbl_l.setStyleSheet("color: #888; font-size: 8px; font-weight: bold;")
        lbl_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left = VuMeterWidget(Qt.Orientation.Vertical)
        left_box.addWidget(lbl_l)
        left_box.addWidget(self.left)

        right_box = QVBoxLayout()
        right_box.setSpacing(0)
        lbl_r = QLabel("R")
        lbl_r.setStyleSheet("color: #888; font-size: 8px; font-weight: bold;")
        lbl_r.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right = VuMeterWidget(Qt.Orientation.Vertical)
        right_box.addWidget(lbl_r)
        right_box.addWidget(self.right)

        layout.addLayout(left_box)
        layout.addLayout(right_box)

        self.setMinimumWidth(30)
        self.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #333; border-radius: 2px;"
        )

    def setLevels(self, left_level, right_level):
        self.left.setLevel(left_level)
        self.right.setLevel(right_level)
