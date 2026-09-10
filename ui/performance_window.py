import logging
import os
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QMessageBox

from ui.perf_window_bpm import PerfBpmMixin
from ui.perf_window_crossfader import PerfCrossfaderMixin
from ui.perf_window_decks import PerfDeckMixin
from ui.perf_window_transition import PerfTransitionMixin
from ui.perf_window_ui import PerfUIMixin

logger = logging.getLogger(__name__)

try:
    import JM_MusicAnalizer

    APP_VERSION = getattr(JM_MusicAnalizer, "APP_VERSION", "4.43.0")

    if not APP_VERSION or APP_VERSION.startswith("${"):
        APP_VERSION = "4.43.0"
except (ImportError, ModuleNotFoundError):
    APP_VERSION = "4.43.0"

try:
    from PySide6.QtMultimedia import QMediaPlayer

    _HAS_QTMULTIMEDIA = True
except ImportError:
    logger.warning("QtMultimedia no disponible")
    QMediaPlayer = None
    _HAS_QTMULTIMEDIA = False

# Forzar fallback si estamos en exe compilado
import sys

if getattr(sys, "frozen", False):
    _HAS_QTMULTIMEDIA = False  # QtMultimedia no funciona en exe sin FFmpeg
    logger.info("Modo exe: forzando fallback sounddevice")

try:
    from core.audio_engine import MasterEngine
    from core.reader.mp3_reader import MP3Reader
    from core.writer.tag_writer import TagWriter
    from services.audio_hardware_service import AudioHardwareService
    from services.metadata_service import MetadataService
    from services.settings_manager import SettingsManager
    from ui.dialogs.about_dialog import AboutDialog
    from ui.dialogs.audio_config_dialog import AudioConfigDialog
    from ui.dialogs.settings_dialog import SettingsDialog
    from ui.styles import load_audio_devices_from_settings
    from ui.widgets.audio_engine_player import AudioEnginePlayerWidget
    from ui.widgets.cover_widget import CoverWidget
    from ui.widgets.player_widget import PlayerWidget
    from ui.widgets.playlist_widget import PlaylistWidget
    from ui.widgets.rating_widget import RatingWidget
except ImportError:
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.audio_engine import MasterEngine
    from core.reader.mp3_reader import MP3Reader
    from services.audio_hardware_service import AudioHardwareService
    from services.metadata_service import MetadataService
    from services.settings_manager import SettingsManager
    from ui.dialogs.about_dialog import AboutDialog
    from ui.dialogs.audio_config_dialog import AudioConfigDialog
    from ui.dialogs.settings_dialog import SettingsDialog
    from ui.widgets.audio_engine_player import AudioEnginePlayerWidget
    from ui.widgets.cover_widget import CoverWidget
    from ui.widgets.player_widget import PlayerWidget
    from ui.widgets.playlist_widget import PlaylistWidget
    from ui.widgets.rating_widget import RatingWidget


