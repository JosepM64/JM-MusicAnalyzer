import logging
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    import soundfile as sf

    _HAS_SOUNDDEVICE = True
except ImportError:
    _HAS_SOUNDDEVICE = False


class TracksInspectorDialog(QDialog):
    MODE_LOW_QUALITY = "low_quality"
    MODE_CORRUPTED = "corrupted"

    def __init__(self, parent, title, emoji, tracks, mode, db_manager):
        super().__init__(parent)
        self.setWindowTitle(f"{emoji} {title}")
        self.setMinimumSize(900, 500)
        self.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")

        self._tracks = tracks
        self._mode = mode
        self._db_manager = db_manager
        self._preview_file = None
        self._table = None
        self._lbl_count = None
        self._btn_stop = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._lbl_count = QLabel(f"Se encontraron {len(self._tracks)} pistas")
        self._lbl_count.setStyleSheet("font-size: 13px; padding: 4px;")
        header.addWidget(self._lbl_count)
        header.addStretch()

        self._btn_stop = QPushButton("⏹ Detener preview")
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet(
            "background-color: #d32f2f; color: white; padding: 4px 10px;"
        )
        self._btn_stop.clicked.connect(self._stop_preview)
        header.addWidget(self._btn_stop)

        btn_export = QPushButton("📄 Exportar TXT")
        btn_export.setStyleSheet("padding: 4px 10px;")
        btn_export.clicked.connect(self._on_export)
        header.addWidget(btn_export)

        layout.addLayout(header)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            [
                "Preview",
                "Título",
                "Artista",
                "Duración",
                "Bitrate",
                "Archivo",
                "Acciones",
            ]
        )
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self._table.setColumnWidth(0, 60)
        self._table.setColumnWidth(3, 80)
        self._table.setColumnWidth(4, 80)
        self._table.setColumnWidth(6, 160)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        self._populate_table()

        btn_close = QPushButton("Cerrar")
        btn_close.setStyleSheet("padding: 6px 12px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _populate_table(self):
        self._table.setRowCount(len(self._tracks))
        for row, track in enumerate(self._tracks):
            filepath = track.get("filepath", "")
            title = track.get("title") or "Sense títol"
            artist = track.get("artist") or ""
            duration = track.get("duration", 0)
            bitrate = track.get("bitrate_real") or track.get("bitrate") or 0
            error = track.get("error") or ""

            btn_preview = QPushButton("▶")
            btn_preview.setFixedSize(40, 24)
            btn_preview.setToolTip(f"Pre-escoltar: {os.path.basename(filepath)}")
            btn_preview.clicked.connect(
                lambda checked, fp=filepath, b=btn_preview: self._toggle_preview(fp, b)
            )
            self._table.setCellWidget(row, 0, btn_preview)

            self._table.setItem(row, 1, QTableWidgetItem(title))
            self._table.setItem(row, 2, QTableWidgetItem(artist))
            dur_str = f"{duration:.1f}s" if duration > 0 else "N/A"
            self._table.setItem(row, 3, QTableWidgetItem(dur_str))
            if self._mode == self.MODE_LOW_QUALITY:
                br_str = f"{bitrate} kbps" if bitrate else "N/A"
            else:
                br_str = (
                    error if error else ("N/A" if duration <= 0 else f"{bitrate} kbps")
                )
            self._table.setItem(row, 4, QTableWidgetItem(br_str))
            self._table.setItem(row, 5, QTableWidgetItem(filepath))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(4)

            btn_ignore = QPushButton("✅")
            btn_ignore.setFixedSize(28, 24)
            btn_ignore.setToolTip("Ignorar (eliminar de la llista)")
            btn_ignore.clicked.connect(
                lambda checked, fp=filepath, r=row: self._on_ignore(fp, r)
            )
            actions_layout.addWidget(btn_ignore)

            btn_delete = QPushButton("🗑")
            btn_delete.setFixedSize(28, 24)
            btn_delete.setToolTip("Eliminar archivo del disco")
            btn_delete.clicked.connect(
                lambda checked, fp=filepath, r=row: self._on_delete(fp, r)
            )
            actions_layout.addWidget(btn_delete)

            self._table.setCellWidget(row, 6, actions_widget)

            if duration <= 0:
                for col in range(7):
                    item = self._table.item(row, col)
                    if item:
                        item.setForeground(QColor("#ff6666"))

    def _toggle_preview(self, filepath, button):
        if self._preview_file == filepath:
            self._stop_preview()
            button.setText("▶")
            return

        self._stop_preview()
        if not _HAS_SOUNDDEVICE:
            QMessageBox.warning(self, "Preview", "sounddevice no disponible")
            return

        try:
            data, sr = sf.read(filepath, dtype="float32")
            sd.play(data, sr)
            self._preview_file = filepath
            button.setText("⏹")
            self._btn_stop.setEnabled(True)

            # Auto-stop after duration
            dur_ms = int(len(data) / sr * 1000) + 500
            QTimer.singleShot(dur_ms, self._on_preview_finished)
        except Exception as e:
            logger.warning(f"Error al previsualitzar {filepath}: {e}")
            QMessageBox.warning(
                self, "Error", f"No s'ha pogut reproduir:\n{os.path.basename(filepath)}"
            )

    def _stop_preview(self):
        if _HAS_SOUNDDEVICE:
            sd.stop()
        self._preview_file = None
        self._btn_stop.setEnabled(False)
        for row in range(self._table.rowCount()):
            btn = self._table.cellWidget(row, 0)
            if btn:
                btn.setText("▶")

    def _on_preview_finished(self):
        if self._preview_file:
            self._preview_file = None
            self._btn_stop.setEnabled(False)
            for row in range(self._table.rowCount()):
                btn = self._table.cellWidget(row, 0)
                if btn:
                    btn.setText("▶")

    def _on_ignore(self, filepath, row):
        reply = QMessageBox.question(
            self,
            "Ignorar pista",
            f"Eliminar de la base de datos?\n{os.path.basename(filepath)}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self._db_manager.delete_track(filepath):
                self._table.removeRow(row)
                self._lbl_count.setText(
                    f"Se encontraron {self._table.rowCount()} pistas"
                )
                logger.info(f"Pista ignorada: {filepath}")
            else:
                QMessageBox.critical(self, "Error", "No s'ha pogut eliminar de la BD")

    def _on_delete(self, filepath, row):
        reply = QMessageBox.question(
            self,
            "Eliminar archivo",
            f"ELIMINAR PERMANENTEMENT del disc?\n{filepath}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(filepath)
                logger.info(f"Archivo eliminado: {filepath}")
            except Exception as e:
                logger.error(f"Error eliminando archivo {filepath}: {e}")
                QMessageBox.critical(
                    self, "Error", f"No s'ha pogut eliminar el fitxer:\n{e}"
                )
                return
            self._db_manager.delete_track(filepath)
            self._table.removeRow(row)
            self._lbl_count.setText(f"Se encontraron {self._table.rowCount()} pistas")

    def _on_export(self):
        tracks = []
        for row in range(self._table.rowCount()):
            filepath_item = self._table.item(row, 5)
            if filepath_item:
                tracks.append({"filepath": filepath_item.text()})
        if not tracks:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar lista",
            f"pistas_{self._mode}.txt",
            "Texto (*.txt)",
        )
        if path:
            if self._db_manager.export_tracks_to_txt(tracks, path):
                QMessageBox.information(self, "Èxit", f"Llista exportada a:\n{path}")
            else:
                QMessageBox.critical(self, "Error", "No s'ha pogut exportar la llista")
