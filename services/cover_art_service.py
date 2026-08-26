import logging
import os

logger = logging.getLogger(__name__)


class CoverArtService:
    """
    Fase D (v4.3.0) - Servei centralitzat per a la gestió de carátules (cover art).

    Responsabilitats:
    - Extreure cover art d'un fitxer de música
    - Guardar cover art a disc com a imatge
    - Extreure cover art dels metadates (MetadataInfo)

    Abans aquesta lògica estava dispersa entre MainWindow i CoverWidget.
    """

    @staticmethod
    def extract_from_file(filepath: str) -> tuple[bytes, str] | None:
        """
        Extreu cover art d'un fitxer d'àudio.
        Retorna (cover_data, mime_type) o None si no n'hi ha.
        """
        if not filepath or not os.path.exists(filepath):
            return None
        try:
            from core.reader.mp3_reader import MP3Reader

            reader = MP3Reader(filepath)
            music_file = reader.read(use_cache=True, save_db=False)
            if music_file and music_file.metadata and music_file.metadata.cover_data:
                mime = music_file.metadata.cover_mime or "image/jpeg"
                return music_file.metadata.cover_data, mime
        except Exception as e:
            logger.error(f"Error extraient cover de {filepath}: {e}")
        return None

    @staticmethod
    def save_to_file(cover_data: bytes, dest_path: str) -> bool:
        """
        Guarda les dades de cover art a un fitxer d'imatge.
        Retorna True si s'ha guardat correctament.
        """
        if not cover_data:
            return False
        try:
            with open(dest_path, "wb") as f:
                f.write(cover_data)
            logger.info(f"Cover art guardat a: {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Error guardant cover art: {e}")
            return False

    @staticmethod
    def detect_image_format(data: bytes) -> str:
        """
        Detecta el format d'imatge pels bytes inicials.
        Retorna 'jpg', 'png', o 'unknown'.
        """
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if data[:2] == b"\xff\xd8":
            return "jpg"
        return "unknown"
