import logging

from core.formats.universal_reader import UniversalReader
from core.models import MusicFile

logger = logging.getLogger(__name__)


class MP3Reader:
    """
    MP3 reader - delegates to UniversalReader for compatibility.
    Kept for backward compatibility with existing code.
    """

    def __init__(self, filepath: str, db=None):
        self.filepath = filepath
        self.db = db
        self._universal = UniversalReader(filepath, db)

    def read(self, use_cache: bool = True, save_db: bool = True) -> MusicFile:
        return self._universal.read(use_cache=use_cache, save_db=save_db)

    @classmethod
    def _from_db_row(cls, row: dict) -> MusicFile:
        return UniversalReader._from_db_row(row)
