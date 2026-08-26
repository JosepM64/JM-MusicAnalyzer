from .base import SUPPORTED_EXTENSIONS
from .universal_reader import UniversalReader


def get_reader_for_file(filepath):
    """Factory function - returns appropriate reader based on file extension."""
    from core.formats.universal_reader import UniversalReader

    return UniversalReader(filepath)
