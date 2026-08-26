from abc import ABC, abstractmethod
import logging
import os

from core.models import MusicFile

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".ogg",
    ".ogv",
    ".oga",
    ".m4a",
    ".aac",
    ".mp4",
    ".wav",
    ".wave",
    ".aiff",
    ".aif",
    ".ape",
    ".tak",
    ".wv",
    ".wvp",
    ".dsf",
    ".dsdiff",
    ".dff",
    ".opus",
    ".spx",
    ".tta",
    ".m4b",
    ".m4r",
    ".m4p",
    ".3gp",
    ".3g2",
    ".motag",
    ".adts",
}


class AudioReader(ABC):
    """Abstract base class for audio file readers."""

    def __init__(self, filepath: str, db=None):
        self.filepath = filepath
        self.db = db

    @abstractmethod
    def read(self, use_cache: bool = True, save_db: bool = True) -> MusicFile:
        """Read audio file and return MusicFile with metadata and technical info."""

    def _get_file_size(self) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(self.filepath)
        except OSError:
            return 0

    def _get_file_times(self):
        """Get file creation and modification times."""
        try:
            return os.path.getctime(self.filepath), os.path.getmtime(self.filepath)
        except OSError:
            return None, None

    @staticmethod
    def is_supported(filepath: str) -> bool:
        """Check if file extension is supported."""
        ext = os.path.splitext(filepath.lower())[1]
        return ext in SUPPORTED_EXTENSIONS
