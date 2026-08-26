from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from services.audio_hardware_service import AudioHardwareService
from services.settings_manager import SettingsManager


class AudioConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Audio (v2.5)")
        self.resize(550, 350)
        self.settings = SettingsManager()
        self.devices = AudioHardwareService.get_output_devices()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info sobre backend
        if self.devices:
            backend = self.devices[0].get("backend", "unknown")
            layout.addWidget(QLabel(f"<b>Backend:</b> {backend}"))
            layout.addWidget(
                QLabel("<i>Selecciona los dispositivos y guarda la configuración.</i>")
            )

        layout.addSpacing(10)

        # Master Output
        layout.addWidget(QLabel("<b>📢 SALIDA PRINCIPAL (Altificadores):</b>"))
        self.cb_master = QComboBox()
        saved_master = self.settings.get("master_device_id")

        self.cb_master.addItem("🖥️ Predeterminado (Sistema)", "")
        for i, dev in enumerate(self.devices):
            name = dev["name"]
            self.cb_master.addItem(name, dev["id"])
            if str(dev["id"]) == str(saved_master):
                self.cb_master.setCurrentIndex(i + 1)
        if not saved_master:
            self.cb_master.setCurrentIndex(0)
        layout.addWidget(self.cb_master)

        layout.addSpacing(15)

        # Cue Output
        layout.addWidget(QLabel("<b>🎧 AURICULARES / DAC (Pre-escucha):</b>"))
        self.cb_cue = QComboBox()
        saved_cue = self.settings.get("cue_device_id")

        self.cb_cue.addItem("🖥️ Predeterminado (Sistema)", "")
        for i, dev in enumerate(self.devices):
            name = dev["name"]
            self.cb_cue.addItem(name, dev["id"])
            if str(dev["id"]) == str(saved_cue):
                self.cb_cue.setCurrentIndex(i + 1)
        if not saved_cue:
            self.cb_cue.setCurrentIndex(0)

        layout.addWidget(self.cb_cue)

        # Sugerencia
        layout.addWidget(
            QLabel("<i>💡 Selecciona el dispositivo de auriculares para CUE</i>")
        )

        layout.addStretch()

        # Mostrar dispositivo actual de CUE
        cue_idx = self._get_current_cue_index()
        if cue_idx is not None:
            layout.addWidget(QLabel(f"<b>CUE actual:</b> índice {cue_idx}"))

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 Guardar")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def _get_current_cue_index(self):
        """Obtiene el índice de dispositivo CUE actual."""
        try:
            cue_id = self.settings.get("cue_device_id")
            if cue_id:
                result = AudioHardwareService.find_device_by_id(cue_id)
                if result and "index" in result:
                    return result["index"]
        except Exception:
            pass
        return None

    def _on_save(self):
        master_data = self.cb_master.currentData()
        cue_data = self.cb_cue.currentData()

        # Guardar como string para compatibilidad
        self.settings.set("master_device_id", str(master_data) if master_data else "")
        self.settings.set("cue_device_id", str(cue_data) if cue_data else "")

        self.accept()

    def get_config(self):
        master_id = self.cb_master.currentData()
        cue_id = self.cb_cue.currentData()
        return {
            "master": AudioHardwareService.find_device_by_id(master_id)
            if master_id
            else None,
            "cue": AudioHardwareService.find_device_by_id(cue_id) if cue_id else None,
        }
