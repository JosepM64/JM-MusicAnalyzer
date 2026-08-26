from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QLabel, QWidget

from core.models import TechnicalInfo


class TechnicalPanel(QGroupBox):
    def __init__(self):
        super().__init__("Información Técnica")
        self.labels = {}
        self.status_indicator = None
        self.status_detail = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(2)

        fields = [
            ("Bitrate:", "bitrate"),
            ("Bitrate Real:", "bitrate_real"),
            ("Frec.:", "sample_rate"),
            ("Canales:", "channels"),
            ("Modo:", "channel_mode"),
            ("Duración:", "duration"),
            ("Tamaño:", "file_size"),
            ("ID3:", "id3_version"),
            ("Creado:", "file_created"),
            ("Modif.:", "file_modified"),
        ]

        for i, (text, key) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2
            t_label = QLabel(text)
            t_label.setStyleSheet("font-weight: bold; color: #555; font-size: 10px;")

            v_label = QLabel("N/A")
            v_label.setStyleSheet("color: #000; font-size: 10px;")

            layout.addWidget(t_label, row, col)
            layout.addWidget(v_label, row, col + 1)
            self.labels[key] = v_label

        # --- Fila de verificación espectral (fila 5, ocupa todo el ancho) ---
        row_spectral = 5

        self.status_indicator = QLabel("")
        self.status_indicator.setFixedWidth(20)
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_indicator.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.status_detail = QLabel("")
        self.status_detail.setStyleSheet("font-size: 9px;")
        self.status_detail.setWordWrap(True)

        spectral_container = QWidget()
        spectral_layout = QHBoxLayout(spectral_container)
        spectral_layout.setContentsMargins(0, 2, 0, 0)
        spectral_layout.setSpacing(4)
        spectral_layout.addWidget(self.status_indicator)
        spectral_layout.addWidget(self.status_detail, 1)

        layout.addWidget(spectral_container, row_spectral, 0, 1, 4)

        self.setMaximumHeight(180)

    def update_data(self, technical: TechnicalInfo):
        vbr = "(VBR)" if technical.vbr else "(CBR)"
        self.labels["bitrate"].setText(f"{technical.bitrate} kbps {vbr}")

        if technical.bitrate_real:
            self.labels["bitrate_real"].setText(f"{technical.bitrate_real} kbps")
        else:
            self.labels["bitrate_real"].setText("N/A")

        self.labels["sample_rate"].setText(f"{technical.sample_rate} Hz")

        ch = technical.channels
        self.labels["channels"].setText(
            "Estéreo" if ch >= 2 else "Mono" if ch == 1 else str(ch)
        )

        self.labels["channel_mode"].setText(technical.channel_mode or "N/A")

        self.labels["duration"].setText(self._format_duration(technical.duration))
        self.labels["file_size"].setText(
            f"{technical.file_size / (1024 * 1024):.2f} MB"
        )
        self.labels["id3_version"].setText(technical.id3_version or "N/A")

        if technical.file_created:
            self.labels["file_created"].setText(
                self._format_date(technical.file_created)
            )
        else:
            self.labels["file_created"].setText("N/A")

        if technical.file_modified:
            self.labels["file_modified"].setText(
                self._format_date(technical.file_modified)
            )
        else:
            self.labels["file_modified"].setText("N/A")

        self._update_spectral_status(technical)

    def _update_spectral_status(self, tech: TechnicalInfo):
        """Actualiza el indicador de verificación espectral."""
        if tech.frecuencia_corte is not None and tech.bitrate_real is not None:
            freq_khz = tech.frecuencia_corte / 1000

            if tech.bitrate_match:
                # --- VERDE: OK ---
                self.status_indicator.setText("✓")
                self.status_indicator.setStyleSheet(
                    "color: #22aa22; font-size: 20px; font-weight: bold;"
                )
                self.status_detail.setText(
                    f"Bitrate verificado: ~{tech.bitrate_real} kbps  |  "
                    f"Frec. corte: {freq_khz:.1f} kHz"
                )
                self.status_detail.setStyleSheet(
                    "color: #22aa22; font-size: 11px; font-weight: bold;"
                )
                self.status_indicator.setToolTip(
                    "El análisis espectral confirma que el bitrate declarado "
                    "es coherente con el contenido de audio."
                )
            else:
                # --- ROJO: FAKE / UPSCALED ---
                self.status_indicator.setText("✗")
                self.status_indicator.setStyleSheet(
                    "color: #dd3333; font-size: 20px; font-weight: bold;"
                )
                self.status_detail.setText(
                    f"FAKE: Header dice {tech.bitrate} kbps pero el audio "
                    f"es ~{tech.bitrate_real} kbps  |  "
                    f"Frec. corte: {freq_khz:.1f} kHz"
                )
                self.status_detail.setStyleSheet(
                    "color: #dd3333; font-size: 11px; font-weight: bold;"
                )
                self.status_indicator.setToolTip(
                    f"ALERTA: El header declara {tech.bitrate} kbps pero "
                    f"la frecuencia de corte ({freq_khz:.1f} kHz) indica "
                    f"que el audio real es ~{tech.bitrate_real} kbps.\n"
                    f"Este archivo probablemente fue upscaled (fake)."
                )
        else:
            # --- GRIS: Sin datos ---
            self.status_indicator.setText("–")
            self.status_indicator.setStyleSheet(
                "color: #888; font-size: 18px; font-weight: bold;"
            )
            self.status_detail.setText("Análisis espectral no disponible")
            self.status_detail.setStyleSheet("color: #888; font-size: 11px;")
            self.status_indicator.setToolTip(
                "El análisis espectral requiere ffmpeg.exe en la carpeta 'tools/' del programa.\n"
                "Puedes descargarlo ejecutando: download_ffmpeg.bat\n"
                "O descarga manualmente desde: https://www.gyan.dev/ffmpeg/builds/\n"
                "Copia ffmpeg.exe a la carpeta 'tools/' junto al ejecutable."
            )

    def _format_duration(self, seconds: float) -> str:
        return f"{int(seconds // 60)}:{int(seconds % 60):02d}"

    def _format_date(self, timestamp: float) -> str:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")

    def clear(self):
        for label in self.labels.values():
            label.setText("N/A")
        if self.status_indicator:
            self.status_indicator.setText("")
        if self.status_detail:
            self.status_detail.setText("")
