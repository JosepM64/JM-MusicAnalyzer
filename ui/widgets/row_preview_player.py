from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class RowPreviewPlayer(QWidget):
    """
    Fase E (v4.4.0) - Widget de preescolta CUE per files de playlist.

    Botó que permet preescoltar una pista pels auriculars (CUE).
    Quan està activat (checked=True), mostra estil ressaltat.

    Senyals:
    - cueClicked(str): emés amb el filepath quan es clica
    """

    cueClicked = Signal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(2)
        self.btn_cue = QPushButton("\U0001f3a7")
        self.btn_cue.setFixedSize(24, 18)
        self.btn_cue.setCheckable(True)
        self.btn_cue.setStyleSheet("""
            QPushButton { background-color: #333; color: cyan; font-size: 10px; border-radius: 2px; padding: 0px; }
            QPushButton:checked { background-color: #00d4ff; color: black; font-weight: bold; }
        """)
        self.btn_cue.setToolTip("Preescucha en auriculares")
        self.btn_cue.clicked.connect(lambda: self.cueClicked.emit(self.filepath))
        layout.addWidget(self.btn_cue)
