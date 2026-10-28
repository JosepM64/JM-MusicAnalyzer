import sys

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from services.audio_hardware_service import AudioHardwareService
from services.settings_manager import SettingsManager


class AudioConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Audio (v2.5)")
        self.resize(550, 380)
        self.settings = SettingsManager()
        self.devices = self._query_devices()
        self._setup_ui()

    def _query_devices(self):
        devices = list(AudioHardwareService.get_output_devices())
        try:
            from PySide6.QtMultimedia import QMediaDevices

            known = set()
            for d in devices:
                name = d.get("name", "")
                known.add(name)
                known.add(name.split(" [")[0].strip().lower())
            for qd in QMediaDevices.audioOutputs():
                try:
                    desc = (qd.description() or "").strip()
                except Exception:
                    continue
                if not desc or len(desc) <= 4:
                    continue
                low = desc.lower()
                if low in known or any(
                    low in k or k in low for k in known if len(k) > 4
                ):
                    continue
                devices.append(
                    {"id": desc, "name": f"{desc} [nou 🆕]", "backend": "qt-new"}
                )
        except Exception:
            pass
        return devices

    def _fill_device_combos(self):
        saved_master = self.settings.get("master_device_id")
        saved_cue = self.settings.get("cue_device_id")
        for cb, keep, saved in (
            (self.cb_master, self.cb_master.currentData(), saved_master),
            (self.cb_cue, self.cb_cue.currentData(), saved_cue),
        ):
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("🖥️ Predeterminado (Sistema)", "")
            for dev in self.devices:
                cb.addItem(dev["name"], dev["id"])
            target = keep if keep else (saved or "")
            idx = cb.findData(target)
            cb.setCurrentIndex(idx if idx >= 0 else 0)
            cb.blockSignals(False)

    def _refresh_info_labels(self):
        if self.devices:
            backend = self.devices[0].get("backend", "unknown")
            self.lbl_backend.setText(
                f"<b>Backend:</b> {backend} · {len(self.devices)} dispositius"
            )
        else:
            self.lbl_backend.setText("<b>Backend:</b> cap dispositiu trobat")
        cue_idx = self._get_current_cue_index()
        if cue_idx is not None:
            self.lbl_cue_actual.setText(f"<b>CUE actual:</b> índex {cue_idx}")
        else:
            self.lbl_cue_actual.setText("<b>CUE actual:</b> --")

    def _on_reload_devices(self):
        self.devices = self._query_devices()
        self._fill_device_combos()
        self._refresh_info_labels()
        nuevos = sum(1 for d in self.devices if d.get("backend") == "qt-new")
        self.lbl_status.setText(
            f"🔄 {len(self.devices)} dispositius ({nuevos} nous 🆕)"
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info sobre backend
        self.lbl_backend = QLabel("")
        layout.addWidget(self.lbl_backend)
        layout.addWidget(
            QLabel("<i>Selecciona los dispositivos y guarda la configuración.</i>")
        )

        layout.addSpacing(10)

        # Master Output
        layout.addWidget(QLabel("<b>📢 SALIDA PRINCIPAL (Altificadores):</b>"))
        self.cb_master = QComboBox()
        layout.addWidget(self.cb_master)

        layout.addSpacing(15)

        # Cue Output
        layout.addWidget(QLabel("<b>🎧 AURICULARES / DAC (Pre-escucha):</b>"))
        self.cb_cue = QComboBox()
        layout.addWidget(self.cb_cue)

        # Sugerencia
        layout.addWidget(
            QLabel("<i>💡 Selecciona el dispositivo de auriculares para CUE</i>")
        )
        layout.addWidget(
            QLabel(
                "<i>🆕 = detectat en calent (sense parar la música). "
                "Si un 🆕 no sona, reinicia l'app (límit del backend).</i>"
            )
        )

        layout.addStretch()

        # Mostrar dispositivo actual de CUE
        self.lbl_cue_actual = QLabel("")
        layout.addWidget(self.lbl_cue_actual)

        self._fill_device_combos()
        self._refresh_info_labels()

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)

        btn_layout = QHBoxLayout()
        self.btn_reload = QPushButton("🔄 Recargar")
        self.btn_reload.setMinimumHeight(40)
        self.btn_reload.setToolTip(
            "Torna a detectar dispositius (DAC USB...) sense parar la música"
        )
        self.btn_reload.clicked.connect(self._on_reload_devices)
        self.btn_save = QPushButton("💾 Guardar")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_reload)
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

    def _selection_needs_restart(self):
        by_id = {str(d.get("id")): d.get("backend") for d in self.devices}
        for cb in (self.cb_master, self.cb_cue):
            data = cb.currentData()
            if (
                data
                and by_id.get(str(data)) == "qt-new"
                and AudioHardwareService.find_device_by_id(data) is None
            ):
                return True
        return False

    def _restart_app(self):
        try:
            if getattr(sys, "frozen", False):
                QProcess.startDetached(sys.executable, sys.argv[1:])
            else:
                QProcess.startDetached(sys.executable, sys.argv)
        except Exception:
            pass
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _on_save(self):
        master_data = self.cb_master.currentData()
        cue_data = self.cb_cue.currentData()

        # Guardar como string para compatibilidad
        self.settings.set("master_device_id", str(master_data) if master_data else "")
        self.settings.set("cue_device_id", str(cue_data) if cue_data else "")

        if self._selection_needs_restart():
            resp = QMessageBox.question(
                self,
                "Reinici necessari",
                "Aquest dispositiu s'ha detectat en calent però el motor "
                "d'àudio encara no el veu.\n\nVols reiniciar l'app ara per "
                "activar-lo? (es guardarà la configuració)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp == QMessageBox.StandardButton.Yes:
                self.accept()
                self._restart_app()
                return

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
