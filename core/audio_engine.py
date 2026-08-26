import logging
import threading

import numpy as np

from core.constants import (
    PEAK_DECAY,
)
from core.dsp import (
    apply_limiter,
    calculate_levels,
    final_clip,
    mono_to_stereo,
    resample_audio,
    soft_clip,
)

logger = logging.getLogger(__name__)

# Import explícit per forçar PyInstaller a incloure sounddevice
try:
    import sounddevice as sd
    import soundfile as sf

    SOUNDDEVICE_AVAILABLE = True
except ImportError as e:
    sd = None
    sf = None
    SOUNDDEVICE_AVAILABLE = False
    logger.error(f"sounddevice NO disponible! Error: {e}")
    import sys

    logger.error(f"Python path: {sys.path}")


class MasterEngine:
    """
    Motor de audio master con limitador y soft clipping.
    Maneja la mezcla de múltiples decks y la salida de audio.
    """

    def __init__(self, samplerate=48000, blocksize=1024, channels=2):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.channels = channels

        # Ganancia master (1.0 = 0dB, hasta 2.0 = +6dB)
        self.master_gain = 1.0

        # Limitador
        self.limiter_threshold = 0.95  # -0.5dB de margen
        self.soft_clip = True
        self.soft_clip_intensity = 1.2

        # Dicionario de decks activos
        self.decks = {}
        self.deck_counter = 0

        # Estado
        self.is_running = False
        self.stream = None

        # Crossfader (-100 = solo A, +100 = solo B)
        self.crossfader = -100

        # Volúmenes individuales de decks
        self.deck_volumes = {}

    def start(self):
        """Inicia el stream de audio"""
        if self.is_running:
            return

        # Limpiar decks anteriores
        self.decks.clear()
        self.deck_volumes.clear()
        self.deck_counter = 0
        logger.info("[MasterEngine] start: decks cleared")

        if not SOUNDDEVICE_AVAILABLE:
            logger.error("sounddevice no disponible, motor de audio no iniciado")
            raise RuntimeError("sounddevice no disponible")

        try:
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                channels=self.channels,
                dtype="float32",
                callback=self._audio_callback,
            )
            self.stream.start()
            self.is_running = True
            logger.info(
                f"MasterEngine iniciado: {self.samplerate}Hz, blocksize={self.blocksize}"
            )
        except Exception as e:
            logger.error(f"Error al iniciar MasterEngine: {e}")
            raise

    def stop(self):
        """Detiene el stream de audio"""
        if not self.is_running:
            return

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self.is_running = False
        logger.info("MasterEngine detenido")

    def _audio_callback(self, outdata, frames, time_info, status):
        """Callback principal - llamado por sounddevice"""
        if status:
            logger.warning(f"Audio callback status: {status}")

        mix = np.zeros((frames, self.channels), dtype=np.float32)

        if not hasattr(self, "_callback_count"):
            self._callback_count = 0
        self._callback_count += 1
        if self._callback_count % 5000 == 0:
            logger.info(
                f"Callback #{self._callback_count}: master_gain={self.master_gain:.2f}, crossfader={self.crossfader}"
            )

        # Calcular factores de crossfader equal-power
        if 0 in self.decks and 1 in self.decks:
            x = (self.crossfader + 100) / 200.0
            cf_a = np.cos(x * np.pi / 2.0)
            cf_b = np.sin(x * np.pi / 2.0)
        else:
            cf_a = 1.0
            cf_b = 1.0

        # Recoger audio de decks activos aplicando volumen + crossfader
        for deck_id in list(self.decks.keys()):
            try:
                deck = self.decks[deck_id]
                if not getattr(deck, "is_playing", False) or not getattr(
                    deck, "is_loaded", False
                ):
                    continue

                deck_audio = deck.get_audio_block(frames)
                if deck_audio is not None and len(deck_audio) > 0:
                    if len(deck_audio) < frames:
                        padded = np.zeros((frames, self.channels), dtype=np.float32)
                        padded[: len(deck_audio)] = deck_audio
                        deck_audio = padded
                    elif len(deck_audio) > frames:
                        deck_audio = deck_audio[:frames]

                    # Volumen individual del deck
                    deck_vol = self.deck_volumes.get(deck_id, 1.0)
                    # Crossfader
                    cf_vol = cf_a if deck_id == 0 else cf_b
                    # Aplicar ambos
                    deck_audio *= deck_vol * cf_vol

                    mix += deck_audio
            except Exception as e:
                logger.error(f"Error procesando deck {deck_id}: {e}")

        # Aplicar ganancia master
        if self.master_gain != 1.0:
            mix *= self.master_gain

        mix = apply_limiter(mix, threshold=1.0)

        if self.soft_clip:
            mix = soft_clip(mix, self.soft_clip_intensity)

        mix = final_clip(mix)

        outdata[:] = mix

    def register_deck(self, deck):
        """Registra un deck en el motor"""
        deck_id = self.deck_counter
        self.deck_counter += 1
        self.decks[deck_id] = deck
        self.deck_volumes[deck_id] = 1.0
        logger.info(
            f"register_deck: deck_id={deck_id}, total decks={list(self.decks.keys())}"
        )
        logger.info(f"Deck {deck_id} registrado en MasterEngine")
        return deck_id

    def unregister_deck(self, deck_id):
        """Desregistra un deck del motor"""
        if deck_id in self.decks:
            del self.decks[deck_id]
        if deck_id in self.deck_volumes:
            del self.deck_volumes[deck_id]
        logger.info(f"Deck {deck_id} desregistrado")

    def set_master_gain(self, gain):
        """Ajusta la ganancia master (0.0 a 3.0)"""
        old_gain = self.master_gain
        self.master_gain = max(0.0, min(3.0, gain))
        logger.info(f"Master gain canviat: {old_gain:.2f} -> {self.master_gain:.2f}")

    def set_crossfader(self, value):
        """Ajusta el crossfader (-100 a +100)"""
        self.crossfader = max(-100, min(100, value))

    def set_deck_volume(self, deck_id, volume):
        """Ajusta el volumen de un deck específico"""
        self.deck_volumes[deck_id] = max(0.0, min(1.5, volume))


