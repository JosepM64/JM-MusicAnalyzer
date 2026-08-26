import logging
import threading

from PySide6.QtCore import QObject, Signal

try:
    import sounddevice as sd
    import soundfile as sf

    _HAS_SOUNDDEVICE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("sounddevice no disponible")
    sd = None
    sf = None
    _HAS_SOUNDDEVICE = False

logger = logging.getLogger(__name__)


class CUEFallbackPlayer(QObject):
    """
    Audio player for CUE/preview output using sounddevice.
    Moved from ui/widgets/ to core/ for SoC separation.
    """

    positionChanged = Signal(int)
    playbackStateChanged = Signal(int)
    durationChanged = Signal(int)

    def __init__(self, device=None):
        super().__init__()
        self._stream = None
        self._data = None
        self._position = 0
        self._position_lock = threading.Lock()
        self._playing = False
        self._volume = 1.0
        self._samplerate = 44100
        self._duration = 0
        self._filename = None
        self._device = device

    def setSource(self, source):
        if not _HAS_SOUNDDEVICE:
            return
        if hasattr(source, "toLocalFile"):
            source = source.toLocalFile()
        self._filename = str(source)

        try:
            self._data, self._samplerate = sf.read(self._filename, dtype="float32")
            with self._position_lock:
                self._position = 0
            self._duration = len(self._data) / self._samplerate * 1000
            self.durationChanged.emit(self._duration)
            self._playing = False
        except Exception as e:
            logger.error(f"Error cargando {self._filename}: {e}")
            self._data = None

    def play(self):
        if not _HAS_SOUNDDEVICE or self._data is None:
            return
        self._playing = True
        self._start_stream()
        self.playbackStateChanged.emit(1)

    def pause(self):
        self._playing = False
        if self._stream:
            try:
                self._stream.stop()
            except Exception:
                pass
        self.playbackStateChanged.emit(0)

    def stop(self):
        self._playing = False
        with self._position_lock:
            self._position = 0
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            except Exception:
                self._stream = None
        self.playbackStateChanged.emit(0)

    def setPosition(self, position_ms):
        if self._data is not None:
            with self._position_lock:
                self._position = int(position_ms * self._samplerate / 1000)
                self._position = max(0, min(self._position, len(self._data)))

    def position(self):
        if self._data is None:
            return 0
        with self._position_lock:
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

    def setDevice(self, device):
        self._device = device

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

        playing = True

        def callback(outdata, frames, time_info, status):
            nonlocal playing
            if not playing:
                outdata.fill(0)
                return
            with self._position_lock:
                start = self._position
            end = start + frames
            if start >= len(self._data):
                outdata.fill(0)
                playing = False
                self._playing = False
                self.playbackStateChanged.emit(0)
                return
            if end > len(self._data):
                chunk = self._data[start:]
                outdata[: len(chunk)] = chunk * self._volume
                outdata[len(chunk) :].fill(0)
                with self._position_lock:
                    self._position = len(self._data)
                playing = False
                self._playing = False
                self.playbackStateChanged.emit(0)
            else:
                outdata[:] = self._data[start:end] * self._volume
                with self._position_lock:
                    self._position = end

        stream_kwargs = {
            "samplerate": self._samplerate,
            "channels": self._data.shape[1] if len(self._data.shape) > 1 else 2,
            "callback": callback,
            "blocksize": chunk_size,
        }

        if self._device is not None:
            logger.info(f"CUEFallbackPlayer: usando device={self._device}")
            stream_kwargs["device"] = self._device
        else:
            logger.info("CUEFallbackPlayer: sin device específico, usando default")

        self._stream = sd.OutputStream(**stream_kwargs)
        self._stream.start()
        logger.info(f"CUEFallbackPlayer: stream iniciado, device={self._device}")
