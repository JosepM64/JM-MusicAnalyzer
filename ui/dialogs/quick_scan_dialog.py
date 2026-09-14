import os

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class QuickScanDialog(QDialog):
    """
    Fase F (v4.5.0) - Diàleg per seleccionar carpeta de favoritos a escanejar.

    Retorna:
    - exec() == Accepted i selected_idx >= 0: escanejar carpeta seleccionada
    - exec() == Accepted i selected_idx == -1: escanejar TOTES les carpetes
    - exec() == Rejected: cancel·lat
    """

    def __init__(self, favorites, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Escaneo Rápido - Seleccionar carpeta")
        self.setMinimumWidth(400)
        try:
            from ui.styles import DARK_DIALOG_STYLE

            self.setStyleSheet(DARK_DIALOG_STYLE)
        except Exception:
            self.setStyleSheet("background-color: #1a1a1a; color: #ffffff;")
        self._selected_idx = 0
        self._paths = [
            f.get("path", f) if isinstance(f, dict) else f for f in favorites
        ]
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Selecciona la carpeta a escanear:"))

        self._combo = QComboBox()
        self._combo.addItems([os.path.basename(p) for p in self._paths])
        layout.addWidget(self._combo)

        btn_layout = QHBoxLayout()
        btn_scan = QPushButton("🔍 Escanear")
        try:
            from ui.tokens import RADIUS_MD, SUCCESS, TEXT_100

            btn_scan.setStyleSheet(
                f"background-color: {SUCCESS}; color: {TEXT_100}; padding: 6px 12px; border-radius: {RADIUS_MD}px; font-weight: 600; font-family: 'Segoe UI', sans-serif;"
            )
        except Exception:
            btn_scan.setStyleSheet(
                "background-color: #00aa00; color: white; padding: 6px 12px; border-radius: 4px; font-weight: 600;"
            )
        btn_all = QPushButton("📂 Escanear TODAS")
        try:
            from ui.tokens import RADIUS_MD, TEXT_100, WARNING

            btn_all.setStyleSheet(
                f"background-color: {WARNING}; color: {TEXT_100}; padding: 6px 12px; border-radius: {RADIUS_MD}px; font-weight: 600; font-family: 'Segoe UI', sans-serif;"
            )
        except Exception:
            btn_all.setStyleSheet(
                "background-color: #ff9800; color: white; padding: 6px 12px; border-radius: 4px; font-weight: 600;"
            )
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("padding: 6px 12px;")

        btn_scan.clicked.connect(self._on_scan_single)
        btn_all.clicked.connect(self._on_scan_all)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_scan)
        btn_layout.addWidget(btn_all)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _on_scan_single(self):
        self._selected_idx = self._combo.currentIndex()
        self.accept()

    def _on_scan_all(self):
        self._selected_idx = -1
        self.accept()

    def get_selected_path(self):
        if self._selected_idx == -1:
            return None
        if 0 <= self._selected_idx < len(self._paths):
            return self._paths[self._selected_idx]
        return None

    def get_all_paths(self):
        return list(self._paths)

    def is_scan_all(self):
        return self._selected_idx == -1
