import os

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
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
        self.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")
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
        btn_scan.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 6px 12px;"
        )
        btn_all = QPushButton("📂 Escanear TODAS")
        btn_all.setStyleSheet(
            "background-color: #FF9800; color: white; padding: 6px 12px;"
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


def show_tracks_report(parent, title, emoji, tracks, export_prefix, db_manager):
    """
    Fase F (v4.5.0) - Mostra informe de pistes (baixa qualitat / corrompudes)
    amb opció d'exportar a TXT.
    """
    if not tracks:
        QMessageBox.information(parent, title, "No se encontraron pistas.")
        return

    msg = f"Se encontraron {len(tracks)} pistas:\n\n"
    for t in tracks[:20]:
        path = t.get("filepath", "")
        if "bitrate_real" in t:
            msg += f"• {os.path.basename(path)} ({t.get('bitrate_real', 0)} kbps)\n"
        else:
            duration = t.get("duration", 0)
            title_t = t.get("title", "Sin título")
            msg += f"• {os.path.basename(path)}\n   Título: {title_t} | Duración: {duration}s\n"

    if len(tracks) > 20:
        msg += f"\n... y {len(tracks) - 20} más"

    reply = QMessageBox.question(
        parent,
        f"{emoji} {title}",
        msg + "\n\n¿Quieres exportar esta lista a un archivo TXT?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )

    if reply == QMessageBox.Yes:
        path, _ = QFileDialog.getSaveFileName(
            parent, "Exportar lista", f"{export_prefix}.txt", "Texto (*.txt)"
        )
        if path:
            if db_manager.export_tracks_to_txt(tracks, path):
                QMessageBox.information(parent, "Éxito", f"Lista exportada a:\n{path}")
            else:
                QMessageBox.critical(parent, "Error", "No se pudo exportar la lista.")
