"""Anàlisi post-descàrrega d'àudio."""

from pathlib import Path

from mutagen.id3 import ID3
from mutagen.mp3 import MP3

BITRATE_EXCELLENT = 320
BITRATE_VERY_GOOD = 256
BITRATE_GOOD = 192
BITRATE_ACCEPTABLE = 128


def analyze_file(filepath):
    """Analitza un fitxer MP3 i retorna les metadades."""
    p = Path(filepath)
    if not p.exists():
        return None

    try:
        audio = MP3(filepath)
        tags = ID3(filepath) if p.suffix.lower() == ".mp3" else None

        result = {
            "filepath": filepath,
            "filename": p.name,
            "duration": round(audio.info.length, 2),
            "bitrate": audio.info.bitrate,
            "sample_rate": audio.info.sample_rate,
            "channels": audio.info.channels,
            "title": "",
            "artist": "",
            "album": "",
        }

        if tags:
            if tags.get("TIT2"):
                result["title"] = str(tags["TIT2"])
            if tags.get("TPE1"):
                result["artist"] = str(tags["TPE1"])
            if tags.get("TALB"):
                result["album"] = str(tags["TALB"])

        return result  # noqa: TRY300
    except Exception:  # noqa: BLE001
        return {
            "filepath": filepath,
            "filename": p.name,
            "duration": 0,
            "bitrate": 0,
            "sample_rate": 0,
            "channels": 0,
            "title": p.stem,
            "artist": "",
            "album": "",
        }


def get_quality_label(bitrate):
    """Retorna una etiqueta de qualitat basada en el bitrate."""
    if bitrate >= BITRATE_EXCELLENT:
        return "Excel·lent"
    if bitrate >= BITRATE_VERY_GOOD:
        return "Molt bona"
    if bitrate >= BITRATE_GOOD:
        return "Bona"
    if bitrate >= BITRATE_ACCEPTABLE:
        return "Acceptable"
    return "Baixa"
