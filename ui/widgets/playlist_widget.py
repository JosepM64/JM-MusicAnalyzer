from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from core.cue_bus import get_cue_bus
from core.cue_player import CUEFallbackPlayer
from services.app_paths import get_data_dir
from services.bookmarks_manager import BookmarksManager
from services.playlist_manager import PlaylistManager
from services.settings_manager import SettingsManager
from ui.styles import DARK_DIALOG_STYLE, icon_btn_qss
from ui.widgets.playlist_automix import PlaylistAutomixMixin
from ui.widgets.playlist_context_menu import PlaylistContextMenuMixin
from ui.widgets.playlist_cue import PlaylistCUEMixin
from ui.widgets.playlist_file_io import PlaylistFileIOMixin
from ui.widgets.playlist_filters import PlaylistFilterMixin
from ui.widgets.playlist_play_counts import PlayCountsManager
from ui.widgets.playlist_sorting import PlaylistSortingMixin
from ui.widgets.playlist_source_loaders import PlaylistSourceLoaderMixin
from ui.widgets.playlist_table_ops import PlaylistTableOpsMixin
from ui.widgets.playlist_track_ops import PlaylistTrackOpsMixin
from utils.paths import normalize_path

logger = logging.getLogger(__name__)

try:
    from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaPlayer

    _HAS_QTMULTIMEDIA = True
except ImportError:
    logger.warning("QtMultimedia no disponible")
    QMediaPlayer = None
    QAudioOutput = None
    QAudioDevice = None
    _HAS_QTMULTIMEDIA = False

try:
    import sounddevice as sd
    import soundfile as sf

    _HAS_SOUNDDEVICE = True
except ImportError:
    logger.warning("sounddevice no disponible")
    sd = None
    sf = None
    _HAS_SOUNDDEVICE = False


