import logging
import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .deck_bpm import DeckBpmMixin
from .deck_controls import DeckControlsMixin
from .deck_vinyl import DeckVinylMixin, GenreLabel, VinylWidget

logger = logging.getLogger(__name__)

try:
    from core.audio_engine import DeckBuffered as Deck
    from core.audio_engine import MasterEngine
    from core.cue_player import CUEFallbackPlayer

    logger.info(
        f"AudioEngine importat: MasterEngine={MasterEngine is not None}, Deck={Deck is not None}"
    )
except ImportError as e:
    MasterEngine = None
    Deck = None
    CUEFallbackPlayer = None
    logger.error(f"Error important AudioEngine: {e}")
    import traceback

    traceback.print_exc()


class AudioEnginePlayerWidget(DeckVinylMixin, DeckControlsMixin, DeckBpmMixin, QWidget):
    """
    Reproductor basado en el motor de audio customizado.
    Usa sounddevice + soundfile para reproducción de alta calidad.
    """

    requestNext = Signal()
    bpmAdjusted = Signal(object)  # Emite el BPM ajustado (int) o None

    def __init__(self, name="DECK", master_engine=None, cue_device=None):
        super().__init__()
        self.name = name
        self.current_file = None

        # Motor de audio compartido o nuevo
        if master_engine:
            self.master = master_engine
        else:
            try:
                self.master = MasterEngine(samplerate=44100, blocksize=1024)
                self.master.start()
            except Exception as e:
                logger.error(f"Error creating MasterEngine: {e}")
                self.master = None

        # Deck individual
        if Deck and self.master:
            self.deck = Deck(self.master)
            self.deck_id = self.master.register_deck(self.deck)
        else:
            logger.error("Cannot create Deck - Deck or master is None")
            self.deck = None
            self.deck_id = None

        # Timer para actualizar UI
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._update_ui)
        self._ui_timer.start(100)

        # Estado anterior para detectar fin de reproducción
        self._last_playing_state = False
        self._request_next_emitted = False  # Evitar múltiples emisiones requestNext
        self._seeking = False  # Estado del seek slider
        self._seek_value = 0  # Valor del slider durante arrastre

        # BPM tracking (Quick Adjust)
        self._original_bpm = None
        self.current_bpm = None
        self.bpm_adjustment = 0

        # Crear compatibilidad con API anterior
        self._player_compat = self._create_player_compat()

        # CUE player per pre-escolta (independent del deck principal)
        self._cue_player = None
        self._cue_playing = False
        if CUEFallbackPlayer:
            try:
                # Convertir device a índex si és diccionari
                cue_dev_index = cue_device
                if isinstance(cue_device, dict):
                    cue_dev_index = cue_device.get("index")
                self._cue_player = CUEFallbackPlayer(device=cue_dev_index)
                logger.info(
                    f"Deck {name}: CUE player creat amb device index={cue_dev_index}"
                )
            except Exception as e:
                logger.warning(f"Deck {name}: no s'ha pogut crear CUE player: {e}")

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(3)

        self.lbl_deck = QLabel(self.name)
        self.lbl_deck.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_deck.setStyleSheet(
            "font-weight: bold; color: cyan; font-size: 12px; padding: 0px; margin: 0px; border-bottom: 2px solid #0078d4;"
        )
        main_layout.addWidget(self.lbl_deck)

        self.lbl_genre_big = QLabel("")
        self.lbl_genre_big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_genre_big.setFixedHeight(0)
        self.lbl_genre_big.setStyleSheet(
            "font-weight: bold; color: #00d4ff; font-size: 16px; padding: 0px; margin: 0px;"
        )
        main_layout.addWidget(self.lbl_genre_big)

        self.lbl_key_big = QLabel("")
        self.lbl_key_big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_key_big.setFixedHeight(0)
        self.lbl_key_big.setStyleSheet(
            "font-weight: bold; font-size: 12px; padding: 0px; margin: 0px;"
        )
        main_layout.addWidget(self.lbl_key_big)

        bpm_layout = QHBoxLayout()
        bpm_layout.setSpacing(2)
        self.lbl_bpm_display = QLabel("BPM: --")
        self.lbl_bpm_display.setStyleSheet(
            "color: #ccc; font-size: 11px; font-weight: bold;"
        )
        bpm_layout.addWidget(self.lbl_bpm_display)
        # Beat Counter (1-2-3-4)
        self._beat_labels = []
        for i in range(4):
            lbl = QLabel(str(i + 1))
            lbl.setFixedSize(20, 18)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "font-size: 9px; font-weight: bold; color: #555; background: #1a1a1a; border: 1px solid #333; border-radius: 3px;"
            )
            bpm_layout.addWidget(lbl)
            self._beat_labels.append(lbl)
        # Botones -10, -5, -1
        for delta in [-10, -5, -1]:
            btn = QPushButton(f"{delta:+d}")
            btn.setFixedSize(24, 20)
            btn.setStyleSheet(
                "font-size: 8px; background: #333; color: white; border: 1px solid #444; border-radius: 3px;"
            )
            btn.clicked.connect(lambda checked, d=delta: self.adjust_bpm(d))
            bpm_layout.addWidget(btn)
        # Rate indicator + Reset
        self.lbl_rate = QLabel("100%")
        self.lbl_rate.setFixedSize(40, 18)
        self.lbl_rate.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rate.setStyleSheet(
            "font-size: 8px; font-weight: bold; color: #aaa; background: #1a1a1a; border: 1px solid #333; border-radius: 3px;"
        )
        bpm_layout.addWidget(self.lbl_rate)
        self.btn_bpm_reset = QPushButton("R")
        self.btn_bpm_reset.setFixedSize(22, 18)
        self.btn_bpm_reset.setToolTip("Reset BPM a original")
        self.btn_bpm_reset.setStyleSheet(
            "font-size: 9px; font-weight: bold; background: #444; color: #ddd; border: 1px solid #666; border-radius: 3px;"
        )
        self.btn_bpm_reset.clicked.connect(self._reset_bpm)
        bpm_layout.addWidget(self.btn_bpm_reset)
        # Botones +1, +5, +10
        for delta in [1, 5, 10]:
            btn = QPushButton(f"{delta:+d}")
            btn.setFixedSize(24, 20)
            btn.setStyleSheet(
                "font-size: 8px; background: #333; color: white; border: 1px solid #444; border-radius: 3px;"
            )
            btn.clicked.connect(lambda checked, d=delta: self.adjust_bpm(d))
            bpm_layout.addWidget(btn)
        main_layout.addLayout(bpm_layout)

        main_layout.addSpacing(2)

        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(6)

        mid_layout.addStretch()

        # Vinyl - plat al centre
        self.vinyl = VinylWidget(size=230)
        mid_layout.addWidget(self.vinyl)

        # VOLUME a la dreta del vinil
        vol_lay = QVBoxLayout()
        vol_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vol_lay.setSpacing(2)  # Espacio entre etiqueta y slider
        lbl_vol = QLabel("VOL")
        lbl_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vol_lay.addWidget(lbl_vol)
        self.slider_vol = QSlider(Qt.Orientation.Vertical)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.setMinimumHeight(45)
        vol_lay.addWidget(self.slider_vol)
        mid_layout.addLayout(vol_lay)

        # CUE VOLUME (més petit)
        cue_vol_lay = QVBoxLayout()
        cue_vol_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cue_vol_lay.setSpacing(2)  # Espacio entre etiqueta y slider
        lbl_cue = QLabel("CUE")
        lbl_cue.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cue_vol_lay.addWidget(lbl_cue)
        self.slider_cue_vol = QSlider(Qt.Orientation.Vertical)
        self.slider_cue_vol.setRange(0, 100)
        self.slider_cue_vol.setValue(50)
        self.slider_cue_vol.setMinimumHeight(35)
        cue_vol_lay.addWidget(self.slider_cue_vol)
        mid_layout.addLayout(cue_vol_lay)

        mid_layout.addStretch()

        main_layout.addLayout(mid_layout)

        main_layout.addSpacing(2)

        self.lbl_info = QLabel("...")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setWordWrap(True)  # Permet multilinea
        self.lbl_info.setStyleSheet("""
color: white;
font-weight: bold;
font-size: 11px;
padding: 2px;
qproperty-textFormat: PlainText;
""")
        main_layout.addWidget(self.lbl_info)

        # Género - visible y grande con gradient animat
        self.lbl_genre = GenreLabel("")
        self.lbl_genre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_genre.setMinimumHeight(22)
        main_layout.addWidget(self.lbl_genre)

        main_layout.addSpacing(2)

        ctrls = QHBoxLayout()
        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setMinimumHeight(28)
        self.btn_play.setStyleSheet(
            "font-weight: bold; background-color: #1a3a1a; color: #44ff44; border: 1px solid #2a5a2a; border-radius: 4px;"
        )
        self.btn_play.clicked.connect(self.toggle_play_pause)
        ctrls.addWidget(self.btn_play, 1)

        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedSize(28, 28)
        self.btn_stop.setStyleSheet(
            "background-color: #3a1a1a; color: #ff4444; border: 1px solid #5a2a2a; border-radius: 4px;"
        )
        self.btn_stop.clicked.connect(self.stop)
        ctrls.addWidget(self.btn_stop)

        # Botó CUE (pre-escolta per auriculars)
        self.btn_cue = QPushButton("🎧")
        self.btn_cue.setFixedSize(28, 28)
        self.btn_cue.setStyleSheet(
            "background-color: #1a1a3a; color: #6688ff; border: 1px solid #2a2a5a; border-radius: 4px;"
        )
        self.btn_cue.clicked.connect(self._toggle_cue)
        ctrls.addWidget(self.btn_cue)

        main_layout.addLayout(ctrls)

        main_layout.addSpacing(2)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet(
            "font-family: monospace; font-size: 10px; color: #888;"
        )
        main_layout.addWidget(self.lbl_time)

        # Slider progreso
        self.slider_progress = QSlider(Qt.Orientation.Horizontal)
        self.slider_progress.setRange(0, 100)
        self.slider_progress.setTracking(True)
        self.slider_progress.setStyleSheet("""
            QSlider::groove:horizontal { background: #333; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #0078d4; width: 14px; margin: -4px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #0078d4; border-radius: 3px; }
        """)
        self.slider_progress.sliderPressed.connect(self._on_seek_pressed)
        self.slider_progress.sliderMoved.connect(self._on_seek_moved)
        self.slider_progress.sliderReleased.connect(self._on_seek_released)
        main_layout.addWidget(self.slider_progress)

        # Conectar slider volumen (master deck)
        self.slider_vol.valueChanged.connect(self._on_vol_changed)
        self._on_vol_changed(self.slider_vol.value())

        # Conectar slider volumen CUE
        self.slider_cue_vol.valueChanged.connect(self._on_cue_vol_changed)
        self._on_cue_vol_changed(self.slider_cue_vol.value())

    def _update_ui(self):
        if self.deck and self.deck.is_loaded:
            # Posición actual
            pos = self.deck.get_position()
            total = self.deck.get_duration_samples()

            if total > 0:
                progress = pos / total * 100
                if not self.slider_progress.isSliderDown():
                    self.slider_progress.setValue(int(progress))

                # Tiempo
                pos_sec = pos / self.deck.samplerate
                total_sec = total / self.deck.samplerate
                self.lbl_time.setText(
                    f"{self._format_time(pos_sec)} / {self._format_time(total_sec)}"
                )
                # Emitir posición para automix
                if hasattr(self, "_player_compat") and self._player_compat:
                    self._player_compat._update_position(pos, self.deck.samplerate)

                # Vinyl
                self.vinyl.set_spinning(self.deck.is_playing)

                # Botón Play
                is_playing = self.deck.is_playing
                self.btn_play.setText("⏸ PAUSE" if is_playing else "▶ PLAY")
                if is_playing:
                    self.btn_play.setStyleSheet(
                        "font-weight: bold; background-color: #0078d4; color: white; border: 2px solid #005a9e; border-radius: 4px;"
                    )
                else:
                    self.btn_play.setStyleSheet(
                        "font-weight: bold; background-color: #222; color: white; border: 1px solid #444; border-radius: 4px;"
                    )

                # Beat Counter
                self._update_beat_counter(pos_sec)

                # Fin de canción - detección robusta con protección anti-duplicados
                # 1. Emitir 2 segundos antes del final para anticipar
                if (
                    pos >= total - (self.deck.samplerate * 2)
                    and self.deck.is_playing
                    and not self._request_next_emitted
                ):
                    logger.debug(
                        f"[AudioEnginePlayer] Emitiendo requestNext (2s antes del final) para {self.name}"
                    )
                    self.requestNext.emit()
                    self._request_next_emitted = True

                # 2. Detectar cuando la reproducción se detiene (transición playing → stopped)
                if (
                    self._last_playing_state
                    and not self.deck.is_playing
                    and not self._request_next_emitted
                ):
                    logger.debug(
                        f"[AudioEnginePlayer] Emitiendo requestNext (detenido) para {self.name}"
                    )
                    self.requestNext.emit()
                    self._request_next_emitted = True

                # Actualizar estado anterior
                self._last_playing_state = self.deck.is_playing

    def _format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def load(self, filepath):
        """Carga un archivo"""
        if not filepath or not os.path.exists(filepath):
            logger.warning(f"[AudioEnginePlayer] File not found: {filepath}")
            return False

        if not self.deck:
            logger.error("[AudioEnginePlayer] Cannot load - deck is None")
            return False

        logger.info(f"[AudioEnginePlayer] load(): {filepath}")
        self.stop()
        self._last_playing_state = False
        self._request_next_emitted = False  # Resetear flag para nueva canción
        self._stop_cue_internal()  # Aturar CUE si n'hi ha un d'actiu

        try:
            if self.deck.load(filepath):
                self.current_file = filepath
                basename = os.path.basename(filepath)
                bpm_val = None  # Se capturará de metadatos si existe

                # Carregar portada
                try:
                    from core.reader.mp3_reader import MP3Reader

                    reader = MP3Reader(filepath)
                    mf = reader.read(use_cache=False, save_db=False)
                    if mf and mf.metadata:
                        if mf.metadata.cover_data:
                            self.vinyl.set_cover(mf.metadata.cover_data)
                            # Títol i artista en una línia
                            title = mf.metadata.title or basename
                            artist = mf.metadata.artist or ""
                            if artist:
                                self.lbl_info.setText(f"{artist} - {title}")
                            else:
                                self.lbl_info.setText(title)
                            # Mostrar gènere grande
                            genre = mf.metadata.genre or ""
                            self.lbl_genre.setText(genre if genre else "Desconegut")
                    else:
                        self.vinyl.set_cover(None)
                        self.lbl_info.setText(
                            basename[:40] + "..." if len(basename) > 40 else basename
                        )
                        self.lbl_genre.setText("Desconegut")
                except Exception:
                    self.vinyl.set_cover(None)
                    self.lbl_info.setText(
                        basename[:30] + "..." if len(basename) > 30 else basename
                    )
                    self.lbl_genre.setText("")

                # Actualizar deck_id después de la carga
                self.deck_id = (
                    self.deck.deck_id if hasattr(self.deck, "deck_id") else None
                )
                logger.info(
                    f"[AudioEnginePlayer] deck.load() returned True, deck_id={self.deck_id}"
                )
                return True
            logger.warning("[AudioEnginePlayer] deck.load() returned False")
            return False
        except Exception as e:
            logger.error(f"[AudioEnginePlayer] Error loading file: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _create_player_compat(self):
        """Crea objeto de compatibilidad con API anterior"""

        class _Signal:
            def __init__(self):
                self._callbacks = []

            def connect(self, callback):
                self._callbacks.append(callback)

            def emit(self, *args):
                for cb in self._callbacks:
                    cb(*args)

        class State:
            PlayingState = 1
            StoppedState = 0
            PausedState = 2

        class PlayerCompat:
            def __init__(self, outer):
                self.outer = outer
                self._position = 0
                self._duration = 0
                self._state = State.StoppedState
                self.positionChanged = _Signal()
                self.durationChanged = _Signal()
                self.playbackStateChanged = _Signal()
                self.mediaStatusChanged = _Signal()

            def play(self):
                self.outer._play_internal()
                self._state = State.PlayingState
                self.playbackStateChanged.emit(self._state)

            def pause(self):
                self.outer.pause()
                if self.outer.deck:
                    self.outer.deck.is_playing = False
                    self.outer.deck.is_paused = True
                self._state = State.PausedState
                self.playbackStateChanged.emit(self._state)

            def stop(self):
                self.outer.stop()
                self._state = State.StoppedState
                self.playbackStateChanged.emit(self._state)

            def setSource(self, url):
                if url:
                    self.outer.load(str(url))

            def setPosition(self, pos):
                self._position = pos
                self.positionChanged.emit(pos)

            def duration(self):
                deck = getattr(self.outer, "deck", None)
                if deck and deck.is_loaded:
                    dur = deck.get_duration_samples()
                    if deck.samplerate > 0:
                        return int(dur / deck.samplerate * 1000)
                return 0

            def playbackState(self):
                deck = getattr(self.outer, "deck", None)
                if deck:
                    if deck.is_playing:
                        return State.PlayingState
                    if deck.is_paused:
                        return State.PausedState
                return State.StoppedState

            def position(self):
                deck = getattr(self.outer, "deck", None)
                if deck and deck.is_loaded and deck.samplerate > 0:
                    pos = deck.get_position()
                    return int(pos / deck.samplerate * 1000)
                return 0

            def _update_position(self, pos_samples, samplerate):
                if samplerate > 0:
                    self._position = int(pos_samples / samplerate * 1000)
                    self.positionChanged.emit(self._position)

        return PlayerCompat(self)

    @property
    def player(self):
        """Propiedad de compatibilidad con API anterior"""
        return self._player_compat

    def load_file(self, filepath, auto_play=False):
        """Carga archivo (compatibilidad)"""
        if self.load(filepath):
            if auto_play:
                self._play_internal()
            return True
        return False

    def _play_internal(self):
        """Reproduce (interno)"""
        if self.deck:
            self.deck.is_paused = False
            self.deck.is_playing = True
            self.deck.play()
