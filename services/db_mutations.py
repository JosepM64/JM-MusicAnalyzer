import logging
import os
import sqlite3

from utils.paths import normalize_path

logger = logging.getLogger(__name__)


class DatabaseMutations:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _track_to_values(self, music_file) -> tuple:
        from core.models import MetadataInfo, TechnicalInfo

        tech = music_file.technical
        meta = music_file.metadata
        if not tech:
            tech = TechnicalInfo(
                bitrate=0, vbr=False, sample_rate=0, channels=0, duration=0, file_size=0
            )
        if not meta:
            meta = MetadataInfo(title="", artist="")
        normalized_filepath = normalize_path(music_file.filepath)
        try:
            mtime = os.path.getmtime(normalized_filepath)
        except OSError:
            mtime = 0
        return (
            normalized_filepath,
            os.path.basename(normalized_filepath),
            tech.file_size,
            mtime,
            getattr(music_file, "sha256", None),
            tech.bitrate,
            tech.bitrate_real,
            1 if tech.vbr else 0,
            tech.sample_rate,
            tech.frecuencia_corte,
            tech.duration,
            meta.title,
            meta.artist,
            meta.album,
            meta.genre,
            meta.year,
            meta.track_number,
            meta.bpm,
            meta.isrc,
            meta.rating,
            meta.comment,
            getattr(meta, "cover_data", None),
            getattr(meta, "cover_mime", None),
        )

    def save_track(self, music_file):
        values = self._track_to_values(music_file)
        if not values:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO tracks (
                    filepath, filename, filesize, mtime, sha256,
                    bitrate_header, bitrate_real, vbr, sample_rate, frecuencia_corte, duration,
                    title, artist, album, genre, year, track_number, bpm, isrc, rating, comment,
                    cover_data, cover_mime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                values,
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error guardando en DB: {e}")

    def bulk_save_tracks(self, music_files):
        if not music_files:
            return

        values = []
        for music_file in music_files:
            v = self._track_to_values(music_file)
            if v:
                values.append(v)

        if not values:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR REPLACE INTO tracks (
                    filepath, filename, filesize, mtime, sha256,
                    bitrate_header, bitrate_real, vbr, sample_rate, frecuencia_corte, duration,
                    title, artist, album, genre, year, track_number, bpm, isrc, rating, comment,
                    cover_data, cover_mime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                values,
            )
            conn.commit()
            conn.close()
            logger.info(f"Bulk save completed for {len(values)} tracks")
        except Exception as e:
            logger.error(f"Error en bulk save: {e}")
            logger.warning("Falling back to individual saves")
            for music_file in music_files:
                try:
                    self.save_track(music_file)
                except Exception as e2:
                    logger.error(f"Error saving track individually: {e2}")

    def update_track_metadata(
        self,
        filepath,
        title=None,
        artist=None,
        album=None,
        genre=None,
        year=None,
        track_number=None,
        bpm=None,
        rating=None,
        comment=None,
    ):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            updates = []
            params = []
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if artist is not None:
                updates.append("artist = ?")
                params.append(artist)
            if album is not None:
                updates.append("album = ?")
                params.append(album)
            if genre is not None:
                updates.append("genre = ?")
                params.append(genre)
            if year is not None:
                updates.append("year = ?")
                params.append(year)
            if track_number is not None:
                updates.append("track_number = ?")
                params.append(track_number)
            if bpm is not None:
                updates.append("bpm = ?")
                params.append(bpm)
            if rating is not None:
                updates.append("rating = ?")
                params.append(rating)
            if comment is not None:
                updates.append("comment = ?")
                params.append(comment)
            if not updates:
                return
            params.append(filepath)
            query = f"UPDATE tracks SET {', '.join(updates)} WHERE filepath = ?"
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            logger.debug(f"Metadatos actualizados para {filepath}")
        except Exception as e:
            logger.error(f"Error actualizando metadatos de {filepath}: {e}")

    def delete_track(self, filepath: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            normalized = normalize_path(filepath)
            cursor.execute("DELETE FROM tracks WHERE filepath = ?", (normalized,))
            conn.commit()
            conn.close()
            logger.info(f"Track eliminado: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error eliminando track: {e}")
            return False

    def clear_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tracks")
            cursor.execute("VACUUM")
            conn.commit()
            conn.close()
            logger.info("Base de datos limpiada y compactada")
            return True
        except Exception as e:
            logger.error(f"Error limpiando base de datos: {e}")
            return False

    def delete_nonexistent_tracks(self) -> dict:
        result = {"deleted": 0, "paths": []}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT filepath FROM tracks")
            all_paths = [row[0] for row in cursor.fetchall()]

            nonexistent = []
            for path in all_paths:
                if not os.path.exists(path):
                    nonexistent.append(path)

            if nonexistent:
                placeholders = ",".join(["?"] * len(nonexistent))
                cursor.execute(
                    f"DELETE FROM tracks WHERE filepath IN ({placeholders})",
                    nonexistent,
                )
                conn.commit()
                result["deleted"] = len(nonexistent)
                result["paths"] = nonexistent
                logger.info(
                    f"Eliminados {len(nonexistent)} tracks inexistentes del disco"
                )

            conn.close()

        except Exception as e:
            logger.error(f"Error deleting nonexistent tracks: {e}")

        return result
