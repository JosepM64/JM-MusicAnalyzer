import logging
import os

from PySide6.QtCore import QPointF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

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
    import numpy as np
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

from PySide6.QtCore import QObject

if getattr(sys, "frozen", False):
    _HAS_QTMULTIMEDIA = False  # QtMultimedia no funciona en exe sin FFmpeg
    logger.info("Modo exe: forzando fallback sounddevice")


class DeckFallbackPlayer(QObject):
    """Fallback player para DJ Deck usando sounddevice + soundfile."""

    positionChanged = Signal(int)
    durationChanged = Signal(int)
    playbackStateChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self._stream = None
        self._data = None
        self._position = 0
        self._playing = False
        self._volume = 1.0
        self._samplerate = 44100
        self._duration = 0
        self._source_url = ""

    def setSource(self, url):
        if not _HAS_SOUNDDEVICE:
            return
        try:
            path = url.toLocalFile() if hasattr(url, "toLocalFile") else str(url)
            if not path or not os.path.exists(path):
                return
            self._source_url = path
            self._data, self._samplerate = sf.read(path, dtype="float32")
            self._position = 0
            self._duration = int(len(self._data) / self._samplerate * 1000)
            self._playing = False
            self.durationChanged.emit(self._duration)
        except Exception as e:
            logger.error(f"Error cargando {url}: {e}")
            self._data = None
            self._duration = 0

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
        return int(self._position / self._samplerate * 1000)

    def duration(self):
        return self._duration

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
        if self._data is None:
            return
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
            self.positionChanged.emit(self.position())

        try:
            self._stream = sd.OutputStream(
                samplerate=self._samplerate,
                channels=2 if len(self._data.shape) > 1 else self._data.shape[1],
                callback=callback,
                blocksize=chunk_size,
            )
            self._stream.start()
        except Exception as e:
            logger.error(f"Error iniciando audio stream: {e}")


