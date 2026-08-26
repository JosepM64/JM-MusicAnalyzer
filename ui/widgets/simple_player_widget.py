import logging
import os

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.cue_player import CUEFallbackPlayer

logger = logging.getLogger(__name__)

try:
    from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaPlayer

    _HAS_QTMULTIMEDIA = True
except ImportError:
    logger.warning("QtMultimedia no disponible - usando fallback sounddevice")
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

# Forzar fallback si estamos en exe compilado
import sys

if getattr(sys, "frozen", False):
    _HAS_QTMULTIMEDIA = False  # QtMultimedia no funciona en exe sin FFmpeg
    logger.info("Modo exe: forzando fallback sounddevice")


class SounddevicePlayer(QObject):
    """Fallback player usando sounddevice + soundfile."""

    positionChanged = Signal(int)
    playbackStateChanged = Signal(int)
    durationChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self._stream = None
        self._data = None
        self._position = 0
        self._playing = False
        self._volume = 1.0
        self._loop = False
        self._samplerate = 44100
        self._duration = 0

    def setSource(self, filename):
        if not _HAS_SOUNDDEVICE:
            return
        try:
            self._data, self._samplerate = sf.read(filename, dtype="float32")
            self._position = 0
            self._duration = len(self._data) / self._samplerate * 1000
            self.durationChanged.emit(self._duration)
            self._playing = False
        except Exception as e:
            logger.error(f"Error cargando {filename}: {e}")

    def play(self):
        if not _HAS_SOUNDDEVICE or self._data is None:
            return
        self._playing = True
        self._start_stream()
        self.playbackStateChanged.emit(1)

    def pause(self):
        self._playing = False
        if self._stream:
            self._stream.stop()
        self.playbackStateChanged.emit(0)

    def stop(self):
        self._playing = False
        self._position = 0
        if self._stream:
            self._stream.stop()
        self.playbackStateChanged.emit(0)

    def setPosition(self, position_ms):
        if self._data is not None:
            self._position = int(position_ms * self._samplerate / 1000)
            self._position = max(0, min(self._position, len(self._data)))

    def position(self):
        if self._data is None:
            return 0
        return self._position / self._samplerate * 1000

    def duration(self):
        return self._duration

    def volume(self):
        return self._volume

    def setVolume(self, vol):
        self._volume = max(0.0, min(1.0, vol))

    def playbackState(self):
        return 1 if self._playing else 0

    def isPlaying(self):
        return self._playing

    def _start_stream(self):
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        chunk_size = 1024

        def callback(outdata, frames, time_info, status):
            if not self._playing:
                outdata.fill(0)
                return
            start = self._position
            end = start + frames
            if start >= len(self._data):
                outdata.fill(0)
                self._playing = False
                self.playbackStateChanged.emit(0)
                return
            if end > len(self._data):
                chunk = self._data[start:]
                outdata[: len(chunk)] = chunk * self._volume
                outdata[len(chunk) :].fill(0)
                self._position = len(self._data)
                self._playing = False
                self.playbackStateChanged.emit(0)
            else:
                outdata[:] = self._data[start:end] * self._volume
                self._position = end

        self._stream = sd.OutputStream(
            samplerate=self._samplerate,
            channels=self._data.shape[1] if len(self._data.shape) > 1 else 2,
            callback=callback,
            blocksize=chunk_size,
        )
        self._stream.start()