class PerformanceWindow(
    PerfDeckMixin,
    PerfCrossfaderMixin,
    PerfTransitionMixin,
    PerfBpmMixin,
    PerfUIMixin,
    QMainWindow,
):
    """
    Frontend especializado para DJ (Modo Performance).
    Gestiona la lógica de transición suave (Mixer Engine).
    """

    closed = Signal()

    def __init__(self):
        super().__init__()
        logger.info("=== PerformanceWindow.__init__ started ===")
        self.setWindowTitle(f"JM-MusicAnalyzer v{APP_VERSION} - DJ PERFORMANCE MODE")
        self.setWindowIcon(QIcon("resources/icons/JM_MusicAnalyzer.ico"))
        self.resize(1280, 720)

        self.settings = SettingsManager()
        self.metadata_service = MetadataService()
        self._automix_active = False
        self._deck_started = {"A": False, "B": False}
        self._transition_in_progress = False
        self._manual_crossfade = False
        self._playlist_index = 0  # Índice de la próxima canción a cargar
        self._playlist_tracks = []  # Lista completa de tracks de la playlist
        self._vu_update_count = 0
        self._last_log_time = 0  # Para limitar logs de _check_automix
        self._s_timer = None  # Timer para silencio en modo automix
        self._fallback_timer = None  # Timer de fallback por si no se detecta fin
        self._deck_tracks = {"A": None, "B": None}  # Metadatos de pista actual por deck

        # Motor de audio - sounddevice + soundfile (Native Audio Engine)
        self._use_simple_engine = False
        self.simple_engine = None
        self._use_audio_engine = True
        try:
            self.master_engine = MasterEngine(samplerate=44100, blocksize=1024)
            self.master_engine.start()

            # Verificar que l'stream està corrent
            if (
                hasattr(self.master_engine, "is_running")
                and self.master_engine.is_running
            ):
                logger.info("[OK] sounddevice stream ACTIU - MasterEngine funcionant")
            else:
                logger.warning("[ERR] sounddevice stream NO funciona")
                self.master_engine = None
                self._use_audio_engine = False
        except Exception as e:
            logger.error(f"[ERR] Error iniciant MasterEngine: {e}")
            import traceback

            traceback.print_exc()
            self.master_engine = None
            self._use_audio_engine = False

        # Timer de transición (Fade dinámico ultra-suave)
        self._fade_timer = QTimer()
        self._fade_timer.timeout.connect(self._handle_transition_logic)
        self._fade_current_val = -100.0
        self._fade_step = 0.0
        self._fade_target_val = -100.0

        import time

        t0 = time.perf_counter()

        logger.info("Applying dark theme...")
        self._apply_dark_theme()
        logger.info(f"  -> dark theme: {time.perf_counter() - t0:.3f}s")

        t1 = time.perf_counter()
        logger.info("Setting up UI...")
        self._setup_ui()
        logger.info(f"  -> setup UI: {time.perf_counter() - t1:.3f}s")

        t2 = time.perf_counter()
        logger.info("Loading hardware settings...")
        self._load_hardware_settings()
        logger.info(f"  -> hardware: {time.perf_counter() - t2:.3f}s")

        # Mode compacte (Space per amagar/mostrar plats)
        self._compact_mode = False
        self._compact_sc = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self._compact_sc.activated.connect(self._toggle_compact_mode)

        logger.info("Connecting signals...")
        self.playlist_widget.playlistReady.connect(self._on_playlist_ready)
        self.playlist_widget.playlistReady.connect(self._update_master_playlist_label)

        # Cargar última playlist automáticamente
        self._load_last_playlist()

        # Conectar CUE entre listas: cuando una reproduce, detener la otra
        self.playlist_widget.cuePlayStarted.connect(
            self.second_playlist_widget.stop_cue
        )
        self.second_playlist_widget.cuePlayStarted.connect(
            self.playlist_widget.stop_cue
        )

        logger.info(
            f"=== PerformanceWindow.__init__ TOTAL: {time.perf_counter() - t0:.3f}s ==="
        )

    def closeEvent(self, event):
        # Comprovar si la master playlist té canvis no guardats
        if self.playlist_widget.is_modified():
            reply = QMessageBox.question(
                self,
                "Playlist modificada",
                "La playlist principal tiene cambios sin guardar.\n¿Deseas guardar antes de salir?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self.playlist_widget._on_save_clicked()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        # Detener reproductores antes de cerrar
        try:
            self.deck_a.stop()
            self.deck_b.stop()
        except Exception:
            pass

        # Detener preescucha (CUE) en ambas listas
        try:
            if (
                hasattr(self.playlist_widget, "cue_player")
                and self.playlist_widget.cue_player
            ):
                self.playlist_widget.cue_player.stop()
        except Exception:
            pass
        try:
            if (
                hasattr(self.second_playlist_widget, "cue_player")
                and self.second_playlist_widget.cue_player
            ):
                self.second_playlist_widget.cue_player.stop()
        except Exception:
            pass

        # Detener timer de automix si está activo
        if self._fade_timer.isActive():
            self._fade_timer.stop()

        # Detener timer VU
        if hasattr(self, "_vu_timer") and self._vu_timer.isActive():
            self._vu_timer.stop()

        # Detener timer compact bar
        if hasattr(self, "_compact_timer") and self._compact_timer.isActive():
            self._compact_timer.stop()

        # Detener MasterEngine
        if hasattr(self, "master_engine") and self.master_engine:
            try:
                self.master_engine.stop()
            except Exception:
                pass

        self.closed.emit()
        super().closeEvent(event)
