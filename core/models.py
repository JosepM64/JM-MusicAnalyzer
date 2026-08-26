from dataclasses import dataclass, field
from typing import Any


@dataclass
class TechnicalInfo:
    bitrate: int  # kbps (del header)
    vbr: bool
    sample_rate: int  # Hz
    channels: int
    duration: float  # seconds
    file_size: int  # bytes
    id3_version: str = ""  # e.g., "2.3.0"
    encoding: str = ""  # e.g., "MPEG Layer 3"
    channel_mode: str = ""  # e.g., "Joint Stereo", "Stereo", "Mono"
    bitrate_real: int | None = None  # kbps (calculado por análisis espectral)
    frecuencia_corte: int | None = None  # Hz
    bitrate_match: bool = True  # True si header y real coinciden
    file_created: float | None = None  # timestamp creación archivo
    file_modified: float | None = None  # timestamp modificación archivo


@dataclass
class MetadataInfo:
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    genre: str | None = None
    year: str | None = None
    track_number: str | None = None
    bpm: int | None = None  # BPM en tags
    comment: str | None = None
    isrc: str | None = None
    rating_mixxx: int | None = None  # POPM (Mixxx/Windows)
    rating_mm: int | None = None  # TXXX (MediaMonkey)
    rating: int | None = None  # Rating unificado/manual
    cover_mime: str | None = None
    cover_data: bytes | None = None


@dataclass
class MusicFile:
    filepath: str
    technical: TechnicalInfo | None = None
    metadata: MetadataInfo | None = None
    raw_frames: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    sha256: str | None = None  # Hash para detectar duplicados reales


@dataclass
class ComparisonResult:
    technical_diffs: dict[str, tuple[Any, Any]]
    metadata_diffs: dict[str, tuple[str, str]]
    hash_equal: bool
    cover_equal: bool
    is_identical: bool = False
