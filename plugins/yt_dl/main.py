"""Plugin yt_dl: Importar àudio des de YouTube amb yt-dlp."""

import logging
import tempfile
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from plugins.yt_dl.analyzer import analyze_file, get_quality_label
from plugins.yt_dl.downloader import DownloadWorker, PreviewDownloader, search_youtube

logger = logging.getLogger(__name__)


class PreviewPlayer:
    """Reproductor d'àudio local amb sounddevice (sense QtMultimedia)."""

    def __init__(self):
        self._stream = None
        self._data = None
        self._samplerate = 44100
        self._position = 0
        self._playing = False

    def load(self, filepath):
        self.stop()
        self._data, self._samplerate = sf.read(filepath, dtype="float32")
        self._position = 0

    def play(self):
        if self._data is None:
            return
        self._playing = True
        self._start_stream()

    def stop(self):
        self._playing = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._position = 0

    def _start_stream(self):
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass

        channels = self._data.shape[1] if len(self._data.shape) > 1 else 2

        def callback(outdata, frames, _time_info, _status):
            if not self._playing:
                outdata.fill(0)
                return
            start = self._position
            end = start + frames
            if start >= len(self._data):
                outdata.fill(0)
                self._playing = False
                return
            if end > len(self._data):
                chunk = self._data[start:]
                outdata[: len(chunk)] = chunk
                outdata[len(chunk) :].fill(0)
                self._position = len(self._data)
                self._playing = False
            else:
                outdata[:] = self._data[start:end]
                self._position = end

        self._stream = sd.OutputStream(
            samplerate=self._samplerate,
            channels=channels,
            callback=callback,
            blocksize=1024,
        )
        self._stream.start()

    @property
    def is_playing(self):
        return self._playing


