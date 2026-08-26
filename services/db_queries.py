import logging
import os
import sqlite3

from core.filter_criteria import FilterCriteria, TrackStatus
from utils.paths import normalize_path

logger = logging.getLogger(__name__)


class DatabaseQueries:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_all_tracks(self) -> list:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tracks")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all tracks: {e}")
            return []

    def get_cached_filepaths(self, filepaths: list, mtimes: dict = None) -> dict:
        if not filepaths:
            return {}
        result = {}
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            normalized_paths = [normalize_path(fp) for fp in filepaths]
            chunk_size = 500

            for i in range(0, len(normalized_paths), chunk_size):
                chunk = normalized_paths[i : i + chunk_size]
                placeholders = ",".join("?" * len(chunk))
                query = f"SELECT * FROM tracks WHERE filepath IN ({placeholders})"
                cursor.execute(query, chunk)
                rows = cursor.fetchall()
                for row in rows:
                    fp = row["filepath"]
                    db_mtime = row["mtime"]
                    if mtimes and fp in mtimes:
                        if db_mtime == mtimes[fp]:
                            result[fp] = dict(row)
                    elif os.path.exists(fp) and db_mtime == os.path.getmtime(fp):
                        result[fp] = dict(row)

            conn.close()
        except Exception as e:
            logger.error(f"Error getting cached filepaths: {e}")
        return result

    def get_track(self, filepath: str, mtime: float = None):
        normalized_filepath = normalize_path(filepath)
        if mtime is None:
            if not os.path.exists(normalized_filepath):
                return None
            current_mtime = os.path.getmtime(normalized_filepath)
        else:
            current_mtime = mtime

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM tracks WHERE filepath = ?", (normalized_filepath,)
        )
        row = cursor.fetchone()
        conn.close()

        if row and row["mtime"] == current_mtime:
            return dict(row)
        return None

    def get_unique_values(self, column_name: str) -> list:
        ALLOWED_COLUMNS = {
            "genre",
            "artist",
            "title",
            "album",
            "year",
            "rating",
            "status",
        }
        if column_name not in ALLOWED_COLUMNS:
            logger.error(f"Columna no permitida: {column_name}")
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT {column_name} FROM tracks WHERE {column_name} IS NOT NULL AND {column_name} != '' ORDER BY {column_name}"
            )
            rows = cursor.fetchall()
            conn.close()
            return [row[0] for row in rows if row[0]]
        except Exception as e:
            logger.error(f"Error obteniendo valores únicos de {column_name}: {e}")
            return []

    def get_unique_artists(self) -> list:
        return self.get_unique_values("artist")

    def get_unique_titles(self) -> list:
        return self.get_unique_values("title")

    def get_unique_genres(self) -> list:
        return self.get_unique_values("genre")

    def get_tracks_by_folder(self, folder_path: str, recursive: bool = True) -> list:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            norm_path = normalize_path(folder_path).lower()

            if recursive:
                if not norm_path.endswith("\\"):
                    norm_path += "\\"
                cursor.execute(
                    "SELECT * FROM tracks WHERE LOWER(filepath) LIKE ?",
                    (f"{norm_path}%",),
                )
            else:
                if not norm_path.endswith("\\"):
                    norm_path += "\\"
                cursor.execute(
                    "SELECT * FROM tracks WHERE LOWER(filepath) LIKE ? AND LOWER(filepath) NOT LIKE ? || '%' || '\\%'",
                    (f"{norm_path}%", norm_path),
                )

            rows = cursor.fetchall()
            tracks = [dict(row) for row in rows]
            conn.close()
            return tracks
        except Exception as e:
            logger.error(f"Error getting tracks by folder {folder_path}: {e}")
            return []

    def get_tracks_by_filepaths(self, filepaths: list) -> dict:
        if not filepaths:
            return {}

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            result = {}
            chunk_size = 500

            for i in range(0, len(filepaths), chunk_size):
                chunk = filepaths[i : i + chunk_size]
                placeholders = ",".join(["?"] * len(chunk))
                normalized_chunk = [normalize_path(p) for p in chunk]

                cursor.execute(
                    f"SELECT * FROM tracks WHERE filepath IN ({placeholders})",
                    normalized_chunk,
                )

                for row in cursor.fetchall():
                    track_data = dict(row)
                    result[track_data["filepath"]] = track_data

            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error getting tracks by filepaths: {e}")
            return {}

    def search_tracks_filtered(self, criteria: FilterCriteria = None, **kwargs) -> list:
        if criteria is None:
            criteria = FilterCriteria(
                genre=kwargs.get("genre"),
                min_rating=kwargs.get("rating") or 0.0,
                status=TrackStatus.NONE,
                search=kwargs.get("search"),
                folder=kwargs.get("folder"),
                limit=kwargs.get("limit", 500),
            )
            if kwargs.get("status") and kwargs["status"] != "Estado":
                criteria.status = TrackStatus.from_ui_string(kwargs["status"])
            if kwargs.get("genre") and kwargs["genre"] == "Género":
                criteria.genre = None

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            conditions = []
            params = []

            if criteria.genre is not None:
                if criteria.genre == "":
                    conditions.append("(genre IS NULL OR genre = '')")
                else:
                    conditions.append("genre = ?")
                    params.append(criteria.genre)

            if criteria.min_rating is not None and criteria.min_rating > 0:
                conditions.append("rating >= ?")
                params.append(criteria.min_rating)

            if getattr(criteria, "bpm_missing", False):
                conditions.append("(bpm IS NULL OR bpm = 0)")
            else:
                if getattr(criteria, "bpm_min", None) is not None:
                    conditions.append("bpm >= ?")
                    params.append(criteria.bpm_min)
                if getattr(criteria, "bpm_max", None) is not None:
                    conditions.append("bpm <= ?")
                    params.append(criteria.bpm_max)

            if criteria.status != TrackStatus.NONE:
                if criteria.status == TrackStatus.OK:
                    conditions.append(
                        "(bitrate_header IS NOT NULL AND bitrate_header > 0)"
                    )
                elif criteria.status == TrackStatus.UNKNOWN:
                    conditions.append("(bitrate_header IS NULL OR bitrate_header = 0)")
                elif criteria.status == TrackStatus.MODIFIED:
                    pass

            if criteria.search:
                conditions.append("(filename LIKE ? OR filepath LIKE ?)")
                params.extend([f"%{criteria.search}%", f"%{criteria.search}%"])

            if criteria.folder:
                folder_norm = normalize_path(criteria.folder).lower()
                if not folder_norm.endswith("\\"):
                    folder_norm += "\\"
                conditions.append("LOWER(filepath) LIKE ?")
                params.append(f"{folder_norm}%")

            query = "SELECT * FROM tracks"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += f" LIMIT {criteria.limit}"

            logger.info(f"SQL Query: {query}")
            logger.info(f"SQL Params: {params}")

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error en búsqueda filtrada: {e}")
            return []

    def get_unique_values_by_folder(
        self, folder_path: str, column_names: list = None
    ) -> dict:
        if column_names is None:
            column_names = ["genre", "artist", "title"]

        ALLOWED_COLUMNS = {
            "genre",
            "artist",
            "title",
            "album",
            "year",
            "rating",
            "status",
        }
        for col in column_names:
            if col not in ALLOWED_COLUMNS:
                logger.error(f"Columna no permitida: {col}")
                return {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            normalized_folder = normalize_path(folder_path)
            if not normalized_folder.endswith("\\"):
                normalized_folder += "\\"

            normalized_folder_lower = normalized_folder.lower()

            result = {}
            for column in column_names:
                query = f"""
                    SELECT DISTINCT {column} FROM tracks 
                    WHERE {column} IS NOT NULL AND {column} != '' 
                      AND LOWER(filepath) LIKE ? 
                    ORDER BY {column}
                """
                cursor.execute(query, (normalized_folder_lower + "%",))
                rows = cursor.fetchall()
                result[column] = [row[0] for row in rows if row[0]]

            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error obteniendo valores únicos por carpeta: {e}")
            return {col: [] for col in column_names}

    def find_duplicates(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT sha256, GROUP_CONCAT(filepath, '|') as paths, COUNT(*) as count 
                FROM tracks 
                WHERE sha256 IS NOT NULL
                GROUP BY sha256 HAVING count > 1
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            if conn:
                conn.close()

    def search_tracks(self, query: str, limit: int = 50) -> list:
        if not query or len(query.strip()) < 2:
            return []

        search_term = f"%{query.strip()}%"

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT filepath, filename, title, artist, album, genre, duration, rating
                FROM tracks 
                WHERE (title LIKE ? OR artist LIKE ?)
                ORDER BY 
                    CASE 
                        WHEN title LIKE ? THEN 1 
                        WHEN artist LIKE ? THEN 2 
                        ELSE 3 
                    END,
                    artist, title
                LIMIT ?
            """,
                (search_term, search_term, search_term, search_term, limit),
            )

            rows = cursor.fetchall()
            conn.close()
            results = []
            for row in rows:
                row_dict = dict(row)
                filepath = row_dict.get("filepath", "")
                row_dict["folder"] = os.path.dirname(normalize_path(filepath))
                results.append(row_dict)
            return results
        except Exception as e:
            logger.error(f"Error en search_tracks: {e}")
            return []

    def get_low_quality_tracks(self, min_bitrate: int = 64) -> list:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tracks 
                WHERE (bitrate_real < ? AND bitrate_real > 0) 
                OR duration < 10 
                OR duration IS NULL
                ORDER BY bitrate_real ASC
            """,
                (min_bitrate,),
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting low quality tracks: {e}")
            return []

    def get_corrupted_tracks(self) -> list:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tracks 
                WHERE duration <= 0 
                OR duration IS NULL
                ORDER BY filepath
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting corrupted tracks: {e}")
            return []

    def get_fake_tracks(self) -> list:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM tracks 
                WHERE bitrate_real > 0 AND bitrate_header > 0 AND bitrate_real < bitrate_header
                ORDER BY (bitrate_header - bitrate_real) DESC
            """)
            rows = cursor.fetchall()

            if not rows:
                cursor.execute("""
                    SELECT * FROM tracks 
                    WHERE bitrate_header >= 256 
                    AND duration > 30
                    AND filesize IS NOT NULL
                    AND (filesize * 8.0 / (duration * 1000.0)) < (bitrate_header * 0.7)
                    ORDER BY (bitrate_header * 0.7 - (filesize * 8.0 / (duration * 1000.0))) DESC
                """)
                rows = cursor.fetchall()

            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return []
