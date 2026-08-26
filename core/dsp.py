import numpy as np
import soxr

from core.constants import LIMITER_THRESHOLD, RMS_SCALE, SOFT_CLIP_INTENSITY


def mono_to_stereo(audio_data: np.ndarray) -> np.ndarray:
    if audio_data.ndim == 1:
        return np.column_stack((audio_data, audio_data))
    return audio_data


def resample_audio(
    audio_data: np.ndarray, source_sr: int, target_sr: int
) -> np.ndarray:
    if source_sr == target_sr:
        return audio_data
    return soxr.resample(audio_data, source_sr, target_sr)


def pad_audio(block: np.ndarray, target_frames: int, channels: int = 2) -> np.ndarray:
    if len(block) < target_frames:
        padded = np.zeros((target_frames, channels), dtype=np.float32)
        padded[: len(block)] = block
        return padded
    return block[:target_frames]


def calculate_levels(block: np.ndarray) -> tuple:
    rms = np.sqrt(np.mean(block**2))
    current_level = min(rms * RMS_SCALE, 1.0)
    peak_level = np.max(np.abs(block))
    return current_level, peak_level


def apply_limiter(mix: np.ndarray, threshold: float = LIMITER_THRESHOLD) -> np.ndarray:
    over = mix - threshold
    over = np.where(over > 0, over, 0)
    ratio = 10.0
    mix = mix - (over / (1 + over * ratio))
    return mix


def soft_clip(
    mix: np.ndarray, intensity: float = SOFT_CLIP_INTENSITY, output_max: float = 0.95
) -> np.ndarray:
    mix = np.tanh(mix * intensity) * output_max
    return mix


def final_clip(mix: np.ndarray) -> np.ndarray:
    np.clip(mix, -1.0, 1.0, out=mix)
    return mix
