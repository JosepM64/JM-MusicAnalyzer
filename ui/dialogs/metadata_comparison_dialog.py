from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class MetadataComparisonDialog(QDialog):
    """
    Diálogo para comparar metadatos locales vs online y aplicar cambios.
    Permite seleccionar qué campos aplicar desde la fuente online.
    Muestra carátula local (izq) vs online (der) cara a cara.
    """

    FIELDS = [
        ("Título", "title"),
        ("Artista", "artist"),
        ("Álbum", "album"),
        ("Año", "year"),
        ("Género", "genre"),
        ("BPM", "bpm"),
        ("Track", "track_number"),
        ("ISRC", "isrc"),
    ]

    def __init__(
        self, local_data: dict, online_data: dict, parent=None, local_cover_data=None
    ):
        super().__init__(parent)
        source = online_data.get("source", "Online")
        self.setWindowTitle(f"Comparar: Local vs {source}")
        self.setMinimumWidth(700)
        self.result_data = None
        self.online_data = online_data
        self.local_cover_data = local_cover_data

        self._setup_ui(local_data, online_data)

    def _setup_ui(self, local, online):
        layout = QVBoxLayout(self)

        # --- Header con carátulas cara a cara ---
        header_layout = QHBoxLayout()

        # Carátula LOCAL (izquierda)
        local_cover_box = QVBoxLayout()
        local_cover_box.addWidget(
            QLabel("<b>Local</b>"), alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.lbl_local_cover = QLabel()
        self.lbl_local_cover.setFixedSize(150, 150)
        self.lbl_local_cover.setStyleSheet(
            "border: 2px solid #4CAF50; background: #222; border-radius: 4px;"
        )
        self.lbl_local_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.local_cover_data:
            self._set_cover_pixmap(self.lbl_local_cover, self.local_cover_data)
        else:
            self.lbl_local_cover.setText("<font color='#666'>Sin carátula</font>")
        local_cover_box.addWidget(self.lbl_local_cover)
        header_layout.addLayout(local_cover_box)

        # Info central
        info_vbox = QVBoxLayout()
        info_vbox.addStretch()
        info_vbox.addWidget(
            QLabel("<b style='font-size:14px;'>Comparar metadatos</b>"),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        info_vbox.addWidget(
            QLabel(
                f"<font color='gray'>Fuente: {online.get('source', 'Internet')}</font>"
            ),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        info_vbox.addWidget(
            QLabel(
                "<font color='gray'>Desmarca los campos que NO quieras aplicar</font>"
            ),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        info_vbox.addStretch()
        header_layout.addLayout(info_vbox)

        # Carátula ONLINE (derecha)
        online_cover_box = QVBoxLayout()
        online_cover_box.addWidget(
            QLabel("<b>Online</b>"), alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.lbl_online_cover = QLabel()
        self.lbl_online_cover.setFixedSize(150, 150)
        self.lbl_online_cover.setStyleSheet(
            "border: 2px solid #2196F3; background: #222; border-radius: 4px;"
        )
        self.lbl_online_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if online.get("cover_url"):
            self.lbl_online_cover.setText("<font color='#666'>Cargando...</font>")
            self._load_online_cover(online["cover_url"])
        else:
            self.lbl_online_cover.setText("<font color='#666'>Sin carátula</font>")
        online_cover_box.addWidget(self.lbl_online_cover)
        header_layout.addLayout(online_cover_box)

        layout.addLayout(header_layout)

        # --- Tabla de comparación con checkboxes ---
        self.table = QTableWidget(len(self.FIELDS), 4)
        self.table.setHorizontalHeaderLabels(
            ["✓", "Campo", "Local", "Online (Sugerido)"]
        )
        self.table.setColumnWidth(0, 30)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.table.verticalHeader().hide()

        for i, (label, key) in enumerate(self.FIELDS):
            # Checkbox column
            item_check = QTableWidgetItem()
            item_check.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            item_check.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(i, 0, item_check)

            # Field label
            item_label = QTableWidgetItem(label)
            item_label.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(i, 1, item_label)

            # Local value
            local_val = str(local.get(key) or "") if local.get(key) is not None else "-"
            item_local = QTableWidgetItem(local_val)
            item_local.setForeground(Qt.GlobalColor.gray)
            item_local.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(i, 2, item_local)

            # Online value
            online_val = (
                str(online.get(key) or "") if online.get(key) is not None else "-"
            )
            if not online_val:
                online_val = "-"

            item_online = QTableWidgetItem(online_val)
            item_online.setFlags(Qt.ItemFlag.ItemIsEnabled)

            if online_val != "-" and online_val.lower() != local_val.lower():
                item_online.setBackground(Qt.GlobalColor.yellow)
                item_online.setForeground(Qt.GlobalColor.black)

            self.table.setItem(i, 3, item_online)

        layout.addWidget(self.table)

        # --- Select All / Deselect All buttons ---
        sel_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Seleccionar Todo")
        self.btn_select_all.setStyleSheet("font-size: 10px; padding: 4px 10px;")
        self.btn_select_all.clicked.connect(self._select_all)
        sel_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deseleccionar Todo")
        self.btn_deselect_all.setStyleSheet("font-size: 10px; padding: 4px 10px;")
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        sel_layout.addWidget(self.btn_deselect_all)

        sel_layout.addStretch()

        self.lbl_selected_count = QLabel("8 campos seleccionados")
        self.lbl_selected_count.setStyleSheet("color: #888; font-size: 10px;")
        sel_layout.addWidget(self.lbl_selected_count)

        layout.addLayout(sel_layout)

        # --- Botones ---
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Aplicar Cambios ✨")
        self.btn_apply.setStyleSheet(
            "background-color: #6a1b9a; color: white; font-weight: bold; padding: 10px 20px; border-radius: 4px; font-size: 12px;"
        )
        self.btn_apply.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setStyleSheet(
            "padding: 10px 20px; border-radius: 4px; font-size: 12px;"
        )
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_apply)

        layout.addLayout(btn_layout)

        # Connect checkbox changes to update count
        self.table.itemChanged.connect(self._update_selected_count)

    def _select_all(self):
        self.table.blockSignals(True)
        for i in range(len(self.FIELDS)):
            item = self.table.item(i, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        self.table.blockSignals(False)
        self._update_selected_count()

    def _deselect_all(self):
        self.table.blockSignals(True)
        for i in range(len(self.FIELDS)):
            item = self.table.item(i, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self._update_selected_count()

    def _update_selected_count(self):
        count = sum(
            1
            for i in range(len(self.FIELDS))
            if self.table.item(i, 0)
            and self.table.item(i, 0).checkState() == Qt.CheckState.Checked
        )
        self.lbl_selected_count.setText(f"{count} campos seleccionados")

    def _set_cover_pixmap(self, label, data):
        """Muestra una carátula desde bytes."""
        try:
            img = QImage()
            img.loadFromData(data)
            if not img.isNull():
                pix = QPixmap.fromImage(img).scaled(
                    150,
                    150,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(pix)
                return
        except Exception:
            pass
        label.setText("<font color='#666'>No válida</font>")

    def _load_online_cover(self, url):
        """Carga carátula online en segundo plano."""
        try:
            import requests

            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                self.online_data["cover_data"] = resp.content
                self._set_cover_pixmap(self.lbl_online_cover, resp.content)
                return
        except Exception:
            pass
        self.lbl_online_cover.setText("<font color='#666'>No disponible</font>")

    def accept(self):
        self.result_data = self.get_selected_data()
        super().accept()

    def get_selected_data(self):
        selected = {}
        for i, (_, key) in enumerate(self.FIELDS):
            item = self.table.item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                val = self.online_data.get(key)
                if val:
                    selected[key] = val
        return selected