class VinylWidget(QWidget):
    def __init__(self, size=150):
        super().__init__()
        self.setFixedSize(size, size)
        self.angle = 0.0
        self._pixmap = None
        self._is_spinning = False
        self._cached_scaled = None
        self._cached_diameter = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(33)  # ~30fps - animación fluida del plato

    def set_cover(self, data):
        if not data:
            self._pixmap = None
        else:
            img = QImage.fromData(data)
            self._pixmap = QPixmap.fromImage(img)
        self._cached_scaled = None
        self.update()

    def set_spinning(self, spinning: bool):
        self._is_spinning = spinning

    def _update_animation(self):
        if self._is_spinning:
            self.angle = (self.angle + 3.0) % 360  # 3 grados por frame = más fluido
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()
        center = rect.center()
        radius = rect.width() // 2 - 5
        painter.setBrush(QBrush(QColor(10, 10, 10)))
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.drawEllipse(center, radius, radius)
        grad = QConicalGradient(QPointF(center), self.angle)
        grad.setColorAt(0, QColor(255, 255, 255, 20))
        grad.setColorAt(1, QColor(255, 255, 255, 20))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)
        label_radius = radius * 0.95  # Carátula casi 100% del vinilo
        painter.save()
        painter.translate(center)
        painter.rotate(self.angle)
        if self._pixmap and not self._pixmap.isNull():
            diam = int(label_radius * 2)
            if self._cached_scaled is None or self._cached_diameter != diam:
                self._cached_scaled = self._pixmap.scaled(
                    diam,
                    diam,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._cached_diameter = diam
            clip_path = QPainterPath()
            clip_path.addEllipse(QPointF(0, 0), label_radius, label_radius)
            painter.setClipPath(clip_path)
            painter.drawPixmap(
                int(-label_radius), int(-label_radius), self._cached_scaled
            )
        else:
            painter.setBrush(QColor(40, 40, 40))
            painter.drawEllipse(QPointF(0, 0), label_radius, label_radius)
        painter.restore()


class PlayerWidget(QWidget):
    requestNext = Signal()

    def __init__(self, name="DECK"):
        super().__init__()
        self.name = name
        if _HAS_QTMULTIMEDIA:
            self.player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.player.setAudioOutput(self.audio_output)
            self._use_fallback = False
        elif _HAS_SOUNDDEVICE:
            self.player = DeckFallbackPlayer()
            self.audio_output = None
            self._use_fallback = True
        else:
            self.player = None
            self.audio_output = None
            self._use_fallback = True
        self.current_file = None
        self._setup_ui()
        self._setup_connections()

        # Timer para actualizar posición en fallback
        if self._use_fallback:
            self._pos_timer = QTimer(self)
            self._pos_timer.timeout.connect(self._update_fallback_state)
            self._pos_timer.start(100)

    def _update_fallback_state(self):
        if self._use_fallback and self.player:
            p = self.player.position()
            if not self.slider_progress.isSliderDown():
                self.slider_progress.setValue(p)
            d = self.player.duration()
            self.lbl_time.setText(f"{self._format_time(p)} / {self._format_time(d)}")
            # Actualizar spinning del vinilo y botón
            is_playing = self.player.isPlaying()
            self.vinyl.set_spinning(is_playing)
            self.btn_play.setText("⏸ PAUSE" if is_playing else "▶ PLAY")
            if is_playing:
                self.btn_play.setStyleSheet(
                    "font-weight: bold; background-color: #0078d4; color: white; border: 2px solid #005a9e; border-radius: 4px;"
                )
            else:
                self.btn_play.setStyleSheet(
                    "font-weight: bold; background-color: #222; color: white; border: 1px solid #444; border-radius: 4px;"
                )

    def setAudioDevice(self, device):
        if self._use_fallback or not self.audio_output:
            pass  # sounddevice usa el dispositivo por defecto
        elif device:
            # device puede ser dict (de AudioHardwareService.find_device_by_id) o QAudioDevice
            if isinstance(device, dict):
                if "device_obj" in device:
                    self.audio_output.setDevice(device["device_obj"])
            else:
                self.audio_output.setDevice(device)

    def setVolume(self, volume_01: float):
        if self._use_fallback and self.player:
            self.player._volume = volume_01
        elif self.audio_output:
            self.audio_output.setVolume(volume_01)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.lbl_deck = QLabel(self.name)
        self.lbl_deck.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_deck.setStyleSheet("font-weight: bold; color: cyan; font-size: 14px;")
        main_layout.addWidget(self.lbl_deck)

        # Centro: Vinilo y Volumen Vertical
        mid_layout = QHBoxLayout()

        self.vinyl = VinylWidget(size=180)
        mid_layout.addStretch()
        mid_layout.addWidget(self.vinyl)

        # Volumen Vertical
        vol_lay = QVBoxLayout()
        vol_lay.addWidget(QLabel("VOL"))
        self.slider_vol = QSlider(Qt.Orientation.Vertical)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.setMinimumHeight(120)
        vol_lay.addWidget(self.slider_vol, 1, Qt.AlignmentFlag.AlignCenter)
        mid_layout.addLayout(vol_lay)
        mid_layout.addStretch()

        main_layout.addLayout(mid_layout)

        self.lbl_info = QLabel("...")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(self.lbl_info)

        # Género - visible y grande
        self.lbl_genre = QLabel("")
        self.lbl_genre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_genre.setStyleSheet("""
            color: #00d4ff; font-weight: bold; font-size: 14px;
            background-color: #1a1a2e; padding: 4px 10px;
            border-radius: 4px; border: 1px solid #00d4ff;
        """)
        main_layout.addWidget(self.lbl_genre)

        ctrls = QHBoxLayout()
        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setMinimumHeight(45)
        self.btn_play.setStyleSheet("""
            QPushButton {
                font-weight: bold; background-color: #222; color: white;
                border: 1px solid #444; border-radius: 4px;
            }
            QPushButton:hover { background-color: #333; }
        """)
        ctrls.addWidget(self.btn_play, 1)
        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedSize(45, 45)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #222; color: white;
                border: 1px solid #444; border-radius: 4px;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        ctrls.addWidget(self.btn_stop)
        main_layout.addLayout(ctrls)

        prog_lay = QHBoxLayout()
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("font-family: monospace; font-size: 10px;")
        self.slider_progress = QSlider(Qt.Orientation.Horizontal)
        self.slider_progress.setRange(0, 100)
        prog_lay.addWidget(self.slider_progress)
        prog_lay.addWidget(self.lbl_time)
        main_layout.addLayout(prog_lay)

    def load_file(self, path: str, auto_play: bool = False):
        self.stop()
        self.current_file = path
        music_file = None
        if path and os.path.exists(path):
            if self.player:
                if self._use_fallback:
                    self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
                else:
                    self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            try:
                from core.reader.mp3_reader import MP3Reader

                reader = MP3Reader(path)
                music_file = reader.read(use_cache=True, save_db=False)
                if music_file and music_file.metadata:
                    self.vinyl.set_cover(music_file.metadata.cover_data)
                    self.lbl_info.setText(
                        f"{music_file.metadata.artist or 'Unknown'} - {music_file.metadata.title or os.path.basename(path)}"
                    )
                    # Mostrar género grande
                    genre = music_file.metadata.genre or ""
                    self.lbl_genre.setText(genre.upper() if genre else "")
                else:
                    self.vinyl.set_cover(None)
                    self.lbl_info.setText(os.path.basename(path))
                    self.lbl_genre.setText("")
            except Exception:
                self.vinyl.set_cover(None)
                self.lbl_info.setText(os.path.basename(path))
            if auto_play and self.player:
                self.player.play()
        else:
            self.vinyl.set_cover(None)
            self.lbl_info.setText("Error")
        return music_file

    def release(self):
        if self.player:
            self.player.stop()
            if hasattr(self.player, "setSource"):
                self.player.setSource(QUrl())

    def stop(self):
        if self.player:
            self.player.stop()
        self.slider_progress.setValue(0)
        self.vinyl.set_spinning(False)

    def _setup_connections(self):
        if self.player:
            if self._use_fallback:
                # Fallback player (sounddevice)
                self.btn_play.clicked.connect(
                    lambda: (
                        self.player.play()
                        if not self.player.isPlaying()
                        else self.player.pause()
                    )
                )
                self.btn_stop.clicked.connect(self.stop)
                self.slider_vol.valueChanged.connect(
                    lambda v: (
                        self.player.__setattr__("_volume", v / 100.0)
                        if self.player
                        else None
                    )
                )
                if hasattr(self.player, "positionChanged"):
                    self.player.positionChanged.connect(self._on_pos_changed)
                if hasattr(self.player, "durationChanged"):
                    self.player.durationChanged.connect(
                        lambda d: self.slider_progress.setRange(0, d)
                    )
                if hasattr(self.player, "playbackStateChanged"):
                    self.player.playbackStateChanged.connect(self._on_state_changed)
                self.slider_progress.sliderMoved.connect(
                    lambda p: self.player.setPosition(p) if self.player else None
                )
            else:
                # QMediaPlayer
                self.btn_play.clicked.connect(
                    lambda: (
                        self.player.play()
                        if self.player.playbackState()
                        != QMediaPlayer.PlaybackState.PlayingState
                        else self.player.pause()
                    )
                )
                self.btn_stop.clicked.connect(self.stop)
                self.slider_vol.valueChanged.connect(
                    lambda v: (
                        self.audio_output.setVolume(v / 100.0)
                        if self.audio_output
                        else None
                    )
                )
                self.player.positionChanged.connect(self._on_pos_changed)
                self.player.durationChanged.connect(
                    lambda d: self.slider_progress.setRange(0, d)
                )
                self.player.playbackStateChanged.connect(self._on_state_changed)
                self.slider_progress.sliderReleased.connect(
                    lambda: (
                        self.player.setPosition(self.slider_progress.value())
                        if self.player
                        else None
                    )
                )

    def _on_pos_changed(self, p):
        if not self.slider_progress.isSliderDown():
            self.slider_progress.setValue(p)
        if self.player:
            d = self.player.duration()
            self.lbl_time.setText(f"{self._format_time(p)} / {self._format_time(d)}")

    def _on_state_changed(self, state):
        if self._use_fallback:
            is_playing = state == 1
        else:
            is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.btn_play.setText("⏸ PAUSE" if is_playing else "▶ PLAY")

        if is_playing:
            self.btn_play.setStyleSheet("""
                QPushButton {
                    font-weight: bold; background-color: #0078d4; color: white;
                    border: 2px solid #005a9e; border-radius: 4px;
                }
            """)
        else:
            self.btn_play.setStyleSheet("""
                QPushButton {
                    font-weight: bold; background-color: #222; color: white;
                    border: 1px solid #444; border-radius: 4px;
                }
                QPushButton:hover { background-color: #333; }
            """)
        self.vinyl.set_spinning(is_playing)

    def _format_time(self, ms):
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"