class YouTubeImportDialog(QDialog):
    """Diàleg per importar àudio des de YouTube."""

    download_completed = Signal(str, list)

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Importar de YouTube")
        self.setMinimumSize(750, 550)
        self.worker = None
        self.results = []
        self._player = PreviewPlayer()
        self._preview_downloader = None
        self._temp_dir = None
        self._preview_timer = QTimer()
        self._preview_timer.setInterval(200)
        self._preview_timer.timeout.connect(self._on_preview_tick)
        self._setup_ui()

    # ── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        search_group = QGroupBox("Cerca")
        search_layout = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Cerca o enganxa URL de YouTube...")
        self.input_search.returnPressed.connect(self._on_search)
        self.btn_search = QPushButton("🔍 Cercar")
        self.btn_search.clicked.connect(self._on_search)
        search_layout.addWidget(self.input_search)
        search_layout.addWidget(self.btn_search)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Seleccionar", "Títol", "Durada", ""])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)
        self.table.itemChanged.connect(self._on_table_item_changed)

        select_all_row = QHBoxLayout()
        self.chk_select_all = QCheckBox("Seleccionar / desseleccionar tot")
        self.chk_select_all.setChecked(False)
        self.chk_select_all.stateChanged.connect(self._on_select_all)
        select_all_row.addWidget(self.chk_select_all)
        select_all_row.addStretch()
        layout.addLayout(select_all_row)
        layout.addWidget(self.table)

        preview_layout = QHBoxLayout()
        self.btn_stop = QPushButton("⏹  Aturar")
        self.btn_stop.clicked.connect(self._on_stop_preview)
        self.btn_stop.setEnabled(False)
        self.lbl_preview_status = QLabel("")
        self.lbl_preview_status.setStyleSheet("color: #00d4ff; font-size: 11px;")
        preview_layout.addWidget(self.btn_stop)
        preview_layout.addWidget(self.lbl_preview_status)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)

        folder_group = QGroupBox("Carpeta destí")
        folder_layout = QHBoxLayout()
        self.input_folder = QLineEdit()
        try:
            from app_state import AppState
            last_folder = AppState().settings.get("last_youtube_folder", "")
        except Exception:
            last_folder = ""
        if last_folder:
            current_path = last_folder
        elif isinstance(self.api, dict):
            current_path = self.api.get("current_path", "")
        else:
            current_path = getattr(getattr(self.api, "active_panel", None), "current_path", "")
        self.input_folder.setText(current_path or "C:\\")
        self.btn_folder = QPushButton("📁 Seleccionar")
        self.btn_folder.clicked.connect(self._select_folder)
        folder_layout.addWidget(self.input_folder)
        folder_layout.addWidget(self.btn_folder)
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)

        options_group = QGroupBox("Opcions")
        options_layout = QVBoxLayout()
        self.chk_metadata = QCheckBox("Afegir metadades ID3")
        self.chk_metadata.setChecked(True)
        self.chk_analyze = QCheckBox("Analitzar després de descarregar")
        self.chk_analyze.setChecked(True)
        self.chk_overwrite = QCheckBox("Sobreescriure si existeix")
        options_layout.addWidget(self.chk_metadata)
        options_layout.addWidget(self.chk_analyze)
        options_layout.addWidget(self.chk_overwrite)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)

        btn_layout = QHBoxLayout()
        self.btn_download = QPushButton("📥 Descarregar")
        self.btn_download.clicked.connect(self._on_download)
        self.btn_download.setEnabled(False)
        self.btn_cancel = QPushButton("Cancel·lar")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setEnabled(False)
        btn_layout.addWidget(self.btn_download)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    # ── cerca ──────────────────────────────────────────────────────────

    def _on_search(self):
        query = self.input_search.text().strip()
        if not query:
            return

        self.lbl_status.setText("Cercant...")
        self.btn_search.setEnabled(False)

        self.results = search_youtube(query)

        self.table.setRowCount(len(self.results))
        for i, r in enumerate(self.results):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(i, 0, chk)
            self.table.setItem(i, 1, QTableWidgetItem(r["title"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["duration"]))

            btn_play = QPushButton("▶")
            btn_play.setFixedSize(28, 24)
            btn_play.setToolTip("Previsualitzar àudio")
            btn_play.clicked.connect(lambda checked, row=i: self._start_preview(row))
            self.table.setCellWidget(i, 3, btn_play)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(3, 36)

        self.btn_search.setEnabled(True)
        self.btn_download.setEnabled(len(self.results) > 0)
        self.lbl_status.setText(f"{len(self.results)} resultats trobats")
        self._sync_select_all()

    def _on_select_all(self, state):
        checked = state == Qt.CheckState.Checked.value
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(
                    Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )

    def _on_table_item_changed(self, item):
        if item and item.column() == 0:
            self._sync_select_all()

    def _sync_select_all(self):
        any_row = False
        all_checked = True
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                any_row = True
                if item.checkState() != Qt.CheckState.Checked:
                    all_checked = False
        self.chk_select_all.blockSignals(True)
        self.chk_select_all.setChecked(all_checked if any_row else False)
        self.chk_select_all.blockSignals(False)

    # ── carpetes ───────────────────────────────────────────────────────

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", self.input_folder.text())
        if folder:
            self.input_folder.setText(folder)

    # ── previsualització ────────────────────────────────────────────────

    def _on_table_double_clicked(self, row, _column):
        self._start_preview(row)

    def _get_temp_dir(self):
        if self._temp_dir is None:
            self._temp_dir = tempfile.mkdtemp(prefix="yt_preview_")
        return self._temp_dir

    def _start_preview(self, row):
        if row < 0 or row >= len(self.results):
            return

        self._stop_preview_internal()
        self.table.selectRow(row)

        self.lbl_preview_status.setText("⏳ baixant previsualització...")
        self.lbl_status.setText("Baixant previsualització (30s)...")
        self.btn_stop.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)

        self._preview_row = row
        video_url = self.results[row]["url"]
        self._preview_downloader = PreviewDownloader(video_url, self._get_temp_dir())
        self._preview_downloader.preview_ready.connect(self._on_preview_ready)
        self._preview_downloader.error_ocurred.connect(self._on_preview_error)
        self._preview_downloader.finished.connect(self._on_preview_finished)
        self._preview_downloader.start()

    def _on_preview_ready(self, filepath):
        self.progress_bar.setVisible(False)
        self._player.load(filepath)
        self._player.play()
        self._preview_timer.start()
        self.lbl_preview_status.setText("▶ Reproduint previsualització...")
        self.lbl_status.setText("")
        self.btn_stop.setEnabled(True)

    def _on_preview_error(self, msg):
        self.progress_bar.setVisible(False)
        self.lbl_preview_status.setText("")
        self.lbl_status.setText(f"❌ Error de previsualització: {msg}")

    def _on_preview_finished(self):
        self._preview_timer.stop()
        self.btn_stop.setEnabled(self._player.is_playing)

    def _on_preview_tick(self):
        if not self._player.is_playing:
            self._preview_timer.stop()
            self.btn_stop.setEnabled(False)
            self.lbl_preview_status.setText("")

    def _on_stop_preview(self):
        self._stop_preview_internal()

    def _stop_preview_internal(self):
        self._player.stop()
        self._preview_timer.stop()
        self.btn_stop.setEnabled(False)
        self.lbl_preview_status.setText("")
        self.progress_bar.setVisible(False)
        if self._preview_downloader and self._preview_downloader.isRunning():
            self._preview_downloader.cancel()
            self._preview_downloader.wait(2000)

    def _cleanup_temp(self):
        if self._temp_dir is None:
            return
        try:
            import shutil
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass
        self._temp_dir = None

    # ── descàrrega ─────────────────────────────────────────────────────

    def _on_download(self):
        urls = []
        for i in range(self.table.rowCount()):
            chk = self.table.item(i, 0)
            if chk.checkState() == Qt.CheckState.Checked and i < len(self.results):
                # Usar la URL exacta del resultat marcat: la descàrrega ha de
                # coincidir amb el que s'ha vist/previsualitzat (abans es feia
                # ytsearch1:<titol>, que podia baixar un vídeo diferent)
                urls.append(self.results[i]["url"])

        if not urls:
            self.lbl_status.setText("Marca almenys un resultat per descarregar")
            return

        self._stop_preview_internal()

        self.btn_download.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self.worker = DownloadWorker(urls, self.input_folder.text())
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.lbl_status.setText(text)

    def _on_finished(self, downloaded):
        self.progress_bar.setVisible(False)
        self.btn_download.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if self.chk_analyze.isChecked():
            for filepath in downloaded:
                info = analyze_file(filepath)
                if info:
                    quality = get_quality_label(info["bitrate"])
                    self.lbl_status.setText(
                        f"✅ {info['filename']} - {quality} ({info['bitrate']} bps)",
                    )

        self.lbl_status.setText(f"✅ {len(downloaded)} fitxers descarregats")
        if downloaded:
            # Tancar el diàleg ABANS de notificar la finestra principal: el handler
            # de download_completed navega a la carpeta i en carrega el contingut
            # (síncron), cosa que congelaria aquest diàleg si seguís obert.
            self.accept()
            self.download_completed.emit(self.input_folder.text(), downloaded)

    def _on_error(self, msg):
        self.lbl_status.setText(f"❌ {msg}")

    def _on_cancel(self):
        if self.worker:
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.lbl_status.setText("Cancel·lat")

    # ── neteja ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._stop_preview_internal()
        self._cleanup_temp()
        super().closeEvent(event)


def register(api):
    api.add_action("import_youtube", "📥 Importar de YouTube", lambda: _open_dialog(api))


def _open_dialog(api):
    dialog = YouTubeImportDialog(api, api.get_parent_window())
    dialog.exec()
