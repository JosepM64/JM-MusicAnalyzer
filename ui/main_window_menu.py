import multiprocessing
import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from ui.metadata_panel import MetadataPanel
from ui.technical_panel import TechnicalPanel
from ui.widgets.cover_widget import CoverWidget
from ui.widgets.file_list_widget import FileListWidget
from ui.widgets.file_tree_widget import FileTreeWidget
from ui.widgets.simple_player_widget import SimplePlayerWidget


class MainWindowMenuMixin:
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        self._total_cores = multiprocessing.cpu_count()

        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            "QToolBar { background: #333; border: none; padding: 2px; spacing: 3px; }"
        )

        self.lbl_now_playing = QLabel()
        self.lbl_now_playing.setStyleSheet(
            "color: #00d4ff; font-size: 11px; font-weight: bold; padding: 0 8px; border: none;"
        )
        self.lbl_now_playing.setMaximumWidth(400)
        toolbar.addWidget(self.lbl_now_playing)

        self.btn_folder_tree = QPushButton("\U0001f4c1")
        self.btn_folder_tree.setToolTip("Mostrar/ocultar arbol de favoritos")
        self.btn_folder_tree.setFixedSize(32, 28)
        self.btn_folder_tree.setStyleSheet(
            "QPushButton { font-size: 14px; border: 1px solid #555; border-radius: 3px; background: #444; } QPushButton:hover { background: #555; } QPushButton:checked { background: #0078d4; border-color: #0078d4; }"
        )
        self.btn_folder_tree.setCheckable(True)
        self.btn_folder_tree.setChecked(False)
        self.btn_folder_tree.clicked.connect(self._on_toggle_folder_tree)
        toolbar.addWidget(self.btn_folder_tree)

        self.btn_scan_favs = QPushButton("\U0001f50d\u266b")
        self.btn_scan_favs.setToolTip("Escanear favoritos")
        self.btn_scan_favs.setFixedSize(42, 28)
        self.btn_scan_favs.setStyleSheet(
            "QPushButton { font-size: 12px; border: 1px solid #555; border-radius: 3px; background: #444; } QPushButton:hover { background: #555; }"
        )
        self.btn_scan_favs.clicked.connect(self._on_quick_scan)
        toolbar.addWidget(self.btn_scan_favs)

        toolbar.addSeparator()

        self.combo_genre = QComboBox()
        self.combo_genre.addItem("Genero")
        self.combo_genre.setFixedWidth(120)
        self.combo_genre.setStyleSheet("QComboBox { font-size: 10px; padding: 2px; }")
        toolbar.addWidget(self.combo_genre)

        self.combo_rating = QComboBox()
        self.combo_rating.addItems(["Rating", "1", "2", "3", "4", "5"])
        self.combo_rating.setFixedWidth(70)
        self.combo_rating.setStyleSheet("QComboBox { font-size: 10px; padding: 2px; }")
        toolbar.addWidget(self.combo_rating)

        self.combo_bpm = QComboBox()
        self.combo_bpm.addItems(
            ["BPM", "Sense BPM", "<90", "90-119", "120-149", "150-179", "180+"]
        )
        self.combo_bpm.setFixedWidth(90)
        self.combo_bpm.setStyleSheet("QComboBox { font-size: 10px; padding: 2px; }")
        self.combo_bpm.setToolTip(
            "Filtrar per BPM del tag (els rangs segueixen la convenció de ball)"
        )
        toolbar.addWidget(self.combo_bpm)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Buscar...")
        self.search_field.setFixedWidth(200)
        self.search_field.setStyleSheet("QLineEdit { font-size: 10px; padding: 3px; }")
        toolbar.addWidget(self.search_field)

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedWidth(60)
        btn_reset.setStyleSheet("QPushButton { font-size: 10px; padding: 3px; }")
        btn_reset.clicked.connect(self._on_search_reset)
        toolbar.addWidget(btn_reset)

        toolbar.addSeparator()

        self.lbl_cue_vol = QLabel("CUE:")
        self.lbl_cue_vol.setStyleSheet("color: #aaa; font-size: 10px;")
        toolbar.addWidget(self.lbl_cue_vol)

        self.slider_cue_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_cue_vol.setRange(0, 100)
        self.slider_cue_vol.setValue(70)
        self.slider_cue_vol.setFixedWidth(80)
        self.slider_cue_vol.valueChanged.connect(self._on_cue_vol_changed)
        toolbar.addWidget(self.slider_cue_vol)

        toolbar.addSeparator()

        self.btn_dj_mode = QPushButton("\U0001f3a7 DJ")
        self.btn_dj_mode.setToolTip("Cambiar a Modo DJ")
        self.btn_dj_mode.setFixedSize(52, 28)
        self.btn_dj_mode.setStyleSheet(
            "QPushButton { font-size: 11px; border: 1px solid #555; border-radius: 3px; background: #444; color: #ddd; } QPushButton:hover { background: #0078d4; color: white; }"
        )
        self.btn_dj_mode.clicked.connect(self._on_switch_to_performance)
        toolbar.addWidget(self.btn_dj_mode)

        btn_help = QPushButton("?")
        btn_help.setFixedSize(24, 24)
        btn_help.setToolTip("Ayuda rápida")
        btn_help.setStyleSheet(
            "QPushButton { font-size: 12px; font-weight: bold; border: 1px solid #555; border-radius: 12px; background: #444; color: #ddd; } QPushButton:hover { background: #0078d4; color: white; }"
        )
        btn_help.clicked.connect(self._show_help_menu)
        toolbar.addWidget(btn_help)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        self.lbl_cores = QLabel(f"{self._num_cores}/{self._total_cores}")
        self.lbl_cores.setToolTip(
            f"Cores usados: {self._num_cores} de {self._total_cores}"
        )
        self._update_cores_label_style()
        toolbar.addWidget(self.lbl_cores)

        main_layout.addWidget(toolbar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.file_tree = FileTreeWidget()
        self.file_tree.setFixedWidth(200)
        self.file_tree.setVisible(False)
        self.splitter.addWidget(self.file_tree)

        self.file_list = FileListWidget()
        self.splitter.addWidget(self.file_list)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(2, 2, 2, 2)
        right_layout.setSpacing(4)

        self.player_widget = SimplePlayerWidget()
        self.player_widget.setMaximumHeight(120)
        right_layout.addWidget(self.player_widget)

        self.metadata_panel = MetadataPanel()
        right_layout.addWidget(self.metadata_panel)

        self.technical_panel = TechnicalPanel()
        right_layout.addWidget(self.technical_panel)

        self.cover_widget = CoverWidget(size=150)
        self.cover_widget.setFixedHeight(160)
        right_layout.addWidget(self.cover_widget)

        right_panel.setFixedWidth(320)
        self.splitter.addWidget(right_panel)

        self.splitter.setSizes([200, 600, 320])
        main_layout.addWidget(self.splitter, 1)

        self._setup_menu_bar()
        self._setup_status_bar()

    def _on_toggle_folder_tree(self, checked):
        self.file_tree.setVisible(checked)
        if checked:
            self.splitter.setSizes([200, 400, 320])
        else:
            self.splitter.setSizes([0, 600, 320])

    def _update_cores_label_style(self):
        ratio = self._num_cores / self._total_cores if self._total_cores > 0 else 0
        if ratio <= 0.5:
            color = "#4CAF50"
        elif ratio <= 0.75:
            color = "#FF9800"
        else:
            color = "#f44336"
        self.lbl_cores.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold; padding: 0 4px;"
        )

    def _setup_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("Archivo")
        act_scan = file_menu.addAction("Escanear Carpeta...")
        act_scan.triggered.connect(lambda: self._on_scan_folder(recursive=True))
        act_quick = file_menu.addAction("Escaneo Rapido")
        act_quick.triggered.connect(self._on_quick_scan)
        file_menu.addSeparator()
        act_exit = file_menu.addAction("Salir")
        act_exit.triggered.connect(self.close)

        edit_menu = menu_bar.addMenu("Editar")
        act_force = edit_menu.addAction("Forzar Lectura Metadata")
        act_force.triggered.connect(self._on_force_read_selected)
        edit_menu.addSeparator()
        act_clear = edit_menu.addAction("Limpiar Base de Datos")
        act_clear.triggered.connect(self._on_clear_database)
        act_optimize = edit_menu.addAction("Optimizar Base de Datos")
        act_optimize.triggered.connect(self._on_optimize_database)
        act_del_nonexist = edit_menu.addAction("Eliminar Pistas Inexistentes")
        act_del_nonexist.triggered.connect(self._on_delete_nonexistent_tracks)
        act_rebuild = edit_menu.addAction("Reconstruir Base de Datos")
        act_rebuild.triggered.connect(self._on_rebuild_database)
        edit_menu.addSeparator()
        act_backup = edit_menu.addAction("Copia de Seguridad")
        act_backup.triggered.connect(self._on_backup_database)
        act_restore = edit_menu.addAction("Restaurar Copia de Seguridad")
        act_restore.triggered.connect(self._on_restore_database)

        view_menu = menu_bar.addMenu("Ver")
        act_low = view_menu.addAction("Pistas de Baja Calidad...")
        act_low.triggered.connect(self._on_show_low_quality)
        act_corrupt = view_menu.addAction("Pistas Corruptas...")
        act_corrupt.triggered.connect(self._on_show_corrupted)
        act_dup = view_menu.addAction("Archivos Duplicados")
        act_dup.triggered.connect(self._on_show_duplicates)
        act_dup_fav = view_menu.addAction("Duplicados en Favoritos")
        act_dup_fav.triggered.connect(self._on_duplicates_in_all_favorites)

        mode_menu = menu_bar.addMenu("Modo")
        act_perf = mode_menu.addAction("Cambiar a Modo DJ")
        act_perf.triggered.connect(self._on_switch_to_performance)

        tools_menu = menu_bar.addMenu("Eina")
        act_ytdl = tools_menu.addAction("📥 Importar de YouTube")
        act_ytdl.triggered.connect(self._on_import_youtube)

    def _setup_status_bar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setMaximumWidth(250)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #555; border-radius: 3px; text-align: center; font-size: 9px; }"
            "QProgressBar::chunk { background-color: #0078d4; }"
        )
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().showMessage("Listo", 3000)

    def _show_help_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2b2b2b; color: #e0e0e0; border: 1px solid #555; padding: 4px; } QMenu::item { padding: 6px 20px; } QMenu::item:selected { background: #0078d4; }"
        )

        act_db = menu.addAction("Base de Datos")
        act_filters = menu.addAction("Filtros y Búsqueda")
        act_player = menu.addAction("Reproductor")
        act_metadata = menu.addAction("Metadatos")
        act_gestion = menu.addAction("Gestión Archivos")
        act_reports = menu.addAction("Informes")

        action = menu.exec_(
            self.mapToGlobal(
                self.btn_dj_mode.pos() + QPoint(0, self.btn_dj_mode.height())
            )
        )

        if action == act_db:
            self._show_help_dialog(
                "Base de Datos",
                "<b>Limpiar</b>: Elimina todas las pistas de la BD. Los archivos no se borran del disco.<br><br>"
                "<b>Optimizar</b>: Compacta la BD (VACUUM) y actualiza estadísticas. Muestra MB liberados.<br><br>"
                "<b>Eliminar Inexistentes</b>: Borra de la BD las pistas cuyo archivo ya no existe en disco.<br><br>"
                "<b>Reconstruir</b>: Re-escanea pistas con datos incompletos (título, artista, duración o bitrate vacíos).<br><br>"
                "<b>Copia de Seguridad</b>: Guarda una copia de la BD con timestamp en backups/.<br><br>"
                "<b>Restaurar Copia</b>: Reemplaza la BD actual por una copia de seguridad anterior.",
            )
        elif action == act_filters:
            self._show_help_dialog(
                "Filtros y Búsqueda",
                "<b>Estado / Género / Rating</b>: Combos para filtrar pistas en la tabla.<br><br>"
                "<b>Buscar</b>: Busca por texto (artista, título, género). Pulsa Enter.<br><br>"
                "<b>Reset</b>: Limpia todos los filtros y muestra todas las pistas.<br><br>"
                "<b>Árbol de carpetas</b>: Clic en una carpeta para ver solo sus pistas.",
            )
        elif action == act_player:
            self._show_help_dialog(
                "Reproductor",
                "<b>Play/Pause</b>: Reproduce o pausa la canción seleccionada.<br><br>"
                "<b>⏮ / ⏭</b>: Canción anterior/siguiente. Se reproduce automáticamente.<br><br>"
                "<b>CUE (Pre-escucha)</b>: Botón para pre-escuchar por auriculares sin reproducir por los altavoces.<br><br>"
                "<b>🖱 Doble clic en fila</b>: Carga la canción en el reproductor.",
            )
        elif action == act_metadata:
            self._show_help_dialog(
                "Metadatos",
                "<b>Guardar</b>: Guarda los cambios de metadatos en el archivo MP3.<br><br>"
                "<b>Identificar (MusicBrainz/iTunes)</b>: Busca metadatos online por artista y título. Muestra comparación para elegir qué guardar.<br><br>"
                "<b>Fingerprint (AcoustID)</b>: Identifica la canción por su huella acústica. Útil cuando no hay metadatos o son incorrectos.<br><br>"
                "<b>Forzar Lectura</b>: Re-lee los metadatos del archivo ignorando la caché.<br><br>"
                "<b>Rating</b>: Haz clic en las estrellas para puntuar. Se guarda automáticamente en la BD.",
            )
        elif action == act_gestion:
            self._show_help_dialog(
                "Gestión Archivos",
                "<b>🖱 Botón derecho sobre pista (Menú contextual):</b><br><br>"
                "<b>Añadir a DJ Master</b>: Envía la(s) pista(s) seleccionada(s) a la playlist principal del modo DJ.<br><br>"
                "<b>Eliminar archivo</b>: Borra el archivo del disco y lo elimina de la BD.<br><br>"
                "<b>Mover archivo</b>: Cambia el archivo de carpeta y actualiza la BD.",
            )
        elif action == act_reports:
            self._show_help_dialog(
                "Informes (Menú Ver)",
                "<b>Pistas de Baja Calidad</b>: Muestra pistas con bitrate &lt; 128 kbps o duración &lt; 10s. "
                "▶ Preview, ✅ Ignorar, 🗑 Eliminar archivo, 📄 Exportar TXT.<br><br>"
                "<b>Pistas Corruptas</b>: Muestra pistas con duración &lt;= 0. "
                "▶ Preview, ✅ Ignorar, 🗑 Eliminar archivo, 📄 Exportar TXT.<br><br>"
                "<b>Archivos Duplicados</b>: Detecta duplicados por SHA256. 5 modos: SHA256, nombre, "
                "título+artista, duración, tamaño+duración.<br><br>"
                "<b>Duplicados en Favoritos</b>: Busca pistas que aparecen en más de una carpeta favorita.",
            )

    def _show_help_dialog(self, title, html):
        from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Ayuda - {title}")
        dlg.setFixedSize(420, 380)
        dlg.setStyleSheet("QDialog { background: #2b2b2b; }")
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setHtml(
            f"<div style='color:#e0e0e0; font-size:12px; font-family:Segoe UI; padding:8px;'>{html}</div>"
        )
        browser.setStyleSheet(
            "QTextBrowser { background: #333; border: none; color: #e0e0e0; }"
        )
        layout.addWidget(browser)
        dlg.exec_()

    def _on_import_youtube(self):
        from plugins.yt_dl.main import YouTubeImportDialog
        current_path = getattr(self, "_current_folder", None) or "C:\\"
        api = {"current_path": current_path}
        dialog = YouTubeImportDialog(api, self)
        dialog.download_completed.connect(self._on_youtube_downloaded)
        dialog.exec()

    def _on_youtube_downloaded(self, folder, new_files):
        if not folder or not os.path.isdir(folder):
            return
        self.settings.set("last_youtube_folder", folder)
        self._on_tree_folder_clicked(folder)

        was_sorting = self.file_list.isSortingEnabled()
        if was_sorting:
            self.file_list.setSortingEnabled(False)
        for fp in reversed(new_files):
            if fp and os.path.isfile(fp):
                self.file_list.add_file_row(fp, index=0, highlight_new=True)
        if was_sorting:
            self.file_list.setSortingEnabled(True)

        self.start_batch_analysis([folder], recursive=True)