class Deck:
    """
    Reproductor de deck para el motor de audio.
    Lee archivos de audio y los envía al MasterEngine.
    """

    def __init__(self, master_engine, filepath=None):
        self.master = master_engine
        self.filepath = filepath
        self.deck_id = None

        # Estado
        self.is_loaded = False
        self.is_playing = False
        self.is_paused = False
        self._state_lock = threading.Lock()

        # Posición
        self.sample_position = 0
        self.samplerate = 48000
        self.channels = 2
        self.total_frames = 0

        # Audio
        self.audio_data = None
        self.gain = 1.0  # Ganancia individual (ReplayGain)

        # Nivel actual para VU meter
        self._current_level = 0.0
        self._peak_level = 0.0

        # Thread de reproducción
        self._play_thread = None
        self._stop_requested = False

        # Buffer para streaming
        self._buffer = []
        self._buffer_lock = threading.Lock()

        if filepath:
            self.load(filepath)

    def load(self, filepath):
        """Carga un archivo de audio"""
        try:
            if sf is None:
                logger.error("soundfile no disponible, no es pot carregar audio")
                return None
            # Leer todo el archivo en memoria (para archivos pequeños/medianos)
            self.audio_data, file_sr = sf.read(filepath, dtype="float32")

            self.audio_data = mono_to_stereo(self.audio_data)

            self.channels = self.audio_data.shape[1] if self.audio_data.ndim > 1 else 2
            self.samplerate = file_sr
            self.total_frames = len(self.audio_data)
            self.filepath = filepath

            # Buscar si deck ya está registrat al master
            registered_id = None
            if self.master:
                for dk_id, dk in list(self.master.decks.items()):
                    if dk is self:
                        registered_id = dk_id
                        break

            # Si ya estaba registrado, desregistrar primero
            if registered_id is not None and self.master and self.master.is_running:
                logger.info(f"Deck re-load: desregistrando deck_id={registered_id}")
                self.master.unregister_deck(registered_id)

            # RESAMPLE: si el sample rate no coincideix, resamplejar amb soxr
            if self.master and self.master.samplerate != file_sr:
                self.audio_data = resample_audio(
                    self.audio_data, file_sr, self.master.samplerate
                )
                self.samplerate = self.master.samplerate
                self.total_frames = len(self.audio_data)
                logger.info(f"Resample: {file_sr}Hz -> {self.master.samplerate}Hz")

            self.is_loaded = True
            self.sample_position = 0

            logger.info(
                f"Deck cargado: {filepath}, {self.total_frames} frames, {self.samplerate}Hz"
            )

            # Registrar en master
            if self.master and self.master.is_running:
                self.deck_id = self.master.register_deck(self)
                logger.info(
                    f"Registered with deck_id={self.deck_id}, total decks={list(self.master.decks.keys())}"
                )

            return True

        except Exception as e:
            logger.error(f"Error cargando archivo en deck: {e}")
            self.is_loaded = False
            return False

    def unload(self):
        """Descarga el archivo actual"""
        self.stop()
        self.audio_data = None
        self.is_loaded = False
        self.sample_position = 0

        if self.deck_id is not None and self.master:
            self.master.unregister_deck(self.deck_id)
            self.deck_id = None

    def play(self):
        """Inicia la reproducción"""
        if not self.is_loaded:
            return False

        with self._state_lock:
            if self.is_paused:
                self.is_paused = False
                self.is_playing = True
                return True

            if not self.is_playing:
                self._stop_requested = False
                self.is_playing = True

        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()
        return True

    def pause(self):
        """Pausa la reproducción"""
        with self._state_lock:
            self.is_playing = False
        self.is_paused = True

    def stop(self):
        """Detiene la reproducción"""
        self._stop_requested = True
        with self._state_lock:
            self.is_playing = False
            self.is_paused = False
            self.sample_position = 0
        self._current_level = 0.0

        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=1.0)

    def seek(self, position_samples):
        """Busca a una posición específica"""
        if not self.is_loaded:
            return
        with self._state_lock:
            self.sample_position = max(0, min(position_samples, self.total_frames - 1))

    def get_position(self):
        """Retorna la posición actual en samples"""
        with self._state_lock:
            return self.sample_position

    def get_duration_samples(self):
        """Retorna la duración en samples"""
        return self.total_frames

    def get_duration_seconds(self):
        """Retorna la duración en segundos"""
        return self.total_frames / self.samplerate if self.samplerate else 0

    def get_level(self):
        """Retorna el nivel actual de audio (0.0-1.0) para VU meter"""
        return self._current_level

    def get_peak(self):
        """Retorna el nivel pico de audio (0.0-1.0)"""
        return self._peak_level

    def reset_peak(self):
        """Resetea el nivel pico"""
        self._peak_level = 0.0

    def set_gain(self, gain_db):
        """Ajusta la ganancia en dB (para ReplayGain)"""
        self.gain = 10 ** (gain_db / 20)

    def _play_loop(self):
        pass

    def get_audio_block(self, frames):
        return None


