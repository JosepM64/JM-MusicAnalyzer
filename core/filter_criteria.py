from dataclasses import dataclass
from enum import Enum


class TrackStatus(Enum):
    NONE = "none"
    OK = "ok"
    UNKNOWN = "unknown"
    MODIFIED = "modified"

    @classmethod
    def from_ui_string(cls, value: str) -> "TrackStatus":
        mapping = {
            "Estado": cls.NONE,
            "✓ OK": cls.OK,
            "? Desconocido": cls.UNKNOWN,
            "✎ Modificado": cls.MODIFIED,
        }
        return mapping.get(value, cls.NONE)


@dataclass
class FilterCriteria:
    genre: str | None = None
    min_rating: float = 0.0
    status: TrackStatus = TrackStatus.NONE
    search: str | None = None
    folder: str | None = None
    limit: int = 500
    bpm_min: int | None = None
    bpm_max: int | None = None
    bpm_missing: bool = False
