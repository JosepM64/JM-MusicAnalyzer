from contextlib import contextmanager
import logging
import os
import sqlite3

from utils.paths import normalize_path

logger = logging.getLogger(__name__)


class DatabaseConnection:
    def __init__(self, db_dir: str, db_path: str):
        self.db_dir = db_dir
        self.db_path = db_path
        self._ensure_db_exists()

    @contextmanager
    def _connection(self, row_factory=True):
        conn = sqlite3.connect(self.db_path)
        if row_factory:
            conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_db_exists(self):
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                filepath TEXT PRIMARY KEY,
                filename TEXT,
                filesize INTEGER,
                mtime REAL,
                sha256 TEXT,
                
                bitrate_header INTEGER,
                bitrate_real INTEGER,
                vbr INTEGER,
                sample_rate INTEGER,
                frecuencia_corte INTEGER,
                duration REAL,
                
                title TEXT,
                artist TEXT,
                album TEXT,
                genre TEXT,
                year TEXT,
                track_number TEXT,
                bpm INTEGER,
                isrc TEXT,
                rating INTEGER,
                comment TEXT,
                cover_data BLOB,
                cover_mime TEXT,
                
                last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            cursor.execute("ALTER TABLE tracks ADD COLUMN isrc TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tracks ADD COLUMN duration REAL")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tracks ADD COLUMN rating_new REAL")
            cursor.execute("UPDATE tracks SET rating_new = CAST(rating AS REAL)")
            cursor.execute("ALTER TABLE tracks DROP COLUMN rating")
            cursor.execute("ALTER TABLE tracks RENAME COLUMN rating_new TO rating")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tracks ADD COLUMN cover_data BLOB")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE tracks ADD COLUMN cover_mime TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sha256 ON tracks(sha256)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_genre ON tracks(genre)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_filepath ON tracks(filepath)")

        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA auto_vacuum=INCREMENTAL")

        self._migrate_normalize_paths()

        conn.commit()
        conn.close()

    def _migrate_normalize_paths(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(tracks)")
            columns = [row[1] for row in cursor.fetchall()]
            filepath_idx = columns.index("filepath")

            cursor.execute("SELECT * FROM tracks")
            all_rows = cursor.fetchall()

            if not all_rows:
                conn.close()
                return

            path_to_row = {}

            for row in all_rows:
                old_path = row[filepath_idx]
                new_path = normalize_path(old_path)

                if new_path not in path_to_row:
                    new_row = list(row)
                    new_row[filepath_idx] = new_path
                    path_to_row[new_path] = new_row

            if len(path_to_row) == len(all_rows):
                conn.close()
                return

            logger.info(
                f"Normalizando {len(all_rows)} paths, {len(all_rows) - len(path_to_row)} duplicados eliminados"
            )

            conn.execute("DELETE FROM tracks")

            for row in path_to_row.values():
                placeholders = ",".join(["?"] * len(columns))
                cursor.execute(
                    f"INSERT INTO tracks ({','.join(columns)}) VALUES ({placeholders})",
                    row,
                )

            conn.commit()
            conn.close()
            logger.info("Migración de paths completada")
        except Exception as e:
            logger.error(f"Error en migración de paths: {e}")
