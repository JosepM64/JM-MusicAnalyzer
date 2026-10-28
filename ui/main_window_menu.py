import multiprocessing
import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
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
        # Normalized per DESIGN.md §5 §17 — BG_700 + S1 spacing
        try:
            from ui.tokens import BG_700, STROKE_400

            toolbar.setStyleSheet(
                f"QToolBar {{ background: {BG_700}; border: none; border-bottom: 1px solid {STROKE_400}; padding: 2px; spacing: 4px; }}"
            )
        except Exception:
            toolbar.setStyleSheet(
                "QToolBar { background: #222; border: none; border-bottom: 1px solid #444; padding: 2px; spacing: 4px; }"
            )

        self.lbl_now_playing = QLabel()
        try:
            from ui.tokens import CYAN

            self.lbl_now_playing.setStyleSheet(
                f"color: {CYAN}; font-size: 11px; font-weight: 700; padding: 0 8px; border: none; font-family: 'Segoe UI', sans-serif;"
            )
        except Exception:
            self.lbl_now_playing.setStyleSheet(
                "color: #00d4ff; font-size: 11px; font-weight: 700; padding: 0 8px; border: none;"
            )
        self.lbl_now_playing.setMaximumWidth(400)
        toolbar.addWidget(self.lbl_now_playing)

        self.btn_folder_tree = QPushButton("\U0001f4c1")
        self.btn_folder_tree.setToolTip("Mostrar/ocultar arbol de favoritos")
        self.btn_folder_tree.setFixedSize(32, 28)
        try:
            from ui.tokens import BG_400, BG_500, PRIMARY, STROKE_400

            self.btn_folder_tree.setStyleSheet(
                f"QPushButton {{ font-size: 14px; border: 1px solid {STROKE_400}; border-radius: 3px; background: {BG_400}; padding: 0px; }} QPushButton:hover {{ background: {BG_500}; }} QPushButton:checked {{ background: {PRIMARY}; border-color: {PRIMARY}; }} QPushButton:focus {{ border: 1px solid #6a1b9a; }}"
            )
        except Exception:
            self.btn_folder_tree.setStyleSheet(
                "QPushButton { font-size: 14px; border: 1px solid #444; border-radius: 3px; background: #333; padding: 0px; } QPushButton:hover { background: #2b2b2b; } QPushButton:checked { background: #0078d4; border-color: #0078d4; }"
            )
        self.btn_folder_tree.setCheckable(True)
        self.btn_folder_tree.setChecked(False)
        self.btn_folder_tree.clicked.connect(self._on_toggle_folder_tree)
        toolbar.addWidget(self.btn_folder_tree)

        self.btn_scan_favs = QPushButton("\U0001f50d\u266b")
        self.btn_scan_favs.setToolTip("Escanear favoritos (Ctrl+Shift+O)")
        self.btn_scan_favs.setFixedSize(42, 28)
        try:
            from ui.tokens import BG_400, BG_500, STROKE_400

            self.btn_scan_favs.setStyleSheet(
                f"QPushButton {{ font-size: 12px; border: 1px solid {STROKE_400}; border-radius: 3px; background: {BG_400}; padding: 0px; }} QPushButton:hover {{ background: {BG_500}; }} QPushButton:focus {{ border: 1px solid #6a1b9a; }}"
            )
        except Exception:
            self.btn_scan_favs.setStyleSheet(
                "QPushButton { font-size: 12px; border: 1px solid #444; border-radius: 3px; background: #333; padding: 0px; } QPushButton:hover { background: #2b2b2b; }"
            )
        self.btn_scan_favs.clicked.connect(self._on_quick_scan)
        toolbar.addWidget(self.btn_scan_favs)

        toolbar.addSeparator()

        # Filter bar — DESIGN.md §11: 11px/5px + BG_400 + focus purple, tokenized
        try:
            from ui.tokens import BG_400, FOCUS_PURPLE, FONT_FAMILY, RADIUS_SM, STROKE_400, TEXT_100

            _filter_qss = (
                f"QComboBox, QLineEdit {{ background-color: {BG_400}; color: {TEXT_100}; "
                f"border: 1px solid {STROKE_400}; border-radius: {RADIUS_SM}px; "
                f"font-size: 11px; padding: 5px; font-family: {FONT_FAMILY}; }}"
                f"QComboBox:focus, QLineEdit:focus {{ border: 1px solid {FOCUS_PURPLE}; }}"
                f"QComboBox QAbstractItemView {{ background-color: {BG_400}; color: {TEXT_100}; selection-background-color: {FOCUS_PURPLE}; }}"
            )
        except Exception:
            _filter_qss = "QComboBox, QLineEdit { background-color: #333; color: #ffffff; border: 1px solid #444; border-radius: 3px; font-size: 11px; padding: 5px; font-family: 'Segoe UI', sans-serif; } QComboBox:focus, QLineEdit:focus { border: 1px solid #6a1b9a; }"

        self.combo_genre = QComboBox()
        self.combo_genre.addItem("Genero")
        self.combo_genre.setFixedWidth(120)
        self.combo_genre.setStyleSheet(_filter_qss)
        self.combo_genre.setToolTip("Filtrar per gènere (Ctrl+G)")
        toolbar.addWidget(self.combo_genre)

        self.combo_rating = QComboBox()
        self.combo_rating.addItems(["Rating", "1", "2", "3", "4", "5"])
        self.combo_rating.setFixedWidth(70)
        self.combo_rating.setStyleSheet(_filter_qss)
        self.combo_rating.setToolTip("Filtrar per rating")
        toolbar.addWidget(self.combo_rating)

        self.combo_bpm = QComboBox()
        self.combo_bpm.addItems(
            ["BPM", "Sense BPM", "<90", "90-119", "120-149", "150-179", "180+"]
        )
        self.combo_bpm.setFixedWidth(90)
        self.combo_bpm.setStyleSheet(_filter_qss)
        self.combo_bpm.setToolTip(
            "Filtrar per BPM del tag (els rangs segueixen la convenció de ball)"
        )
        toolbar.addWidget(self.combo_bpm)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Buscar... (Ctrl+F)")
        self.search_field.setFixedWidth(200)
        self.search_field.setStyleSheet(_filter_qss)
        self.search_field.setToolTip("Cerca per artista/títol/gènere (Ctrl+F)")
        toolbar.addWidget(self.search_field)

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedWidth(60)
        try:
            from ui.tokens import BG_500, RADIUS_MD, STROKE_400, TEXT_80

            btn_reset.setStyleSheet(
                f"QPushButton {{ background-color: {BG_500}; color: {TEXT_80}; border: 1px solid {STROKE_400}; border-radius: {RADIUS_MD}px; font-size: 11px; padding: 5px 6px; font-weight: 600; font-family: 'Segoe UI', sans-serif; }}"
                f"QPushButton:hover {{ background-color: #3a3a3a; }} QPushButton:pressed {{ background-color: #0078d4; border-color: #0078d4; color: #ffffff; }}"
            )
        except Exception:
            btn_reset.setStyleSheet("QPushButton { font-size: 11px; padding: 5px 6px; font-weight: 600; }")
        btn_reset.setToolTip("Netejar filtres (Esc)")
        btn_reset.clicked.connect(self._on_search_reset)
        toolbar.addWidget(btn_reset)

        toolbar.addSeparator()

        self.lbl_cue_vol = QLabel("CUE:")
        try:
            from ui.tokens import TEXT_60

            self.lbl_cue_vol.setStyleSheet(f"color: {TEXT_60}; font-size: 10px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        except Exception:
            self.lbl_cue_vol.setStyleSheet("color: #a0a0a0; font-size: 10px; font-weight: 600;")
        toolbar.addWidget(self.lbl_cue_vol)

        self.slider_cue_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_cue_vol.setRange(0, 100)
        self.slider_cue_vol.setValue(70)
        self.slider_cue_vol.setFixedWidth(80)
        self.slider_cue_vol.valueChanged.connect(self._on_cue_vol_changed)
        toolbar.addWidget(self.slider_cue_vol)

        toolbar.addSeparator()

        self.btn_dj_mode = QPushButton("\U0001f3a7 DJ")
        self.btn_dj_mode.setToolTip("Cambiar a Modo DJ (Ctrl+D)")
        self.btn_dj_mode.setFixedSize(58, 28)
        try:
            from ui.tokens import BG_400, PRIMARY, STROKE_400, TEXT_80, TEXT_100

            self.btn_dj_mode.setStyleSheet(
                f"QPushButton {{ font-size: 11px; border: 1px solid {STROKE_400}; border-radius: 3px; background: {BG_400}; color: {TEXT_80}; font-weight: 600; padding: 0px; }} QPushButton:hover {{ background: {PRIMARY}; color: {TEXT_100}; border-color: {PRIMARY}; }} QPushButton:focus {{ border: 1px solid #6a1b9a; }}"
            )
        except Exception:
            self.btn_dj_mode.setStyleSheet(
                "QPushButton { font-size: 11px; border: 1px solid #444; border-radius: 3px; background: #333; color: #ddd; padding: 0px; } QPushButton:hover { background: #0078d4; color: white; }"
            )
        self.btn_dj_mode.clicked.connect(self._on_switch_to_performance)
        toolbar.addWidget(self.btn_dj_mode)

        self.btn_audio_main = QPushButton("🎧")
        self.btn_audio_main.setFixedSize(28, 28)
        self.btn_audio_main.setToolTip("Configurar audio")
        try:
            from ui.tokens import BG_400, PRIMARY, STROKE_400, TEXT_80, TEXT_100

            self.btn_audio_main.setStyleSheet(
                f"QPushButton {{ font-size: 13px; border: 1px solid {STROKE_400}; border-radius: 3px; background: {BG_400}; color: {TEXT_80}; padding: 0px; }} QPushButton:hover {{ background: {PRIMARY}; color: {TEXT_100}; }} QPushButton:focus {{ border: 1px solid #6a1b9a; }}"
            )
        except Exception:
            self.btn_audio_main.setStyleSheet(
                "QPushButton { font-size: 13px; border: 1px solid #444; border-radius: 3px; background: #333; color: #ddd; padding: 0px; } QPushButton:hover { background: #0078d4; color: white; }"
            )
        self.btn_audio_main.clicked.connect(self._on_audio_config)
        toolbar.addWidget(self.btn_audio_main)

        self.btn_settings_main = QPushButton("⚙")
        self.btn_settings_main.setFixedSize(28, 28)
        self.btn_settings_main.setToolTip("Ajustes")
        try:
            from ui.tokens import BG_400, PRIMARY, STROKE_400, TEXT_80, TEXT_100

            self.btn_settings_main.setStyleSheet(
                f"QPushButton {{ font-size: 13px; border: 1px solid {STROKE_400}; border-radius: 3px; background: {BG_400}; color: {TEXT_80}; padding: 0px; }} QPushButton:hover {{ background: {PRIMARY}; color: {TEXT_100}; }} QPushButton:focus {{ border: 1px solid #6a1b9a; }}"
            )
        except Exception:
            self.btn_settings_main.setStyleSheet(
                "QPushButton { font-size: 13px; border: 1px solid #444; border-radius: 3px; background: #333; color: #ddd; padding: 0px; } QPushButton:hover { background: #0078d4; color: white; }"
            )
        self.btn_settings_main.clicked.connect(self._on_open_settings)
        toolbar.addWidget(self.btn_settings_main)

        btn_help = QPushButton("?")
        btn_help.setFixedSize(28, 28)
        btn_help.setToolTip("Ayuda rápida (F1)")
        try:
            from ui.tokens import BG_400, PRIMARY, STROKE_400, TEXT_80, TEXT_100

            btn_help.setStyleSheet(
                f"QPushButton {{ font-size: 12px; font-weight: 700; border: 1px solid {STROKE_400}; border-radius: 12px; background: {BG_400}; color: {TEXT_80}; padding: 0px; }} QPushButton:hover {{ background: {PRIMARY}; color: {TEXT_100}; }} QPushButton:focus {{ border: 1px solid #6a1b9a; }}"
            )
        except Exception:
            btn_help.setStyleSheet(
                "QPushButton { font-size: 12px; font-weight: 700; border: 1px solid #444; border-radius: 12px; background: #333; color: #ddd; padding: 0px; } QPushButton:hover { background: #0078d4; color: white; }"
            )
        btn_help.clicked.connect(self._show_help_menu)
        toolbar.addWidget(btn_help)

        # Labels de info (tracks + cores) — fora del QToolBar per evitar overflow "..."
        # abans eren dins toolbar i quedaven amagats quan la barra no cabia
        self.lbl_tracks = QLabel("♫ --")
        self.lbl_tracks.setToolTip("Cançons indexades a la base de dades")
        try:
            from ui.tokens import TEXT_60

            self.lbl_tracks.setStyleSheet(f"color: {TEXT_60}; font-size: 11px; font-weight: 600; padding: 0 6px;")
        except Exception:
            self.lbl_tracks.setStyleSheet("color: #a0a0a0; font-size: 11px; font-weight: 600; padding: 0 6px;")

        self.lbl_cores = QLabel(f"{self._num_cores}/{self._total_cores}")
        self.lbl_cores.setToolTip(
            f"Cores usados: {self._num_cores} de {self._total_cores}"
        )
        self._update_cores_label_style()

        # Contenidor superior: toolbar + labels a la dreta (fora de l'overflow)
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)
        top_layout.addWidget(toolbar, 1)
        top_layout.addWidget(self.lbl_tracks, 0)
        top_layout.addWidget(self.lbl_cores, 0)
        main_layout.addWidget(top_bar)

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
        # comptador BD — actualitza després d'init (DB ja disponible)
        try:
            self._update_tracks_count()
        except Exception:
            pass

    def _on_toggle_folder_tree(self, checked):
        self.file_tree.setVisible(checked)
        if checked:
            # Recarregar per recollir favorits afegits amb +⭐ mentre era ocult,
            # i per no mostrar mai el panell buit de la foto.
            try:
                if self.file_tree.topLevelItemCount() <= 1:
                    self._refresh_folder_tree()
            except Exception:
                pass
            self.splitter.setSizes([200, 400, 320])
        else:
            self.splitter.setSizes([0, 600, 320])

    def _on_audio_config(self):
        from ui.dialogs.audio_config_dialog import AudioConfigDialog

        dlg = AudioConfigDialog(self)
        if dlg.exec():
            cfg = dlg.get_config()
            try:
                if cfg["master"]:
                    self.player_widget.setAudioDevice(cfg["master"])
                if cfg["cue"]:
                    self.player_widget.setCueAudioDevice(cfg["cue"])
            except Exception:
                pass

    def _on_open_settings(self):
        from ui.dialogs.settings_dialog import SettingsDialog

        SettingsDialog(self).exec()

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

    def _update_tracks_count(self):
        try:
            count = 0
            if hasattr(self, "db_manager") and self.db_manager:
                count = self.db_manager.get_track_count()
            elif hasattr(self, "db") and self.db:
                # fallback via get_db()
                from services.db import get_db

                count = get_db().get_track_count()
            # format amb separador
            txt = f"{count:,}".replace(",", ".") if count else "0"
            self.lbl_tracks.setText(f"\u266b {txt}")
            self.lbl_tracks.setToolTip(f"{count} cançons indexades a la base de dades")
        except Exception:
            try:
                self.lbl_tracks.setText("\u266b --")
            except Exception:
                pass

    def _setup_menu_bar(self):
        from ui.i18n_menu import menu_text as _

        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu(_("menu_file"))
        act_scan = file_menu.addAction(_("scan_folder"))
        act_scan.triggered.connect(lambda: self._on_scan_folder(recursive=True))
        act_quick = file_menu.addAction(_("quick_scan"))
        act_quick.triggered.connect(self._on_quick_scan)
        file_menu.addSeparator()
        act_exit = file_menu.addAction(_("exit"))
        act_exit.triggered.connect(self.close)

        edit_menu = menu_bar.addMenu(_("menu_edit"))
        act_force = edit_menu.addAction(_("force_read"))
        act_force.triggered.connect(self._on_force_read_selected)
        edit_menu.addSeparator()
        act_clear = edit_menu.addAction(_("clear_db"))
        act_clear.triggered.connect(self._on_clear_database)
        act_optimize = edit_menu.addAction(_("optimize_db"))
        act_optimize.triggered.connect(self._on_optimize_database)
        act_del_nonexist = edit_menu.addAction(_("del_nonexist"))
        act_del_nonexist.triggered.connect(self._on_delete_nonexistent_tracks)
        act_rebuild = edit_menu.addAction(_("rebuild_db"))
        act_rebuild.triggered.connect(self._on_rebuild_database)
        edit_menu.addSeparator()
        act_backup = edit_menu.addAction(_("backup_db"))
        act_backup.triggered.connect(self._on_backup_database)
        act_restore = edit_menu.addAction(_("restore_db"))
        act_restore.triggered.connect(self._on_restore_database)

        view_menu = menu_bar.addMenu(_("menu_view"))
        act_low = view_menu.addAction(_("low_quality"))
        act_low.triggered.connect(self._on_show_low_quality)
        act_corrupt = view_menu.addAction(_("corrupted"))
        act_corrupt.triggered.connect(self._on_show_corrupted)
        act_dup = view_menu.addAction(_("duplicates"))
        act_dup.triggered.connect(self._on_show_duplicates)
        act_dup_fav = view_menu.addAction(_("duplicates_fav"))
        act_dup_fav.triggered.connect(self._on_duplicates_in_all_favorites)

        mode_menu = menu_bar.addMenu(_("menu_mode"))
        act_perf = mode_menu.addAction(_("to_dj"))
        act_perf.triggered.connect(self._on_switch_to_performance)

        tools_menu = menu_bar.addMenu(_("menu_tools"))
        act_ytdl = tools_menu.addAction(_("import_yt"))
        act_ytdl.triggered.connect(self._on_import_youtube)

    def _setup_status_bar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setMaximumWidth(250)
        self.progress_bar.setVisible(False)
        try:
            from ui.tokens import BG_800, PRIMARY, STROKE_400, TEXT_80

            self.progress_bar.setStyleSheet(
                f"QProgressBar {{ background-color: {BG_800}; border: 1px solid {STROKE_400}; border-radius: 3px; text-align: center; font-size: 9px; color: {TEXT_80}; }}"
                f"QProgressBar::chunk {{ background-color: {PRIMARY}; border-radius: 2px; }}"
            )
        except Exception:
            self.progress_bar.setStyleSheet(
                "QProgressBar { border: 1px solid #444; border-radius: 3px; text-align: center; font-size: 9px; }"
                "QProgressBar::chunk { background-color: #0078d4; }"
            )
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().showMessage("Listo", 3000)

    def _show_help_menu(self):
        from ui.i18n_help import help_text as _h

        menu = QMenu(self)
        try:
            from ui.tokens import BG_500, PRIMARY, STROKE_400, TEXT_80, TEXT_100

            menu.setStyleSheet(
                f"QMenu {{ background: {BG_500}; color: {TEXT_80}; border: 1px solid {STROKE_400}; padding: 4px; font-family: 'Segoe UI', sans-serif; }} QMenu::item {{ padding: 6px 20px; }} QMenu::item:selected {{ background: {PRIMARY}; color: {TEXT_100}; }} QMenu::separator {{ height: 1px; background: {STROKE_400}; margin: 4px 8px; }}"
            )
        except Exception:
            menu.setStyleSheet(
                "QMenu { background: #2b2b2b; color: #e0e0e0; border: 1px solid #444; padding: 4px; } QMenu::item { padding: 6px 20px; } QMenu::item:selected { background: #0078d4; }"
            )

        act_db = menu.addAction(_h("m_db"))
        act_filters = menu.addAction(_h("m_filters"))
        act_player = menu.addAction(_h("m_player"))
        act_metadata = menu.addAction(_h("m_metadata"))
        act_gestion = menu.addAction(_h("m_files"))
        act_reports = menu.addAction(_h("m_reports"))

        action = menu.exec_(
            self.mapToGlobal(
                self.btn_dj_mode.pos() + QPoint(0, self.btn_dj_mode.height())
            )
        )

        if action == act_db:
            self._show_help_dialog(_h("m_db"), _h("h_db"))
        elif action == act_filters:
            self._show_help_dialog(_h("m_filters"), _h("h_filters"))
        elif action == act_player:
            self._show_help_dialog(_h("m_player"), _h("h_player"))
        elif action == act_metadata:
            self._show_help_dialog(_h("m_metadata"), _h("h_metadata"))
        elif action == act_gestion:
            self._show_help_dialog(_h("m_files"), _h("h_files"))
        elif action == act_reports:
            self._show_help_dialog(_h("m_reports"), _h("h_reports"))

    def _show_help_dialog(self, title, html):
        from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout
        from ui.i18n_help import help_prefix

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{help_prefix()} - {title}")
        dlg.setFixedSize(420, 380)
        try:
            from ui.tokens import BG_500, BG_400, TEXT_80

            dlg.setStyleSheet(f"QDialog {{ background: {BG_500}; }}")
            layout = QVBoxLayout(dlg)
            browser = QTextBrowser()
            browser.setHtml(
                f"<div style='color:{TEXT_80}; font-size:12px; font-family:Segoe UI; padding:8px;'>{html}</div>"
            )
            browser.setStyleSheet(
                f"QTextBrowser {{ background: {BG_400}; border: none; color: {TEXT_80}; border-radius: 3px; }}"
            )
        except Exception:
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
        self._last_scanned_paths = [folder]
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