class DeckBuffered(Deck):
    """
    Versión simplificada del deck - lectura directa sense thread.
    El callback de sounddevice llegeix directament de audio_data.
    """

    def __init__(self, master_engine, filepath=None):
        super().__init__(master_engine, filepath)
        self._buffer_lock = threading.Lock()
        self.playback_rate = 1.0  # 1.0 = velocidad normal

    def load(self, filepath):
        """Carga un archivo y resetea el playback rate."""
        if super().load(filepath):
            self.playback_rate = 1.0
            return True
        return False

    def set_rate(self, rate):
        """Ajusta la velocidad de reproducción (1.0 = normal)."""
        self.playback_rate = max(0.5, min(2.0, rate))

    def _play_loop(self):
        """Versió simplificada - no fa res ja que el callback llegeix directament"""

    def get_audio_block(self, frames):
        """Retorna un bloc d'àudio llegint directament de audio_data, aplicando playback_rate."""
        if not self.is_loaded or self.audio_data is None:
            return np.zeros((frames, 2), dtype=np.float32)

        with self._buffer_lock:
            total = self.total_frames
            if self.sample_position >= total:
                self.is_playing = False
                return np.zeros((frames, 2), dtype=np.float32)

            # Calcular cuántos samples del archivo leer según playback_rate
            read_frames = int(round(frames * self.playback_rate))
            if read_frames <= 0:
                read_frames = 1

            start = int(self.sample_position)
            end = min(start + read_frames, total)
            block = self.audio_data[start:end].copy()

            # Avanzar posición de lectura (samples de archivo consumidos)
            self.sample_position += end - start

            # Si no se leyó suficiente (fin de archivo), rellenar con zeros
            if len(block) < read_frames:
                pad_len = read_frames - len(block)
                block = np.pad(block, ((0, pad_len), (0, 0)), "constant")

            # Resamplear a 'frames' samples si es necesario
            if self.playback_rate != 1.0 and frames != read_frames:
                x_old = np.arange(read_frames)
                x_new = np.linspace(0, read_frames - 1, frames)
                resampled = np.zeros((frames, 2), dtype=np.float32)
                for ch in range(2):
                    resampled[:, ch] = np.interp(x_new, x_old, block[:, ch])
                block = resampled

            # Aplicar gain individual
            if self.gain != 1.0:
                block *= self.gain

            # Calcular nivell RMS per VU meter (sobre el block final)
            if len(block) > 0:
                self._current_level, peak = calculate_levels(block)
                self._peak_level = max(self._peak_level * PEAK_DECAY, peak)

            # Verificar fi de reproducció
            if self.sample_position >= total:
                self.is_playing = False

            return block