class SimplePlayerWidget(QWidget):
    requestNext = Signal()
    requestPrev = Signal()
    requestDelete = Signal()
    nowPlayingChanged = Signal(str)

    def __init__(self):
        super().__init__()
        if _HAS_QTMULTIMEDIA:
            self.player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.player.setAudioOutput(self.audio_output)
            self._use_fallback = False
        elif _HAS_SOUNDDEVICE:
            self.player = SounddevicePlayer()
            self._use_fallback = True
        else:
            self.player = None
            self._use_fallback = True
        self.current_file = None
        self._auto_advance = False
        self._preview_25s = False
        self._preview_duration = 25 * 1000  # 25 segundos en ms
        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._on_preview_finished)
        self._position_timer = QTimer()
        self._position_timer.timeout.connect(self._update_position)
        self._position_timer.start(100)

        # CUE player deferred - created after show()
        self.cue_player = None
        self.cue_output = None
        self._cue_playing = False
        self._cue_update_timer = QTimer()
        self._cue_update_timer.timeout.connect(self._update_cue_progress)
        self._cue_update_timer.start(100)
        QTimer.singleShot(0, self._init_cue_player)

        self._setup_ui()
        self._setup_connections()

    def _init_cue_player(self):
        if self.cue_player is not None:
            return
        self.cue_output = None
        if _HAS_SOUNDDEVICE:
            cue_device_idx = self._get_cue_device_index()
            self.cue_player = CUEFallbackPlayer(device=cue_device_idx)
            logger.info(
                f"SimplePlayerWidget: usando CUEFallbackPlayer (sounddevice) con device={cue_device_idx}"
            )
        elif _HAS_QTMULTIMEDIA:
            self.cue_player = QMediaPlayer()
            self.cue_output = QAudioOutput()
            self.cue_player.setAudioOutput(self.cue_output)
            logger.info("SimplePlayerWidget: usando QMediaPlayer (QtMultimedia)")
        else:
            self.cue_player = None
            logger.warning("SimplePlayerWidget: sin soporte de audio para CUE")

    def _get_cue_device_index(self):
        """Obtiene el índice del dispositivo CUE configurado en settings."""
        try:
            from services.settings_manager import SettingsManager

            settings = SettingsManager()

            # Intentar primero con cue_device_idx (guardado directamente como entero)
            cue_idx = settings.get("cue_device_idx")
            if cue_idx is not None:
                try:
                    return int(cue_idx)
                except Exception:
                    pass

            # Fallback: intentar con cue_device_id
            cue_id = settings.get("cue_device_id")
            if cue_id:
                if isinstance(cue_id, int):
                    return cue_id
                if isinstance(cue_id, str) and cue_id.isdigit():
                    return int(cue_id)
        except Exception:
            pass
        return None

    def setAudioDevice(self, device):
        if self._use_fallback:
            pass  # sounddevice usa el dispositivo por defecto
        elif device:
            # device puede ser dict (de AudioHardwareService.find_device_by_id) o QAudioDevice
            if isinstance(device, dict):
                backend = device.get("backend", "")
                if backend == "qtmultimedia" and "device_obj" in device:
                    # Es un dispositivo QtMultimedia - usar el objeto QAudioDevice
                    self.audio_output.setDevice(device["device_obj"])
                elif backend == "sounddevice":
                    # sounddevice no usa QAudioOutput, se configura en el reproductor sounddevice
                    pass  # No aplica para QtMultimedia
                # Para versiones anteriores que devolvían dict sin backend
                elif "device_obj" in device:
                    self.audio_output.setDevice(device["device_obj"])
            else:
                # Es directamente un QAudioDevice
                self.audio_output.setDevice(device)

    def setCueAudioDevice(self, device):
        if not device:
            return

        # device puede ser dict (de AudioHardwareService.find_device_by_id) o QAudioDevice
        if isinstance(device, dict):
            backend = device.get("backend", "")
            if backend == "qtmultimedia" and "device_obj" in device:
                # Es un dispositivo QtMultimedia - usar el objeto QAudioDevice
                if hasattr(self, "cue_output") and self.cue_output:
                    self.cue_output.setDevice(device["device_obj"])
            elif backend == "sounddevice":
                # sounddevice usa índice numérico
                idx = device.get("index")
                if (
                    idx is not None
                    and hasattr(self, "cue_player")
                    and hasattr(self.cue_player, "setDevice")
                ):
                    self.cue_player.setDevice(idx)
            # Para versiones anteriores que devolvían dict sin backend
            elif "device_obj" in device:
                if hasattr(self, "cue_output") and self.cue_output:
                    self.cue_output.setDevice(device["device_obj"])
            elif "index" in device:
                idx = device.get("index")
                if hasattr(self, "cue_player") and hasattr(
                    self.cue_player, "setDevice"
                ):
                    self.cue_player.setDevice(idx)
        # Es directamente un QAudioDevice
        elif hasattr(self, "cue_output") and self.cue_output:
            self.cue_output.setDevice(device)

    def setVolume(self, volume_01: float):
        if self._use_fallback and self.player:
            self.player.setVolume(volume_01)
        elif self.audio_output:
            self.audio_output.setVolume(volume_01)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        # Etiqueta de info
        self.lbl_info = QLabel("Sin reproducción")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet("color: #333; font-weight: bold; font-size: 10px;")
        self.lbl_info.setMaximumHeight(16)
        main_layout.addWidget(self.lbl_info)

        # Controles principales
        ctrls = QHBoxLayout()
        ctrls.setSpacing(2)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(35)
        self.btn_play.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 2px; border-radius: 2px; }
            QPushButton:hover { background-color: #45a049; }
        """)
        ctrls.addWidget(self.btn_play)

        self.btn_cue = QPushButton("🎧")
        self.btn_cue.setFixedWidth(30)
        self.btn_cue.setCheckable(True)
        self.btn_cue.setStyleSheet("""
            QPushButton { background-color: #333; color: #00d4ff; font-weight: bold; padding: 2px; border-radius: 2px; }
            QPushButton:hover { background-color: #444; }
            QPushButton:checked { background-color: #00d4ff; color: black; }
        """)
        self.btn_cue.setToolTip("Preview en cascos (dispositivo CUE)")
        ctrls.addWidget(self.btn_cue)

        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedWidth(30)
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 2px; border-radius: 2px; }
            QPushButton:hover { background-color: #da190b; }
        """)
        ctrls.addWidget(self.btn_stop)

        # Botón canción anterior
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedWidth(30)
        self.btn_prev.setStyleSheet("""
            QPushButton { background-color: #607D8B; color: white; font-weight: bold; padding: 2px; border-radius: 2px; }
            QPushButton:hover { background-color: #455A64; }
        """)
        self.btn_prev.setToolTip("Canción anterior")
        ctrls.addWidget(self.btn_prev)

        # Botón canción siguiente
        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedWidth(30)
        self.btn_next.setStyleSheet("""
            QPushButton { background-color: #607D8B; color: white; font-weight: bold; padding: 2px; border-radius: 2px; }
            QPushButton:hover { background-color: #455A64; }
        """)
        self.btn_next.setToolTip("Siguiente canción")
        ctrls.addWidget(self.btn_next)

        # Botón borrar canción
        self.btn_delete = QPushButton("🗑")
        self.btn_delete.setFixedWidth(30)
        self.btn_delete.setStyleSheet("""
            QPushButton { background-color: #9E9E9E; color: white; font-weight: bold; padding: 2px; border-radius: 2px; }
            QPushButton:hover { background-color: #f44336; }
        """)
        self.btn_delete.setToolTip("Eliminar canción de la lista")
        ctrls.addWidget(self.btn_delete)

        self.lbl_time = QLabel("00:00")
        self.lbl_time.setStyleSheet("font-family: monospace; font-size: 9px;")
        ctrls.addWidget(self.lbl_time)

        ctrls.addStretch()

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.setMaximumWidth(60)
        ctrls.addWidget(QLabel("Vol:"))
        ctrls.addWidget(self.slider_vol)

        main_layout.addLayout(ctrls)

        # Botones de modo reproducción (gris cuando inactivos, azul cuando activos)
        mode_lay = QHBoxLayout()
        mode_lay.setSpacing(2)

        self.btn_full = QPushButton("🎵 Completa")
        self.btn_full.setCheckable(True)
        self.btn_full.setFixedHeight(20)
        self.btn_full.setStyleSheet("""
            QPushButton { background-color: #9E9E9E; color: white; font-weight: bold; padding: 1px; border-radius: 2px; font-size: 9px; }
            QPushButton:checked { background-color: #2196F3; color: white; }
            QPushButton:hover { background-color: #757575; }
            QPushButton:checked:hover { background-color: #1976D2; }
        """)
        self.btn_full.setChecked(True)
        self.btn_full.clicked.connect(lambda: self._set_mode(False))
        mode_lay.addWidget(self.btn_full)

        self.btn_preview = QPushButton("⏱ 25s")
        self.btn_preview.setCheckable(True)
        self.btn_preview.setFixedHeight(20)
        self.btn_preview.setStyleSheet("""
            QPushButton { background-color: #9E9E9E; color: white; font-weight: bold; padding: 1px; border-radius: 2px; font-size: 9px; }
            QPushButton:checked { background-color: #2196F3; color: white; }
            QPushButton:hover { background-color: #757575; }
            QPushButton:checked:hover { background-color: #1976D2; }
        """)
        self.btn_preview.clicked.connect(lambda: self._set_mode(True))
        mode_lay.addWidget(self.btn_preview)

        main_layout.addLayout(mode_lay)

        # Barra de progreso
        self.slider_progress = QSlider(Qt.Orientation.Horizontal)
        self.slider_progress.setRange(0, 0)
        self.slider_progress.setFixedHeight(12)
        self.slider_progress.sliderPressed.connect(self._on_seek_pressed)
        self.slider_progress.sliderMoved.connect(self._on_seek_moved)
        self.slider_progress.sliderReleased.connect(self._on_seek_released)
        main_layout.addWidget(self.slider_progress)

        # CUE controls (headphones preview)
        cue_lay = QHBoxLayout()
        cue_lay.setSpacing(2)
        cue_lay.addWidget(QLabel("CUE:"))
        self.slider_cue_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_cue_vol.setRange(0, 100)
        self.slider_cue_vol.setValue(70)
        self.slider_cue_vol.setMaximumWidth(60)
        self.slider_cue_vol.valueChanged.connect(self._on_cue_volume_changed)
        cue_lay.addWidget(self.slider_cue_vol)
        self.cue_progress = QProgressBar()
        self.cue_progress.setFixedWidth(80)
        self.cue_progress.setFixedHeight(6)
        self.cue_progress.setTextVisible(False)
        self.cue_progress.setStyleSheet(
            "QProgressBar::chunk { background-color: #00d4ff; }"
        )
        cue_lay.addWidget(self.cue_progress)
        cue_lay.addStretch()
        main_layout.addLayout(cue_lay)

    def _set_mode(self, preview_25s: bool):
        self._preview_25s = preview_25s
        self._auto_advance = not preview_25s  # Auto-advance solo para canción completa

        # Actualizar estado de botones (uno u otro, no ambos)
        self.btn_full.setChecked(not preview_25s)
        self.btn_preview.setChecked(preview_25s)

    def load_file(self, path: str, auto_play: bool = False):
        self.stop()
        self._stop_cue()
        self.current_file = path
        if path and os.path.exists(path):
            if self._use_fallback:
                self.player.setSource(path)  # SounddevicePlayer espera string
            else:
                self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            # Load into cue player too - CUEFallbackPlayer siempre espera string
            if self.cue_player:
                self.cue_player.setSource(path)
            music_file = None
            try:
                from core.reader.mp3_reader import MP3Reader

                reader = MP3Reader(path)
                music_file = reader.read(use_cache=True, save_db=False)
                if music_file and music_file.metadata:
                    text = f"{music_file.metadata.artist or 'Unknown'} - {music_file.metadata.title or os.path.basename(path)}"
                    self.lbl_info.setText(text)
                else:
                    text = os.path.basename(path)
                    self.lbl_info.setText(text)
            except Exception:
                text = os.path.basename(path)
                self.lbl_info.setText(text)
            self.nowPlayingChanged.emit(text)

            if auto_play:
                self.play()

            return music_file
        self.lbl_info.setText("Error: Archivo no encontrado")
        return None

    def release(self):
        self.player.stop()
        if not self._use_fallback:
            self.player.setSource(QUrl())
        self._stop_cue()

    def play(self):
        if self.current_file:
            self.player.play()
            if self._preview_25s:
                self._preview_timer.start(self._preview_duration)

    def stop(self):
        self._preview_timer.stop()
        self.player.stop()
        self.slider_progress.setValue(0)
        self.lbl_info.setText("Sin reproducción")
        self.nowPlayingChanged.emit("")

    def pause(self):
        self._preview_timer.stop()
        self.player.pause()

    def _on_preview_finished(self):
        self._preview_timer.stop()
        self.requestNext.emit()

    def _on_cue_clicked(self):
        if self._cue_playing:
            self._stop_cue()
        else:
            self._play_cue()

    def _play_cue(self):
        if self.cue_player and self.current_file:
            self._cue_playing = True
            self.btn_cue.setChecked(True)
            self.cue_player.play()

    def _stop_cue(self):
        if self.cue_player:
            self.cue_player.stop()
        self._cue_playing = False
        self.btn_cue.setChecked(False)
        self.cue_progress.setValue(0)

    def _on_cue_volume_changed(self, v):
        logger.debug(
            f"_on_cue_volume_changed: v={v}, cue_output={self.cue_output}, cue_player={type(self.cue_player)}"
        )
        if self.cue_player:
            if self.cue_output and hasattr(self.cue_output, "setVolume"):
                self.cue_output.setVolume(v / 100.0)
                logger.debug("Applied volume to cue_output")
            elif hasattr(self.cue_player, "setVolume"):
                self.cue_player.setVolume(v / 100.0)
                logger.debug(f"Applied volume to cue_player._volume={v / 100.0}")

    def _update_cue_progress(self):
        if self.cue_player and self._cue_playing:
            if hasattr(self.cue_player, "duration"):
                d = self.cue_player.duration()
                if d > 0:
                    p = (
                        self.cue_player.position()
                        if hasattr(self.cue_player, "position")
                        else 0
                    )
                    self.cue_progress.setValue(int((p / d) * 100))
                else:
                    self.cue_progress.setValue(0)
            else:
                self.cue_progress.setValue(0)
        elif not self._cue_playing:
            self.cue_progress.setValue(0)

    def _setup_connections(self):
        self.btn_play.clicked.connect(
            lambda: self.play() if self.player.playbackState() != 1 else self.pause()
        )
        self.btn_stop.clicked.connect(self.stop)
        self.btn_cue.clicked.connect(self._on_cue_clicked)
        self.btn_prev.clicked.connect(self.requestPrev.emit)
        self.btn_next.clicked.connect(self.requestNext.emit)
        self.btn_delete.clicked.connect(self.requestDelete.emit)
        self.slider_vol.valueChanged.connect(lambda v: self.setVolume(v / 100.0))

        if self.player and _HAS_QTMULTIMEDIA:
            if hasattr(self.player, "positionChanged"):
                self.player.positionChanged.connect(self._on_pos_changed)
            if hasattr(self.player, "durationChanged"):
                self.player.durationChanged.connect(self._on_duration_changed)
            if hasattr(self.player, "playbackStateChanged"):
                self.player.playbackStateChanged.connect(self._on_state_changed)
            if hasattr(self.player, "mediaStatusChanged"):
                self.player.mediaStatusChanged.connect(self._on_media_status_changed)
            self.slider_progress.sliderMoved.connect(
                lambda p: (
                    self.player.setPosition(p)
                    if self.player and hasattr(self.player, "setPosition")
                    else None
                )
            )
        elif self._use_fallback and self.player:
            if hasattr(self.player, "durationChanged"):
                self.player.durationChanged.connect(self._on_duration_changed)

    def _on_pos_changed(self, p):
        if not self.slider_progress.isSliderDown():
            self.slider_progress.setValue(p)
        self.lbl_time.setText(f"{self._format_time(p)}")

    def _on_duration_changed(self, d):
        self.slider_progress.setRange(0, d)

    def _on_seek_pressed(self):
        pass

    def _on_seek_moved(self, value):
        if self.player and hasattr(self.player, "duration"):
            d = self.player.duration()
            if d > 0:
                self.lbl_time.setText(f"{self._format_time(value)}")

    def _on_seek_released(self):
        if self.player and hasattr(self.player, "setPosition"):
            value = self.slider_progress.value()
            self.player.setPosition(value)
            if hasattr(self.player, "play") and self.player.playbackState() == 0:
                self.player.play()

    def _update_position(self):
        if self._use_fallback and self.player and hasattr(self.player, "position"):
            p = self.player.position()
            d = self.player.duration() if hasattr(self.player, "duration") else 0
            if d > 0:
                self.slider_progress.setRange(0, d)
            if not self.slider_progress.isSliderDown():
                self.slider_progress.setValue(int(p))
            self.lbl_time.setText(f"{self._format_time(int(p))}")
            # Auto-advance detection for fallback player
            if self._auto_advance and d > 0 and p >= d - 100:
                self.requestNext.emit()

    def _on_state_changed(self, state):
        if self._use_fallback:
            is_playing = state == 1
        else:
            is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.btn_play.setText("⏸ Pausa" if is_playing else "▶ Play")

    def _on_media_status_changed(self, status):
        if self._auto_advance and status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.requestNext.emit()

    def _format_time(self, ms):
        if ms <= 0:
            return "00:00"
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"