class PlaylistWidget(
    PlaylistAutomixMixin,
    PlaylistCUEMixin,
    PlaylistFileIOMixin,
    PlaylistFilterMixin,
    PlaylistSortingMixin,
    PlaylistSourceLoaderMixin,
    PlaylistTableOpsMixin,
    PlaylistTrackOpsMixin,
    PlaylistContextMenuMixin,
    QWidget,
):
    from PySide6.QtCore import Signal as _Signal

    trackLoaded = _Signal(str, str)
    trackSelected = _Signal(str)
    ratingChanged = _Signal(str, int)
    metadataChanged = _Signal(str, dict)
    playlistReady = _Signal()
    trackAddToMaster = _Signal(str)
    batchAddToMaster = _Signal(list)
    cuePlayStarted = _Signal()
    automixToggled = _Signal(bool)

    def __init__(self, is_master=True):
        super().__init__()
        logger.info(f"PlaylistWidget.__init__(is_master={is_master})")
        self.is_master = is_master
        self.settings = SettingsManager()
        self.pm = PlaylistManager()
        self.bm = BookmarksManager()
        self.cue_output = None
        if _HAS_SOUNDDEVICE:
            cue_device_idx = self._get_cue_device_index()
            self.cue_player = CUEFallbackPlayer(device=cue_device_idx)
            logger.info(
                f"PlaylistWidget: usando CUEFallbackPlayer (sounddevice) con device={cue_device_idx}"
            )
        elif _HAS_QTMULTIMEDIA:
            self.cue_player = QMediaPlayer()
            self.cue_output = QAudioOutput()
            self.cue_player.setAudioOutput(self.cue_output)
            logger.info("PlaylistWidget: usando QMediaPlayer (QtMultimedia)")
        else:
            self.cue_player = None
            logger.warning("PlaylistWidget: sin soporte de audio para CUE")
        self.play_counts_file = os.path.join(get_data_dir(), "play_counts.json")
        self.play_counts_manager = PlayCountsManager.shared(self.play_counts_file)
        self.play_counts_manager.add_listener(self)
        self._last_load_deck = "B"
        self.all_tracks = []
        self.filtered_tracks = []
        self.current_page = 1
        self.page_size = 100
        self.total_pages = 1
        self._current_preview_row = -1
        self._current_preview_path = None
        self._current_playlist_path = None
        self._batch_adding = False
        self._db_cache = None
        self._sorting_in_progress = False
        self._modified = False
        self._setup_ui()

        if self.is_master:
            self._load_recent()
        else:
            self._load_recent_combobox_only()
            self._current_source = None
            self._update_source_label(
                "📂 Selecciona playlist, favorito o biblioteca", "#888888"
            )

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_preview_progress)
        self.timer.start(300)
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self._apply_filters)

        # Connecta al bus global de CUE per exclusió mutua amb editor i decks
        _bus = get_cue_bus()
        _bus.cue_started.connect(self._on_global_cue_started)
        _bus.cue_stopped.connect(self._on_global_cue_stopped)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()

        self.cb_recent = QComboBox()
        self.cb_recent.setMinimumWidth(150 if not self.is_master else 200)
        top.addWidget(self.cb_recent, 1)
        self.btn_load = QPushButton("📂")
        self.btn_save = QPushButton("💾")
        self.btn_save.setToolTip(
            "Guardar (sobreescribir) - Clic derecho para 'Guardar como'"
        )
        self.btn_save.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_save.customContextMenuRequested.connect(self._on_save_context_menu)
        for b in [self.btn_load, self.btn_save]:
            b.setFixedSize(28, 28)
            b.setStyleSheet(icon_btn_qss(11))
            top.addWidget(b)

        if self.is_master:
            self.btn_new_playlist = QPushButton("🆕")
            self.btn_new_playlist.setToolTip("Crear nueva playlist (pide nombre y guarda .m3u)")
            self.btn_new_playlist.setFixedSize(28, 28)
            self.btn_new_playlist.setStyleSheet(icon_btn_qss(11))
            self.btn_new_playlist.clicked.connect(self._on_new_playlist_clicked)
            top.addWidget(self.btn_new_playlist)

            self.btn_recargar = QPushButton("🔄")
            self.btn_recargar.setToolTip("🔄 Recargar playlist desde archivo")
            self.btn_recargar.setFixedSize(28, 28)
            self.btn_recargar.setStyleSheet(icon_btn_qss(11))
            self.btn_recargar.clicked.connect(self._on_recargar_clicked)
            top.addWidget(self.btn_recargar)

        if self.is_master:
            self.btn_clear = QPushButton("🗑")
            self.btn_clear.setToolTip("Vaciar lista")
            self.btn_clear.setFixedSize(24, 24)
            self.btn_clear.setStyleSheet(icon_btn_qss(10, "color: #ff6666;"))
            self.btn_clear.clicked.connect(self._clear_all)
            top.addWidget(self.btn_clear)

            self.btn_edit_playlist = QPushButton("✏")
            self.btn_edit_playlist.setToolTip("Editar playlist en bloc de notas")
            self.btn_edit_playlist.setFixedSize(24, 24)
            self.btn_edit_playlist.setStyleSheet(icon_btn_qss(10))
            self.btn_edit_playlist.clicked.connect(self._edit_playlist_file)
            top.addWidget(self.btn_edit_playlist)
        else:
            self.btn_clear = None
            self.btn_edit_playlist = None

        if self.is_master:
            self.btn_automix = QPushButton("▶ LANZAR MIX")
            self.btn_automix.setMinimumHeight(32)
            self.btn_automix.setCheckable(True)
            self.btn_automix.setChecked(False)
            self._update_automix_button_style(False)
            top.addWidget(self.btn_automix)
        else:
            self.btn_automix = None

        if not self.is_master:
            separator = QLabel(" | ")
            separator.setStyleSheet("color: #666; font-weight: bold;")
            top.addWidget(separator)

            self.lbl_source = QLabel("📚 Biblioteca")
            self.lbl_source.setStyleSheet("""
                color: #00d4ff;
                font-weight: bold;
                font-size: 11px;
                padding: 3px 8px;
                border: 1px solid #00d4ff;
                border-radius: 3px;
                background-color: rgba(0, 212, 255, 0.1);
            """)
            top.addWidget(self.lbl_source)

            self.cb_favorites = QComboBox()
            self.cb_favorites.setMinimumWidth(150)
            self.cb_favorites.setStyleSheet("""
                QComboBox {
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 3px;
                    background-color: #333;
                    color: white;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox QAbstractItemView {
                    background-color: #333;
                    color: white;
                    selection-background-color: #6a1b9a;
                }
            """)
            self._refresh_favorites_combo()
            top.addWidget(self.cb_favorites, 1)

            self.btn_load_favorite = QPushButton("📁")
            self.btn_load_favorite.setToolTip("Cargar favorito")
            self.btn_load_favorite.setFixedSize(28, 28)
            self.btn_load_favorite.setStyleSheet(icon_btn_qss(11))
            self.btn_load_favorite.clicked.connect(self._on_load_favorite_clicked)
            top.addWidget(self.btn_load_favorite)

            self.btn_load_playlist = QPushButton("🔄")
            self.btn_load_playlist.setToolTip("🔄 Recargar")
            self.btn_load_playlist.setFixedSize(28, 28)
            self.btn_load_playlist.setStyleSheet(icon_btn_qss(11))
            self.btn_load_playlist.clicked.connect(self._on_recargar_clicked)
            top.addWidget(self.btn_load_playlist)

            self.btn_load_library = QPushButton("📚")
            self.btn_load_library.setToolTip("Cargar toda la biblioteca desde DB")
            self.btn_load_library.setFixedSize(28, 28)
            self.btn_load_library.setStyleSheet(icon_btn_qss(11))
            self.btn_load_library.clicked.connect(self._on_load_library_clicked)
            top.addWidget(self.btn_load_library)

            self.btn_refresh_favorites = QPushButton("🔄")
            self.btn_refresh_favorites.setToolTip(
                "Actualizar lista desde base de datos"
            )
            self.btn_refresh_favorites.setFixedSize(28, 28)
            self.btn_refresh_favorites.setStyleSheet(icon_btn_qss(11))
            self.btn_refresh_favorites.clicked.connect(
                self._on_refresh_favorites_clicked
            )
            top.addWidget(self.btn_refresh_favorites)

        layout.addLayout(top)

        cfg = QHBoxLayout()
        if self.is_master:
            cfg.addWidget(QLabel("Fade/Silencio (s):"))
            self.spin_fade = QSpinBox()
            self.spin_fade.setRange(-60, 60)
            self.spin_fade.setValue(-5)
            cfg.addWidget(self.spin_fade)
        else:
            self.spin_fade = None

        self.btn_reset_plays = QPushButton("🗑 Reset Plays")
        self.btn_reset_plays.setStyleSheet("font-size: 10px; color: #ff6666;")
        self.btn_reset_plays.clicked.connect(self.reset_all_play_counts)
        if not self.is_master:
            self.btn_reset_plays.setVisible(False)
        cfg.addSpacing(10)
        cfg.addWidget(self.btn_reset_plays)

        self.btn_session = QPushButton("📜 Sessió")
        self.btn_session.setStyleSheet("font-size: 10px; color: #4dabf7;")
        self.btn_session.setToolTip(
            "Cançons punxades en aquesta sessió (fins al proper Reset)"
        )
        self.btn_session.clicked.connect(self.show_session_tracks)
        cfg.addWidget(self.btn_session)

        self.btn_cleanup = QPushButton("🧹 Limpiar")
        self.btn_cleanup.setStyleSheet("font-size: 10px; color: #ffaa44;")
        self.btn_cleanup.setToolTip("Eliminar pistas que ya no existen en el disco")
        self.btn_cleanup.clicked.connect(self.cleanup_missing_files)
        cfg.addWidget(self.btn_cleanup)

        self.btn_dupes = QPushButton("🔍 Duplicats")
        self.btn_dupes.setStyleSheet("font-size: 10px; color: #bb88ff;")
        self.btn_dupes.setToolTip("Netegjar cançons duplicades a la llista carregada")
        self.btn_dupes.clicked.connect(self.cleanup_duplicates_in_playlist)
        cfg.addWidget(self.btn_dupes)

        cfg.addStretch()
        cfg.addWidget(QLabel("Vol CUE:"))
        self.slider_cue_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_cue_vol.setRange(0, 100)
        self.slider_cue_vol.setValue(70)
        self.slider_cue_vol.setFixedWidth(60)
        if hasattr(self, "cue_output") and self.cue_output:
            self.slider_cue_vol.valueChanged.connect(
                lambda v: self.cue_output.setVolume(v / 100.0)
            )
        elif (
            hasattr(self, "cue_player")
            and self.cue_player
            and hasattr(self.cue_player, "setVolume")
        ):
            self.slider_cue_vol.valueChanged.connect(
                lambda v: self.cue_player.setVolume(v / 100.0)
            )
        cfg.addWidget(self.slider_cue_vol)
        self.cue_progress = QProgressBar()
        self.cue_progress.setFixedWidth(80)
        self.cue_progress.setFixedHeight(4)
        self.cue_progress.setTextVisible(False)
        self.cue_progress.setStyleSheet(
            "QProgressBar::chunk { background-color: #00d4ff; }"
        )
        cfg.addWidget(self.cue_progress)
        layout.addLayout(cfg)

        if not self.is_master:
            filter_layout = QHBoxLayout()
            filter_layout.addWidget(QLabel("Género:"))
            self.cb_genre_filter = QComboBox()
            self.cb_genre_filter.addItem("Todos", "")
            self.cb_genre_filter.setMinimumWidth(100)
            filter_layout.addWidget(self.cb_genre_filter)

            filter_layout.addSpacing(10)
            filter_layout.addWidget(QLabel("Rating ≥:"))
            self.cb_rating_filter = QComboBox()
            rating_labels = [
                "Sin",
                "★",
                "★½",
                "★★",
                "★★½",
                "★★★",
                "★★★½",
                "★★★★",
                "★★★★½",
                "★★★★★",
            ]
            for i, label in enumerate(rating_labels):
                self.cb_rating_filter.addItem(label, i / 2.0)
            self.cb_rating_filter.setCurrentIndex(0)
            filter_layout.addWidget(self.cb_rating_filter)

            filter_layout.addSpacing(10)
            filter_layout.addWidget(QLabel("Buscar:"))
            self.edit_search = QLineEdit()
            self.edit_search.setPlaceholderText("Artista, Título...")
            self.edit_search.setMinimumWidth(120)
            filter_layout.addWidget(self.edit_search)

            self.btn_apply_filter = QPushButton("🔍 Aplicar")
            self.btn_apply_filter.clicked.connect(self._apply_filters)
            filter_layout.addWidget(self.btn_apply_filter)

            self.cb_genre_filter.currentIndexChanged.connect(self._apply_filters)
            self.cb_rating_filter.currentIndexChanged.connect(self._apply_filters)
            self.edit_search.textChanged.connect(lambda: self.filter_timer.start(300))

            filter_layout.addStretch()
            layout.addLayout(filter_layout)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "Nº",
                "CUE",
                "Plays",
                "Artista",
                "Título",
                "Duración",
                "Género",
                "Rating",
                "Carpeta",
                "Bitrate",
                "Peso",
            ]
        )
        self.table.setColumnWidth(0, 30)
        self.table.setColumnWidth(1, 30)
        self.table.setColumnWidth(2, 35)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 55)
        self.table.setColumnWidth(6, 80)
        self.table.setColumnWidth(7, 60)
        self.table.setColumnWidth(8, 160)
        self.table.setColumnWidth(9, 50)
        self.table.setColumnWidth(10, 55)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setDragEnabled(False)
        self.table.setAcceptDrops(False)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().sortIndicatorChanged.connect(
            self._on_sort_changed
        )
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1a1a1a; color: #ccc; font-size: 10px; }
            QTableWidget::item:selected { background-color: #004a80; }
            QHeaderView::section { padding: 2px; font-size: 10px; }
        """)
        layout.addWidget(self.table)
        self.table.verticalHeader().setDefaultSectionSize(18)
        self.table.verticalHeader().setVisible(False)

        if not self.is_master:
            pagination_layout = QHBoxLayout()
            pagination_layout.addWidget(QLabel("Página:"))

            self.btn_page_first = QPushButton("⏮")
            self.btn_page_prev = QPushButton("◀")
            self.lbl_page_info = QLabel("1 / 1")
            self.btn_page_next = QPushButton("▶")
            self.btn_page_last = QPushButton("⏭")

            for btn in [
                self.btn_page_first,
                self.btn_page_prev,
                self.btn_page_next,
                self.btn_page_last,
            ]:
                btn.setFixedSize(30, 25)
                btn.setStyleSheet(icon_btn_qss(12))

            self.btn_page_first.clicked.connect(lambda: self._go_to_page(1))
            self.btn_page_prev.clicked.connect(
                lambda: self._go_to_page(self.current_page - 1)
            )
            self.btn_page_next.clicked.connect(
                lambda: self._go_to_page(self.current_page + 1)
            )
            self.btn_page_last.clicked.connect(
                lambda: self._go_to_page(self.total_pages)
            )

            pagination_layout.addWidget(self.btn_page_first)
            pagination_layout.addWidget(self.btn_page_prev)
            pagination_layout.addWidget(self.lbl_page_info)
            pagination_layout.addWidget(self.btn_page_next)
            pagination_layout.addWidget(self.btn_page_last)

            pagination_layout.addSpacing(20)
            pagination_layout.addWidget(QLabel("Tracks por página:"))
            self.spin_page_size = QSpinBox()
            self.spin_page_size.setRange(10, 500)
            self.spin_page_size.setValue(self.page_size)
            self.spin_page_size.setFixedWidth(80)
            self.spin_page_size.valueChanged.connect(self._on_page_size_changed)
            pagination_layout.addWidget(self.spin_page_size)

            pagination_layout.addStretch()
            layout.addLayout(pagination_layout)

        self.btn_load.clicked.connect(self._on_load_clicked)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.cb_recent.currentIndexChanged.connect(self._on_recent_selected)
        if self.btn_automix:
            self.btn_automix.clicked.connect(self._on_automix_clicked)

    def increment_play_count(self, path):
        if not path:
            return
        self.play_counts_manager.increment(path)
        self._refresh_play_count_in_table(path)

    def _refresh_play_count_in_table(self, path=None):
        target = None
        if path is not None:
            try:
                target = normalize_path(path).lower()
            except Exception:
                target = path
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 4)
            if item is None:
                continue
            if target is not None:
                try:
                    row_key = normalize_path(
                        item.data(Qt.ItemDataRole.UserRole) or ""
                    ).lower()
                except Exception:
                    row_key = None
                if row_key != target:
                    continue
                row_path = item.data(Qt.ItemDataRole.UserRole)
            else:
                row_path = item.data(Qt.ItemDataRole.UserRole)
            play_item = self.table.item(r, 2)
            if play_item:
                play_item.setText(str(self.play_counts_manager.get(row_path)))

    def show_session_tracks(self):
        from PySide6.QtWidgets import (
            QDialog,
            QLabel,
            QPushButton,
            QTableWidgetItem,
            QVBoxLayout,
        )

        tracks = self.play_counts_manager.session_tracks()
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Punxades aquesta sessió ({len(tracks)})")
        dlg.resize(520, 400)
        dlg.setStyleSheet(DARK_DIALOG_STYLE)
        layout = QVBoxLayout(dlg)
        if not tracks:
            lbl = QLabel("Encara no s'ha punxat cap cançó en aquesta sessió.")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
        else:
            import time as _time

            table = QTableWidget(len(tracks), 4)
            table.setHorizontalHeaderLabels(["#", "Cançó", "Plays", "Hora"])
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            for i, t in enumerate(tracks):
                table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                table.setItem(
                    i, 1, QTableWidgetItem(os.path.basename(t.get("path", "")))
                )
                table.setItem(i, 2, QTableWidgetItem(str(t.get("count", 1))))
                table.setItem(
                    i,
                    3,
                    QTableWidgetItem(
                        _time.strftime(
                            "%H:%M:%S", _time.localtime(t.get("first", 0))
                        )
                    ),
                )
            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(table)
        btns = QHBoxLayout()
        btn_ok = QPushButton("Tancar")
        btn_ok.clicked.connect(dlg.accept)
        btns.addStretch()
        btns.addWidget(btn_ok)
        layout.addLayout(btns)
        dlg.exec()

    def reset_all_play_counts(self):
        """Resetea todos los contadores de reproducción a 0."""
        from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle("Resetear Plays")
        dlg.setMinimumWidth(400)
        dlg.setStyleSheet(DARK_DIALOG_STYLE)
        layout = QVBoxLayout(dlg)
        lbl = QLabel(
            "🔄 Se van a BORRAR los Plays de todas las canciones.\n\n"
            "Esta acción pone a 0 el contador de reproducciones de TODAS las canciones\n"
            "y vacía la lista de sesión (📜 Sessió).\n\n"
            "¿Continuar?"
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        btns = QHBoxLayout()
        btn_no = QPushButton("No")
        btn_yes = QPushButton("Sí")
        btn_yes.setStyleSheet("background-color: #d32f2f;")
        btns.addStretch()
        btns.addWidget(btn_no)
        btns.addWidget(btn_yes)
        layout.addLayout(btns)

        btn_no.clicked.connect(dlg.reject)
        btn_yes.clicked.connect(dlg.accept)

        if dlg.exec():
            self.play_counts_manager.reset_all()
            for r in range(self.table.rowCount()):
                it = self.table.item(r, 2)
                if it:
                    it.setText("0")

    def _on_new_playlist_clicked(self):
        """Crea una playlist vacía pidiendo el nombre al usuario."""
        if self.is_modified():
            reply = QMessageBox.question(
                self,
                "Playlist modificada",
                "La playlist principal tiene cambios sin guardar.\n"
                "¿Desea guardarlos antes de crear una nueva?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._on_save_clicked()
                if self.is_modified():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        default_dir = str(self.settings.get("default_playlist_dir", ""))
        if not default_dir:
            default_dir = os.path.expanduser("~")

        name, ok = QInputDialog.getText(
            self,
            "Nueva playlist",
            "Nombre de la nueva playlist:",
            text="Nueva playlist",
        )
        if not ok or not name.strip():
            return

        name = name.strip()
        if not name.lower().endswith(".m3u"):
            name += ".m3u"

        new_path = os.path.join(default_dir, name)

        if os.path.exists(new_path):
            reply = QMessageBox.question(
                self,
                "Playlist ya existe",
                f"La playlist '{name}' ya existe.\n"
                "¿Desea sobreescribirla?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Limpiar playlist actual y establecer la nueva
        self.table.setRowCount(0)
        self.all_tracks = []
        self.filtered_tracks = []
        self.current_page = 1
        self.total_pages = 1
        self._current_playlist_path = new_path
        self._modified = False
        self._db_cache = None

        self.pm.record_playlist_usage(new_path)
        self._add_to_recent_combo(new_path)

        logger.info(f"Nueva playlist creada: {new_path}")

    def is_modified(self):
        return self._modified
