import logging
import os

from mutagen.id3 import ID3

try:
    from mutagen.id3._frames import (
        APIC,
        COMM,
        POPM,
        TALB,
        TBPM,
        TCON,
        TDRC,
        TIT2,
        TPE1,
        TRCK,
        TXXX,
    )
except ImportError:
    from mutagen.id3 import (
        APIC,
        COMM,
        POPM,
        TALB,
        TBPM,
        TCON,
        TDRC,
        TIT2,
        TPE1,
        TRCK,
        TXXX,
    )

logger = logging.getLogger(__name__)


class TagWriter:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def save_all_metadata(self, data: dict) -> bool:
        """Guarda todos los metadatos editados en el archivo."""
        try:
            if not os.path.exists(self.filepath):
                return False

            try:
                tags = ID3(self.filepath)
            except Exception:
                tags = ID3()

            # --- 1. Campos de Texto Estándar ---
            def set_text_frame(frame_class, key, current_tags):
                if key in data:
                    val = data[key]
                    if val is not None:
                        current_tags.delall(frame_class.__name__)
                        if str(val).strip():
                            current_tags.add(frame_class(encoding=3, text=[str(val)]))

            # --- 2. Rating (Sincronización Multi-formato) ---
            if "rating" in data:
                stars = data["rating"]
                stars = round(stars * 2) / 2

                val_255_table = {
                    0: 0,
                    0.5: 32,
                    1: 64,
                    1.5: 96,
                    2: 128,
                    2.5: 160,
                    3: 196,
                    3.5: 218,
                    4: 252,
                    4.5: 230,
                    5: 255,
                }
                val_255 = val_255_table.get(stars, 0)
                val_100 = int(stars * 20)

                tags.delall("POPM")
                tags.delall("TXXX:Rating")
                tags.delall("TXXX:MediaMonkey_Score")

                if stars > 0:
                    tags.add(POPM(email="no@email", rating=val_255))
                    tags.add(TXXX(desc="Rating", text=[str(val_255)]))
                    tags.add(TXXX(desc="MediaMonkey_Score", text=[str(val_100)]))

            # Aplicar campos de texto
            set_text_frame(TIT2, "title", tags)
            set_text_frame(TPE1, "artist", tags)
            set_text_frame(TALB, "album", tags)
            set_text_frame(TCON, "genre", tags)
            set_text_frame(TDRC, "year", tags)
            set_text_frame(TRCK, "track_number", tags)
            set_text_frame(TBPM, "bpm", tags)
            set_text_frame(COMM, "comment", tags)

            # --- 3. Campos personalizados (ISRC, etc.) ---
            isrc = data.get("isrc")
            if isrc:
                tags.delall("TXXX:ISRC")
                if str(isrc).strip():
                    tags.add(TXXX(desc="ISRC", text=[str(isrc)]))

            # --- 4. Carátula (APIC) ---
            cover_data = data.get("cover_data")
            if cover_data:
                # Borrar carátulas anteriores
                tags.delall("APIC")
                tags.add(
                    APIC(
                        encoding=3,  # UTF-8
                        mime="image/jpeg",  # Asumimos jpeg para portadas online
                        type=3,  # Portada frontal
                        desc="Front Cover",
                        data=cover_data,
                    )
                )

            # Guardar con ID3v2.3 para máxima compatibilidad
            tags.save(self.filepath, v2_version=3)
            return True
        except Exception as e:
            logger.error(f"Error guardando metadatos completos en {self.filepath}: {e}")
            return False

    def save_rating(self, stars: int) -> bool:
        return self.save_all_metadata({"rating": stars})
