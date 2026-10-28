from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from services.settings_manager import SettingsManager


class SettingsDialog(QDialog):
    """
    Diálogo general de configuración de la aplicación.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración Global")
        self.resize(500, 420)
        self.settings = SettingsManager()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Grupo: Rutas y Archivos ---
        path_group = QGroupBox("Rutas y Bibliotecas")
        path_lay = QVBoxLayout(path_group)

        path_lay.addWidget(QLabel("Carpeta de Playlists por defecto:"))
        self.txt_playlist_dir = QLineEdit()
        self.txt_playlist_dir.setText(self.settings.get("default_playlist_dir", ""))

        btn_browse = QPushButton("Explorar...")
        btn_browse.clicked.connect(self._on_browse_playlist_dir)

        path_lay.addWidget(self.txt_playlist_dir)
        path_lay.addWidget(btn_browse)

        path_lay.addWidget(QLabel("Carpeta de Biblioteca principal per defecte:"))
        self.txt_library_dir = QLineEdit()
        self.txt_library_dir.setText(self.settings.get("default_library_dir", ""))

        btn_browse_lib = QPushButton("Explorar...")
        btn_browse_lib.clicked.connect(self._on_browse_library_dir)

        path_lay.addWidget(self.txt_library_dir)
        path_lay.addWidget(btn_browse_lib)
        layout.addWidget(path_group)

        # --- Grupo: Comportamiento ---
        behavior_group = QGroupBox("Comportamiento")
        behavior_lay = QVBoxLayout(behavior_group)

        self.chk_autoload = QCheckBox("Cargar última lista automáticamente al arrancar")
        self.chk_autoload.setChecked(self.settings.get("auto_load_last_playlist", True))
        behavior_lay.addWidget(self.chk_autoload)

        self.chk_confirm_delete = QCheckBox(
            "Confirmar antes de quitar pistas de la lista"
        )
        self.chk_confirm_delete.setChecked(
            self.settings.get("confirm_playlist_remove", True)
        )
        behavior_lay.addWidget(self.chk_confirm_delete)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Idioma dels menús:"))
        self.combo_language = QComboBox()
        self.combo_language.addItem("Español", "es")
        self.combo_language.addItem("Català", "ca")
        current = self.settings.get("language", "es")
        self.combo_language.setCurrentIndex(1 if current == "ca" else 0)
        self._initial_language = current
        lang_row.addWidget(self.combo_language)
        lang_row.addStretch()
        behavior_lay.addLayout(lang_row)

        layout.addWidget(behavior_group)

        layout.addStretch()

        # Botones finales
        btns = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Cambios")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setStyleSheet(
            "background-color: #0078d4; color: white; font-weight: bold;"
        )
        self.btn_save.clicked.connect(self._on_save)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

    def _on_browse_playlist_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Seleccionar Carpeta de Playlists"
        )
        if path:
            self.txt_playlist_dir.setText(path)

    def _on_browse_library_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Seleccionar Carpeta de Biblioteca principal"
        )
        if path:
            self.txt_library_dir.setText(path)

    def _on_save(self):
        self.settings.set("default_playlist_dir", self.txt_playlist_dir.text())
        self.settings.set("default_library_dir", self.txt_library_dir.text())
        self.settings.set("auto_load_last_playlist", self.chk_autoload.isChecked())
        self.settings.set(
            "confirm_playlist_remove", self.chk_confirm_delete.isChecked()
        )
        new_lang = self.combo_language.currentData()
        self.settings.set("language", new_lang)
        self.accept()
        if new_lang != self._initial_language:
            QMessageBox.information(
                self,
                "Idioma / Idioma",
                "Reinicia l'aplicació per aplicar el nou idioma.\n"
                "Reinicia la aplicación para aplicar el nuevo idioma.",
            )
