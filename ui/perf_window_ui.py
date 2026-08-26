import logging

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCompleter,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.widgets.audio_engine_player import AudioEnginePlayerWidget
from ui.widgets.cover_widget import CoverWidget
from ui.widgets.player_widget import PlayerWidget
from ui.widgets.playlist_widget import PlaylistWidget
from ui.widgets.rating_widget import RatingWidget

logger = logging.getLogger(__name__)

try:
    import JM_MusicAnalizer

    APP_VERSION = getattr(JM_MusicAnalizer, "APP_VERSION", "4.43.0")

    if not APP_VERSION or APP_VERSION.startswith("${"):
        APP_VERSION = "4.43.0"
except (ImportError, ModuleNotFoundError):
    APP_VERSION = "4.43.0"


class PerfUIMixin:
    def _apply_dark_theme(self):
        p = self.palette()
        p.setColor(QPalette.ColorRole.Window, QColor(20, 20, 20))
        p.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        p.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        p.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
        self.setPalette(p)
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLabel { color: #eee; font-family: 'Segoe UI', sans-serif; }
            QToolBar { background-color: #222; border-bottom: 1px solid #444; spacing: 10px; }
            QPushButton { 
                background-color: #333; color: white; border: 1px solid #444; padding: 6px; border-radius: 4px; font-weight: bold; 
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #0078d4; }
        """)

    def _setup_ui(self):
        self.toolbar = QToolBar("DJ Tools")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        self.btn_exit = QPushButton("\U0001f519 VOLVER")
        self.btn_exit.clicked.connect(self.close)
        self.toolbar.addWidget(self.btn_exit)
        self.toolbar.addSeparator()
        self.btn_audio_setup = QPushButton("\U0001f3a7 CONFIG AUDIO")
        self.btn_audio_setup.clicked.connect(self._on_audio_config)
        self.toolbar.addWidget(self.btn_audio_setup)
        self.btn_global_settings = QPushButton("\u2699\ufe0f")
        self.btn_global_settings.clicked.connect(self._on_open_settings)
        self.toolbar.addWidget(self.btn_global_settings)
        self.btn_about = QPushButton("\u2139\ufe0f ACERCA")
        self.btn_about.clicked.connect(self._on_about)
        self.toolbar.addWidget(self.btn_about)
        self.btn_help_dj = QPushButton("?")
        self.btn_help_dj.setFixedSize(24, 24)
        self.btn_help_dj.setToolTip("Ayuda rápida DJ")
        self.btn_help_dj.setStyleSheet(
            "QPushButton { font-size: 12px; font-weight: bold; border: 1px solid #555; border-radius: 12px; background: #444; color: #ddd; } QPushButton:hover { background: #0078d4; color: white; }"
        )
        self.btn_help_dj.clicked.connect(self._show_dj_help)
        self.toolbar.addWidget(self.btn_help_dj)
        self.btn_toggle_list = QPushButton("\U0001f4cb LISTA 2")
        self.btn_toggle_list.setCheckable(True)
        self.btn_toggle_list.clicked.connect(self._toggle_second_list)
        self.toolbar.addWidget(self.btn_toggle_list)
        self.toolbar.addSeparator()

        # BOTÓN SIGUIENTE (Transición Manual Progresiva)
        self.btn_next_now = QPushButton("\u23ed\ufe0f CROSSFADER")
        self.btn_next_now.setStyleSheet(
            "background-color: #8a2be2; color: white; padding: 0 15px;"
        )
        self.btn_next_now.clicked.connect(self._on_skip_and_mix)
        self.toolbar.addWidget(self.btn_next_now)

        # Botón modo compacto
        self.btn_compact_mode = QPushButton("\U0001f5d4 COMPACT")
        self.btn_compact_mode.setCheckable(True)
        self.btn_compact_mode.setToolTip(
            "Modo compacto (Espacio) - oculta platos para ver más lista"
        )
        self.btn_compact_mode.setStyleSheet("font-size: 10px; padding: 4px 8px;")
        self.btn_compact_mode.clicked.connect(self._toggle_compact_mode)
        self.toolbar.addWidget(self.btn_compact_mode)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # Indicador de motor de audio
        self.lbl_audio_engine = QLabel("\U0001f3b5 sounddevice + soundfile")
        self.lbl_audio_engine.setStyleSheet(
            "color: #00ff00; font-weight: bold; font-size: 11px;"
        )
        self.lbl_audio_engine.setToolTip(
            "sounddevice + soundfile (Native Audio Engine)"
        )
        self.toolbar.addWidget(self.lbl_audio_engine)

        # Indicador de dispositivos de audio configurados
        self._update_audio_device_label()

        self.toolbar.addSeparator()

        # BPM Match Indicator
        self.lbl_bpm_match = QLabel("BPM: --")
        self.lbl_bpm_match.setStyleSheet(
            "color: #aaa; font-size: 10px; font-weight: bold;"
        )
        self.lbl_bpm_match.setToolTip(
            "Diferencia BPM entre decks (verde: \u00b10-3, amarillo: \u00b14-8, rojo: \u00b19+)"
        )
        self.toolbar.addWidget(self.lbl_bpm_match)
        self.lbl_bpm_match.setVisible(False)  # Oculto por defecto

        title_label = QLabel(f"<b>JM DJ ENGINE v{APP_VERSION}</b>")
        title_label.setStyleSheet("color: #0078d4; font-size: 14px;")
        self.toolbar.addWidget(title_label)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(3)

        decks_layout = QHBoxLayout()
        decks_layout.setContentsMargins(0, 0, 0, 0)
        # Usar AudioEnginePlayerWidget v3.0
        if self._use_audio_engine and self.master_engine:
            try:
                self.deck_a = AudioEnginePlayerWidget("DECK A", self.master_engine)
                self.deck_b = AudioEnginePlayerWidget("DECK B", self.master_engine)
                # Conectar señal de ajuste BPM (Quick BPM Adjust)
                if hasattr(self.deck_a, "bpmAdjusted"):
                    self.deck_a.bpmAdjusted.connect(
                        lambda bpm, d="A": self._on_bpm_adjusted(d, bpm)
                    )
                if hasattr(self.deck_b, "bpmAdjusted"):
                    self.deck_b.bpmAdjusted.connect(
                        lambda bpm, d="B": self._on_bpm_adjusted(d, bpm)
                    )
                if not self.deck_a.deck or not self.deck_b.deck:
                    logger.error("AudioEngine Deck és None - fallback a QMediaPlayer")
                    self._use_audio_engine = False
            except Exception as e:
                logger.error(f"Error creant AudioEnginePlayerWidget: {e}")
                self._use_audio_engine = False

        if not self._use_audio_engine:
            self.deck_a = PlayerWidget("DECK A")
            self.deck_b = PlayerWidget("DECK B")
        self.mixer_panel = self._create_mixer_panel()
        decks_layout.addWidget(self.deck_a, 1)
        decks_layout.addWidget(self.mixer_panel, 1)
        decks_layout.addWidget(self.deck_b, 1)
        self.decks_container = QWidget()
        self.decks_container.setLayout(decks_layout)
        main_layout.addWidget(self.decks_container, 0)

        self._setup_compact_bar()
        main_layout.addWidget(self.compact_bar, 0)
        self.compact_bar.setVisible(False)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.setHandleWidth(8)
        bottom_splitter.setStyleSheet("""
            QSplitter::handle { background-color: #555; border: 1px solid #666; }
            QSplitter::handle:hover { background-color: #0078d4; }
        """)
        self.playlist_widget = PlaylistWidget(is_master=True)
        self.playlist_widget.trackLoaded.connect(self._on_track_loaded)
        self.playlist_widget.trackSelected.connect(self._on_track_selected_in_list)
        self.playlist_widget.startAutomix.connect(self._on_start_automix)
        self.playlist_widget.automixToggled.connect(self._on_automix_toggled)
        self.playlist_widget.ratingChanged.connect(self._on_save_rating)

        # Master playlist (sin botón de cargar extra - el PlaylistWidget ya lo tiene)
        playlist_with_btn = QWidget()
        playlist_vbox = QVBoxLayout(playlist_with_btn)
        playlist_vbox.setContentsMargins(0, 0, 0, 0)
        playlist_vbox.setSpacing(2)

        load_bar = QHBoxLayout()
        self.lbl_master_playlist = QLabel(
            "<b>\U0001f4dc MASTER PLAYLIST:</b> <span style='color:#888'>Ninguna</span>"
        )
        self.lbl_master_playlist.setStyleSheet("font-size: 11px;")
        load_bar.addWidget(self.lbl_master_playlist)
        load_bar.addStretch()
        playlist_vbox.addLayout(load_bar)

        playlist_vbox.addWidget(self.playlist_widget)
        bottom_splitter.addWidget(playlist_with_btn)

        # Panel derecho: Stacked widget (info de pista / segunda lista)
        self.right_stacked = QStackedWidget()

        # Página 0: Info de pista con metadatos editables
        self.info_panel = QFrame()
        self.info_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.info_panel.setStyleSheet("background-color: #1a1a1a;")
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setSpacing(4)

        # Portada
        self.cover_view = CoverWidget(size=160)
        info_layout.addWidget(self.cover_view, 0, Qt.AlignmentFlag.AlignCenter)

        # Título y artista
        self.lbl_track_info = QLabel("<b>INFO DE PISTA</b>")
        self.lbl_track_info.setStyleSheet("color: #00d4ff; font-size: 11px;")
        info_layout.addWidget(self.lbl_track_info)

        self.lbl_now_playing = QLabel("No hay pista cargada")
        self.lbl_now_playing.setWordWrap(True)
        self.lbl_now_playing.setStyleSheet("color: #ccc; font-size: 10px;")
        info_layout.addWidget(self.lbl_now_playing)

        # Ruta del archivo
        self.lbl_file_path = QLabel("")
        self.lbl_file_path.setWordWrap(True)
        self.lbl_file_path.setStyleSheet(
            "color: #888; font-size: 9px; font-family: monospace;"
        )
        self.lbl_file_path.setMaximumHeight(32)
        info_layout.addWidget(self.lbl_file_path)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #333;")
        info_layout.addWidget(sep)

        # Sección de metadatos editables
        meta_label = QLabel("<b>\u270f\ufe0f METADATOS</b>")
        meta_label.setStyleSheet("color: #aaa; font-size: 10px;")
        info_layout.addWidget(meta_label)

        # Campos de edición
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("Título")
        self.edit_title.setMaximumHeight(20)
        self.edit_title.setStyleSheet(
            "color: #000; background-color: #fff; border: 1px solid #444; font-size: 10px; padding: 1px 3px;"
        )
        info_layout.addWidget(self.edit_title)

        self.edit_artist = QLineEdit()
        self.edit_artist.setPlaceholderText("Artista")
        self.edit_artist.setMaximumHeight(20)
        self.edit_artist.setStyleSheet(
            "color: #000; background-color: #fff; border: 1px solid #444; font-size: 10px; padding: 1px 3px;"
        )
        info_layout.addWidget(self.edit_artist)

        self.edit_genre = QLineEdit()
        self.edit_genre.setPlaceholderText("Género")
        self.edit_genre.setMaximumHeight(20)
        self.edit_genre.setStyleSheet(
            "color: #000; background-color: #fff; border: 1px solid #444; font-size: 10px; padding: 1px 3px;"
        )
        info_layout.addWidget(self.edit_genre)

        # Completers para autocomplete
        self.artist_completer = QCompleter()
        self.artist_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.artist_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.edit_artist.setCompleter(self.artist_completer)

        self.genre_completer = QCompleter()
        self.genre_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.genre_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.edit_genre.setCompleter(self.genre_completer)

        # Cargar sugerencias desde DB
        self._load_metadata_suggestions()

        # Rating
        rating_layout = QHBoxLayout()
        rating_layout.addWidget(QLabel("\u2605:"))
        self.rating_edit = RatingWidget(star_size=14, editable=True)
        rating_layout.addWidget(self.rating_edit)
        rating_layout.addStretch()
        info_layout.addLayout(rating_layout)

        # Botón guardar
        self.btn_save_metadata = QPushButton("\U0001f4be GUARDAR")
        self.btn_save_metadata.setFixedHeight(24)
        self.btn_save_metadata.setStyleSheet(
            "background-color: #6a1b9a; color: white; font-weight: bold; font-size: 10px; border-radius: 3px;"
        )
        self.btn_save_metadata.clicked.connect(self._save_metadata_from_info_panel)
        self.btn_save_metadata.setEnabled(False)
        info_layout.addWidget(self.btn_save_metadata)

        info_layout.addStretch()
        self.right_stacked.addWidget(self.info_panel)

        # Página 1: Segunda lista (biblioteca/favoritos)
        self.second_playlist_widget = PlaylistWidget(is_master=False)
        self.second_playlist_widget.trackLoaded.connect(self._on_track_loaded)
        self.second_playlist_widget.trackSelected.connect(
            self._on_track_selected_in_list
        )
        # No conectar startAutomix para la segunda lista (solo master)
        self.second_playlist_widget.ratingChanged.connect(self._on_save_rating)
        self.second_playlist_widget.trackAddToMaster.connect(self._add_track_to_master)
        self.second_playlist_widget.batchAddToMaster.connect(self._add_tracks_to_master)
        self.right_stacked.addWidget(self.second_playlist_widget)

        bottom_splitter.addWidget(self.right_stacked)
        self.right_stacked.setMinimumWidth(100)
        self.second_playlist_widget.setMinimumWidth(80)
        bottom_splitter.setStretchFactor(0, 3)
        bottom_splitter.setStretchFactor(1, 2)
        bottom_splitter.setSizes([1100, 750])
        main_layout.addWidget(bottom_splitter, 3)

        self.deck_a.player.positionChanged.connect(
            lambda p: self._check_automix(p, "A")
        )
        self.deck_b.player.positionChanged.connect(
            lambda p: self._check_automix(p, "B")
        )
        self.deck_a.requestNext.connect(lambda: self._on_deck_finished("A"))
        self.deck_b.requestNext.connect(lambda: self._on_deck_finished("B"))

        # Timer para actualizar medidores VU - optimizado a 100ms (10fps)
        self._vu_timer = QTimer(self)
        self._vu_timer.timeout.connect(self._update_vu_meters)
        self._vu_timer.start(100)  # 10fps - suficiente para VU meters

    def _create_mixer_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #252525; border: 1px solid #333;")
        main_lay = QVBoxLayout(panel)
        main_lay.setContentsMargins(5, 5, 5, 5)
        main_lay.setSpacing(8)

        # === Fila 1: VU-L | MASTER | VU-R ===
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        # VU-L (Deck A) - QProgressBar simple
        self.vu_left = QProgressBar()
        self.vu_left.setOrientation(Qt.Orientation.Vertical)
        self.vu_left.setFixedWidth(14)
        self.vu_left.setMinimumHeight(180)
        self.vu_left.setRange(0, 100)
        self.vu_left.setValue(0)
        self.vu_left.setTextVisible(False)
        self.vu_left.setStyleSheet(
            "QProgressBar { border: 1px solid #333; border-radius: 2px; background-color: #0a0a0a; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff0000, stop:0.7 #ffff00, stop:1 #00ff00); border-radius: 1px; }"
        )

        # Master Central
        master_col = QVBoxLayout()
        master_col.setSpacing(4)
        master_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_master = QLabel("MASTER")
        lbl_master.setStyleSheet("color: #aaa; font-weight: bold; font-size: 11px;")
        master_col.addWidget(lbl_master, 0, Qt.AlignmentFlag.AlignCenter)

        # Master: slider + gradiente como UNIDAD
        master_unit = QHBoxLayout()
        master_unit.setSpacing(2)
        master_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Escala numérica 300-0 (a la izquierda del slider)
        scale_num = QVBoxLayout()
        scale_num.setSpacing(0)
        lbl_300 = QLabel("300")
        lbl_300.setStyleSheet("color: #ff4444; font-size: 9px; font-weight: bold;")
        lbl_200 = QLabel("200")
        lbl_200.setStyleSheet("color: #888; font-size: 9px; font-weight: bold;")
        lbl_100 = QLabel("100")
        lbl_100.setStyleSheet("color: #666; font-size: 8px;")
        lbl_0 = QLabel("0")
        lbl_0.setStyleSheet("color: #888; font-size: 9px; font-weight: bold;")
        scale_num.addWidget(lbl_300, 0, Qt.AlignmentFlag.AlignRight)
        scale_num.addWidget(lbl_200, 0, Qt.AlignmentFlag.AlignRight)
        scale_num.addWidget(lbl_100, 0, Qt.AlignmentFlag.AlignRight)
        scale_num.addWidget(lbl_0, 0, Qt.AlignmentFlag.AlignRight)

        # Slider vertical - rang augmentat per més gain
        self.vol_master = QSlider(Qt.Orientation.Vertical)
        self.vol_master.setRange(0, 300)  # Fins a 300%
        self.vol_master.setValue(100)
        self.vol_master.setFixedWidth(40)
        self.vol_master.setFixedHeight(180)
        self.vol_master.setTickPosition(QSlider.TickPosition.TicksRight)
        self.vol_master.setTickInterval(50)
        self.vol_master.setToolTip(
            "Master Volume\n100% = nivel unity\n>100% = gain extra\n300% = màxim gain"
        )
        self.vol_master.valueChanged.connect(self._on_master_vol_changed)

        # Gradiente de color (a la derecha del slider)
        gradient = QFrame()
        gradient.setFixedWidth(16)
        gradient.setStyleSheet("""
            QFrame { background: qlineargradient(x1:0,y1:1, x2:0,y2:0, 
                stop:0 #00aa00, stop:0.4 #00aa00, stop:0.6 #ffff00, stop:0.75 #ff8800, stop:1 #ff0000); 
                border-radius: 2px; }
        """)

        master_unit.addLayout(scale_num)
        master_unit.addWidget(self.vol_master)
        master_unit.addWidget(gradient)

        # Info: volumen + botón + CLIP
        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        info_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_master_vol = QLabel("100%")
        self.lbl_master_vol.setFixedWidth(50)
        self.lbl_master_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_master_vol.setStyleSheet(
            "color: cyan; font-weight: bold; font-size: 12px;"
        )

        self.btn_master_reset = QPushButton("100%")
        self.btn_master_reset.setFixedSize(36, 20)
        self.btn_master_reset.setStyleSheet(
            "font-size: 9px; font-weight: bold; background-color: #555; color: white; padding: 0px; border: 1px solid #777;"
        )
        self.btn_master_reset.setToolTip("Resetear a 100% (sin ganancia extra)")
        self.btn_master_reset.clicked.connect(lambda: self.vol_master.setValue(100))

        self.lbl_clip = QLabel("CLIP")
        self.lbl_clip.setFixedSize(40, 18)
        self.lbl_clip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_clip.setStyleSheet("""
            background-color: #222; color: #444; 
            font-weight: bold; font-size: 9px;
            border-radius: 2px;
        """)
        self.lbl_clip.setToolTip("¡Pico detectado! Los picos superan 100%")

        info_row.addWidget(self.lbl_master_vol)
        info_row.addWidget(self.btn_master_reset)
        info_row.addWidget(self.lbl_clip)

        master_col.addLayout(master_unit)
        master_col.addLayout(info_row)

        # VU-R (Deck B) - QProgressBar simple
        self.vu_right = QProgressBar()
        self.vu_right.setOrientation(Qt.Orientation.Vertical)
        self.vu_right.setFixedWidth(14)
        self.vu_right.setMinimumHeight(180)
        self.vu_right.setRange(0, 100)
        self.vu_right.setValue(0)
        self.vu_right.setTextVisible(False)
        self.vu_right.setStyleSheet(
            "QProgressBar { border: 1px solid #333; border-radius: 2px; background-color: #0a0a0a; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff0000, stop:0.7 #ffff00, stop:1 #00ff00); border-radius: 1px; }"
        )

        # Ensamblar: VU-L | master | VU-R con labels
        vu_left_col = QVBoxLayout()
        vu_left_col.setSpacing(1)
        lbl_vu_l = QLabel("A")
        lbl_vu_l.setStyleSheet("color: #00aaff; font-size: 8px; font-weight: bold;")
        lbl_vu_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vu_left_col.addWidget(lbl_vu_l)
        vu_left_col.addWidget(self.vu_left, 0, Qt.AlignmentFlag.AlignHCenter)

        vu_right_col = QVBoxLayout()
        vu_right_col.setSpacing(1)
        lbl_vu_r = QLabel("B")
        lbl_vu_r.setStyleSheet("color: #ff6600; font-size: 8px; font-weight: bold;")
        lbl_vu_r.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vu_right_col.addWidget(lbl_vu_r)
        vu_right_col.addWidget(self.vu_right, 0, Qt.AlignmentFlag.AlignHCenter)

        row1.addStretch(1)
        row1.addLayout(vu_left_col)
        row1.addLayout(master_col, 0)
        row1.addLayout(vu_right_col)
        row1.addStretch(1)

        main_lay.addLayout(row1)

        # Forzar show y repaint de VU meters
        self.vu_left.show()
        self.vu_right.show()
        self.vu_left.repaint()
        self.vu_right.repaint()

        # === Fila 2: Crossfader ===

        # Separador visual
        sep_cf = QFrame()
        sep_cf.setFrameShape(QFrame.Shape.HLine)
        sep_cf.setStyleSheet("color: #333;")
        main_lay.addWidget(sep_cf)

        cf_row = QHBoxLayout()
        cf_row.setSpacing(4)
        lbl_a_cf = QLabel("A \u25c4")
        lbl_a_cf.setStyleSheet("color: #00aaff; font-size: 9px; font-weight: bold;")
        cf_row.addWidget(lbl_a_cf)
        self.crossfader = QSlider(Qt.Orientation.Horizontal)
        self.crossfader.setRange(-100, 100)
        self.crossfader.setValue(-100)
        self.crossfader.setFixedHeight(30)
        self.crossfader.valueChanged.connect(self._on_crossfader_changed)
        self.crossfader.setStyleSheet(
            "QSlider::groove:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0078d4, stop:0.5 #444, stop:1 #ff6600); height: 8px; border-radius: 4px; } "
            "QSlider::handle:horizontal { background: #fff; width: 14px; height: 18px; margin: -6px 0; border-radius: 3px; border: 1px solid #888; } "
            "QSlider::sub-page:horizontal { background: transparent; } "
            "QSlider::add-page:horizontal { background: transparent; }"
        )
        cf_row.addWidget(self.crossfader, 1)
        lbl_b_cf = QLabel("\u25ba B")
        lbl_b_cf.setStyleSheet("color: #ff6600; font-size: 9px; font-weight: bold;")
        cf_row.addWidget(lbl_b_cf)
        main_lay.addLayout(cf_row)

        # Separador visual
        sep_tt = QFrame()
        sep_tt.setFrameShape(QFrame.Shape.HLine)
        sep_tt.setStyleSheet("color: #333;")
        main_lay.addWidget(sep_tt)

        # Timer de transicion visible
        timer_row = QHBoxLayout()
        timer_row.setSpacing(5)
        timer_row.addStretch()
        self.lbl_transition_timer = QLabel("\u23f1 --")
        self.lbl_transition_timer.setStyleSheet(
            "color: #aaa; font-size: 10px; font-weight: bold;"
        )
        timer_row.addWidget(self.lbl_transition_timer)
        timer_row.addStretch()
        main_lay.addLayout(timer_row)

        # === Fila 3: Controles de transición ===
        trans_row = QHBoxLayout()
        trans_row.setSpacing(5)

        # Botón SKIP (transición rápida sin esperar fade)
        self.btn_skip = QPushButton("\u23ed SKIP")
        self.btn_skip.setFixedSize(70, 28)
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background-color: #8a2be2; color: white; font-weight: bold; font-size: 11px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #9b4de0; }
        """)
        self.btn_skip.setToolTip("Saltar inmediatamente (sin esperar fade)")
        trans_row.addStretch()

        self.btn_skip.clicked.connect(self._on_skip_now)
        trans_row.addWidget(self.btn_skip)

        # Botón LOOP (extender final de canción)
        self.btn_loop = QPushButton("\U0001f501 LOOP")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setFixedSize(70, 28)
        self.btn_loop.setStyleSheet("""
            QPushButton {
                background-color: #333; color: #888; font-weight: bold; font-size: 11px;
                border-radius: 3px; border: 1px solid #444;
            }
            QPushButton:checked {
                background-color: #00aa00; color: white;
            }
        """)
        self.btn_loop.setToolTip("Activar loop al final de la canción")
        self.btn_loop.clicked.connect(self._on_loop_toggle)
        trans_row.addWidget(self.btn_loop)

        trans_row.addStretch()
        main_lay.addLayout(trans_row)

        return panel

    def _setup_compact_bar(self):
        self.compact_bar = QWidget()
        self.compact_bar.setStyleSheet("""
            QWidget { background-color: #1a1a1a; }
            QProgressBar { background: #2a2a2a; border: 1px solid #444; border-radius: 2px; height: 10px; text-align: center; }
            QProgressBar::chunk { background: #0078d4; border-radius: 2px; }
            QSlider::groove:horizontal { background: #333; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background: #0078d4; width: 10px; margin: -3px 0; border-radius: 5px; }
            QSlider::sub-page:horizontal { background: #555; border-radius: 2px; }
        """)
        self._compact = {"A": {}, "B": {}}
        outer = QVBoxLayout(self.compact_bar)
        outer.setContentsMargins(4, 2, 4, 2)
        outer.setSpacing(2)
        columns = QHBoxLayout()
        columns.setSpacing(8)
        left = self._make_compact_column("A")
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #333;")
        right = self._make_compact_column("B")
        columns.addLayout(left, 1)
        columns.addWidget(sep)
        columns.addLayout(right, 1)
        outer.addLayout(columns, 1)

        # Crossfader slider interactiu
        xf_row = QHBoxLayout()
        xf_row.setSpacing(4)
        self._compact_xf_label = QLabel("CROSSFADER")
        self._compact_xf_label.setStyleSheet(
            "color: #666; font-size: 8px; font-weight: bold;"
        )
        self._compact_xf_label.setFixedWidth(70)
        xf_row.addWidget(self._compact_xf_label)
        lbl_a = QLabel("A")
        lbl_a.setStyleSheet("color: #0078d4; font-size: 8px; font-weight: bold;")
        xf_row.addWidget(lbl_a)
        self._compact_xf_slider = QSlider(Qt.Orientation.Horizontal)
        self._compact_xf_slider.setRange(-100, 100)
        self._compact_xf_slider.setValue(-100)
        self._compact_xf_slider.setFixedHeight(16)
        self._compact_xf_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #1a1a2a; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #0078d4; width: 12px; margin: -3px 0; border-radius: 6px; }
            QSlider::sub-page:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0078d4, stop:0.5 #44ff44, stop:1 #0078d4); border-radius: 3px; }
        """)
        self._compact_xf_slider.valueChanged.connect(self._on_compact_xf_changed)
        xf_row.addWidget(self._compact_xf_slider, 1)
        lbl_b = QLabel("B")
        lbl_b.setStyleSheet("color: #0078d4; font-size: 8px; font-weight: bold;")
        xf_row.addWidget(lbl_b)
        outer.addLayout(xf_row)
        self._compact_timer = QTimer(self)
        self._compact_timer.timeout.connect(self._update_compact_bar)

    def _make_compact_column(self, letter):
        col = QVBoxLayout()
        col.setSpacing(2)
        c = self._compact[letter]

        # Header row: label + play + stop
        header = QHBoxLayout()
        header.setSpacing(3)
        lbl = QLabel(f"DECK {letter}")
        lbl.setStyleSheet("color: #0078d4; font-weight: bold; font-size: 10px;")
        header.addWidget(lbl)
        header.addStretch()
        btn_play = QPushButton("\u25b6")
        btn_play.setFixedSize(22, 20)
        btn_play.setStyleSheet(
            "font-size: 9px; background: #1a3a1a; color: #4a4; border: 1px solid #2a5a2a; border-radius: 3px;"
        )
        btn_play.clicked.connect(
            lambda checked=False, l=letter: self._compact_play_pause(l)
        )
        header.addWidget(btn_play)
        c["play"] = btn_play
        btn_stop = QPushButton("\u23f9")
        btn_stop.setFixedSize(20, 20)
        btn_stop.setStyleSheet(
            "font-size: 9px; background: #3a1a1a; color: #a44; border: 1px solid #5a2a2a; border-radius: 3px;"
        )
        btn_stop.clicked.connect(lambda checked=False, l=letter: self._compact_stop(l))
        header.addWidget(btn_stop)
        c["stop"] = btn_stop
        col.addLayout(header)

        info = QLabel("...")
        info.setStyleSheet("color: #ccc; font-size: 10px; padding: 0 4px;")
        col.addWidget(info)
        c["info"] = info

        # Progress row
        prog_row = QHBoxLayout()
        prog_row.setSpacing(4)
        prg = QProgressBar()
        prg.setFixedHeight(8)
        prg.setTextVisible(False)
        prog_row.addWidget(prg, 1)
        c["progress"] = prg
        tm = QLabel("00:00/00:00")
        tm.setStyleSheet("color: #888; font-size: 9px; font-family: monospace;")
        prog_row.addWidget(tm)
        c["time"] = tm
        col.addLayout(prog_row)

        # Volume row
        vol_row = QHBoxLayout()
        vol_row.setSpacing(3)
        lbl_v = QLabel("VOL")
        lbl_v.setStyleSheet("color: #888; font-size: 8px;")
        vol_row.addWidget(lbl_v)
        vol = QSlider(Qt.Orientation.Horizontal)
        vol.setRange(0, 100)
        vol.setValue(80)
        vol.valueChanged.connect(lambda v, l=letter: self._compact_vol_changed(l, v))
        vol_row.addWidget(vol, 1)
        c["vol"] = vol
        col.addLayout(vol_row)

        return col

    def _update_compact_bar(self):
        for letter in ("A", "B"):
            c = self._compact[letter]
            deck = self.deck_a if letter == "A" else self.deck_b
            if not deck or not deck.deck or not deck.deck.is_loaded:
                c["info"].setText("\u2014")
                c["progress"].setValue(0)
                c["time"].setText("00:00/00:00")
                c["play"].setText("\u25b6")
                c["play"].setStyleSheet(
                    "font-size: 9px; background: #1a3a1a; color: #4a4; border: 1px solid #2a5a2a; border-radius: 3px;"
                )
                continue
            c["info"].setText(deck.lbl_info.text())
            pos = deck.deck.get_position()
            total = deck.deck.get_duration_samples()
            sr = deck.deck.samplerate
            if total > 0:
                pct = int(pos * 100 / total)
                c["progress"].setValue(pct)
                ps = pos / sr
                ts = total / sr
                c["time"].setText(
                    f"{int(ps // 60):02d}:{int(ps % 60):02d}/{int(ts // 60):02d}:{int(ts % 60):02d}"
                )
            is_playing = deck.deck.is_playing
            c["play"].setText("\u23f8" if is_playing else "\u25b6")
            c["play"].setStyleSheet(
                "font-size: 9px; background: #0078d4; color: white; border: 1px solid #005a9e; border-radius: 3px;"
                if is_playing
                else "font-size: 9px; background: #1a3a1a; color: #4a4; border: 1px solid #2a5a2a; border-radius: 3px;"
            )
            c["vol"].blockSignals(True)
            c["vol"].setValue(deck.slider_vol.value())
            c["vol"].blockSignals(False)

        # Crossfader slider (synced from real crossfader, signals blocked)
        xf_val = self.crossfader.value() if hasattr(self, "crossfader") else 0
        xf_active = self._transition_in_progress or self._fade_timer.isActive()
        self._compact_xf_slider.blockSignals(True)
        self._compact_xf_slider.setValue(xf_val)
        self._compact_xf_slider.blockSignals(False)
        if xf_active:
            self._compact_xf_label.setText("\u23f3 CROSSFADER")
            self._compact_xf_label.setStyleSheet(
                "color: #44ff44; font-size: 8px; font-weight: bold;"
            )
        else:
            self._compact_xf_label.setText("CROSSFADER")
            self._compact_xf_label.setStyleSheet(
                "color: #666; font-size: 8px; font-weight: bold;"
            )

    def _compact_play_pause(self, letter):
        deck = self.deck_a if letter == "A" else self.deck_b
        if deck:
            deck.toggle_play_pause()

    def _compact_stop(self, letter):
        deck = self.deck_a if letter == "A" else self.deck_b
        if deck:
            deck.stop()

    def _compact_vol_changed(self, letter, value):
        deck = self.deck_a if letter == "A" else self.deck_b
        if deck:
            deck.slider_vol.setValue(value)

    def _on_compact_xf_changed(self, value):
        if hasattr(self, "crossfader"):
            self.crossfader.setValue(value)

    def _toggle_compact_mode(self):
        """Alterna mode compacte: amaga/mostra plats i mixer per veure més llista.
        No afecta la reproducció d'àudio."""
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QComboBox, QSpinBox, QTextBrowser)):
            return

        self._compact_mode = not self._compact_mode
        self.decks_container.setVisible(not self._compact_mode)
        self.compact_bar.setVisible(self._compact_mode)
        self.btn_compact_mode.setChecked(self._compact_mode)

        if self._compact_mode:
            self._update_compact_bar()
            self._compact_timer.start(200)
        else:
            self._compact_timer.stop()

        mode = "COMPACT" if self._compact_mode else "NORMAL"
        logger.info(f"DJ Mode toggled: {mode}")

    def _toggle_second_list(self, checked):
        # Alternar entre info de pista (0) y segunda lista (1)
        if checked:
            self.right_stacked.setCurrentIndex(1)
            self.btn_toggle_list.setText("\U0001f4cb LISTA 2 \U0001f504")
            # Ya NO se carga automáticamente la biblioteca para evitar freeze con muchos tracks
            # El usuario debe hacer clic en el botón "📚" o seleccionar un favorito del desplegable
        else:
            self.right_stacked.setCurrentIndex(0)
            self.btn_toggle_list.setText("\U0001f4cb LISTA 2")
            # Forzar actualización de la tabla de info (opcional)
            self.playlist_widget.table.viewport().update()

    def _on_about(self):
        """Muestra el diálogo 'Acerca de'."""
        dlg = AboutDialog(self)
        dlg.exec()

    def _on_open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def _show_dj_help(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2b2b2b; color: #e0e0e0; border: 1px solid #555; padding: 4px; } QMenu::item { padding: 6px 20px; } QMenu::item:selected { background: #0078d4; }"
        )
        act_playback = menu.addAction("Reproducción y Decks")
        act_crossfader = menu.addAction("Crossfader y Mezcla")
        act_playlist = menu.addAction("Playlists")
        act_audio = menu.addAction("Audio y CUE")

        action = menu.exec_(
            self.mapToGlobal(
                self.btn_help_dj.pos() + QPoint(0, self.btn_help_dj.height())
            )
        )

        if action == act_playback:
            self._show_help_dialog(
                "Reproducción y Decks",
                "<b>Deck A / Deck B</b>: Dos reproductores independientes. Carga canciones desde las playlists.<br><br>"
                "<b>⏭ SKIP</b>: Salta inmediatamente a la siguiente canción sin esperar fade.<br><br>"
                "<b>🔁 LOOP</b>: Activa loop al final de la canción actual para extenderla.<br><br>"
                "<b>⏭️ MEZCLAR SIGUIENTE YA</b>: Inicia la transición al siguiente tema inmediatamente.<br><br>"
                "<b>Automix</b>: Reproducción automática con crossfade entre pistas consecutivas.<br><br>"
                "<b>🗔 COMPACT</b> (o tecla Espacio): Oculta los platos y mixer para ver más lista. "
                "Aparece una barra compacta con controles esenciales: play/pause, stop, información de pista, "
                "barra de progreso, volumen y crossfader interactivo.",
            )
        elif action == act_crossfader:
            self._show_help_dialog(
                "Crossfader y Mezcla",
                "<b>Crossfader</b>: Desliza para mezclar entre Deck A (izquierda) y Deck B (derecha).<br><br>"
                "<b>Fade Time</b>: Ajusta la velocidad del crossfade automático (0.5s - 10s).<br><br>"
                "<b>Vol Master</b>: Control de volumen general. El botón 100% resetea sin ganancia extra.<br><br>"
                "<b>CLIP</b>: Indicador de pico de señal. Si se ilumina, reduce el volumen master.<br><br>"
                "<b>VU Meters</b>: Barras de nivel de señal para cada deck.",
            )
        elif action == act_playlist:
            self._show_help_dialog(
                "Playlists",
                "<b>📂 Cargar</b>: Carga una playlist desde archivo M3U/M3U8 o escanea una carpeta.<br><br>"
                "<b>💾 Guardar</b>: Guarda la playlist actual como M3U.<br><br>"
                "<b>📋 LISTA 2</b>: Activa/desactiva una segunda lista independiente para el Deck B.<br><br>"
                "<b>CUE (🎧)</b>: Pre-escucha una pista por auriculares sin enviarla a los altavoces.<br><br>"
                "<b>Vol CUE</b>: Control de volumen independiente para la pre-escucha.<br><br>"
                "<b>Rating</b>: Puntuación por estrellas en cada fila. Se guarda en la BD automáticamente.<br><br>"
                "<b>Arrastrar</b>: Reordena pistas arrastrando filas dentro de la lista.",
            )
        elif action == act_audio:
            self._show_help_dialog(
                "Audio y CUE",
                "<b>🎧 CONFIG AUDIO</b>: Configura los dispositivos de salida (Master y CUE/auriculares).<br><br>"
                "<b>📢 Master</b>: Salida principal (altavoces/amplificadores).<br><br>"
                "<b>🎧 CUE</b>: Salida para auriculares (pre-escucha). Permite escuchar antes de mezclar.<br><br>"
                "<b>🔄 Crossfader</b>: Transición suave entre Deck A y Deck B. Desliza para mezclar.<br><br>"
                "<b>⚙️ Ajustes</b>: Configuración general de la aplicación.",
            )

    def _show_help_dialog(self, title, html):
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
