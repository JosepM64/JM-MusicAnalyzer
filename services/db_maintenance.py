import logging
import os
import sqlite3

logger = logging.getLogger(__name__)


class DatabaseMaintenance:
    def __init__(self, db_dir: str, db_path: str):
        self.db_dir = db_dir
        self.db_path = db_path

    def optimize_database(self) -> dict:
        result = {"success": False, "freed_mb": 0.0, "size_mb": 0.0}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
            )
            size_before = cursor.fetchone()[0]

            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            cursor.execute("PRAGMA incremental_vacuum")
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")

            cursor.execute(
                "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
            )
            size_after = cursor.fetchone()[0]

            conn.commit()
            conn.close()

            freed_mb = (size_before - size_after) / (1024 * 1024)
            size_mb = size_after / (1024 * 1024)
            logger.info(f"Base de datos optimizada: {freed_mb:.2f} MB liberados")
            result = {
                "success": True,
                "freed_mb": round(freed_mb, 2),
                "size_mb": round(size_mb, 2),
            }
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
        return result

    def get_freelist_count(self) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA freelist_count")
            free_pages = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            conn.close()
            return free_pages * page_size
        except Exception as e:
            logger.error(f"Error getting freelist count: {e}")
            return 0

    def get_db_size(self) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
            )
            size = cursor.fetchone()[0]
            conn.close()
            return size
        except Exception as e:
            logger.error(f"Error getting db size: {e}")
            return 0

    def auto_optimize_if_needed(self, scan_count: int = 0) -> dict:
        result = {"optimized": False, "reason": "", "freed_mb": 0.0}

        try:
            db_size = self.get_db_size()
            free_size = self.get_freelist_count()

            if db_size == 0:
                return result

            free_pct = (free_size / db_size) * 100

            if free_pct > 20:
                logger.info(
                    f"Auto-optimizing: {free_pct:.1f}% espacio libre ({free_size / (1024 * 1024):.1f} MB)"
                )
                opt = self.optimize_database()
                if opt["success"]:
                    result["optimized"] = True
                    result["reason"] = f"{free_pct:.1f}% espacio libre detectado"
                    result["freed_mb"] = opt["freed_mb"]
                return result

            if scan_count > 0 and scan_count % 5 == 0:
                logger.info(f"Auto-optimizing: escaneo #{scan_count}")
                opt = self.optimize_database()
                if opt["success"]:
                    result["optimized"] = True
                    result["reason"] = f"Escaneo #{scan_count} (cada 5)"
                    result["freed_mb"] = opt["freed_mb"]
                return result

            logger.debug(
                f"Auto-optimize skipped: {free_pct:.1f}% free, scan #{scan_count}"
            )

        except Exception as e:
            logger.error(f"Error in auto_optimize_if_needed: {e}")

        return result

    def export_tracks_to_txt(self, tracks: list, filepath: str) -> bool:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("JM-MusicAnalyzer - Informe de Pistas\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Total de pistas: {len(tracks)}\n\n")

                for i, t in enumerate(tracks, 1):
                    f.write(f"{i}. {os.path.basename(t.get('filepath', 'Unknown'))}\n")
                    f.write(f"   Ruta: {t.get('filepath', '')}\n")
                    f.write(f"   Título: {t.get('title', 'Unknown')}\n")
                    f.write(f"   Artista: {t.get('artist', 'Unknown')}\n")
                    f.write(f"   Álbum: {t.get('album', 'Unknown')}\n")
                    f.write(f"   Género: {t.get('genre', 'Unknown')}\n")
                    f.write(f"   Duración: {t.get('duration', 0)}s\n")
                    f.write(f"   Bitrate: {t.get('bitrate_real', 'Unknown')} kbps\n")
                    f.write(
                        f"   Tamaño: {t.get('filesize', 0) / (1024 * 1024):.2f} MB\n"
                    )
                    f.write("\n")

            logger.info(f"Exportado {len(tracks)} pistas a {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting tracks: {e}")
            return False

    def get_database_stats(self) -> dict:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM tracks")
            total = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM tracks WHERE bitrate_real < 128 AND bitrate_real > 0"
            )
            low_quality = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM tracks WHERE duration < 1 OR duration IS NULL"
            )
            corrupted = cursor.fetchone()[0]

            cursor.execute(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            )
            size_bytes = cursor.fetchone()[0]

            cursor.execute("PRAGMA freelist_count")
            free_pages = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            free_bytes = free_pages * page_size

            conn.close()
            return {
                "total_tracks": total,
                "low_quality": low_quality,
                "corrupted": corrupted,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "free_mb": round(free_bytes / (1024 * 1024), 2),
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    def backup_database(self, backup_dir: str = None) -> dict:
        from datetime import datetime
        import shutil

        result = {"path": "", "size_mb": 0.0}
        try:
            if backup_dir is None:
                backup_dir = os.path.join(self.db_dir, "backups")
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"library_{timestamp}.db")

            if not os.path.exists(self.db_path):
                logger.warning("No existe la base de datos, no se puede hacer backup")
                return result

            shutil.copy2(self.db_path, backup_path)

            wal_path = self.db_path + "-wal"
            if os.path.exists(wal_path):
                shutil.copy2(wal_path, backup_path + "-wal")

            shm_path = self.db_path + "-shm"
            if os.path.exists(shm_path):
                shutil.copy2(shm_path, backup_path + "-shm")

            backup_size = os.path.getsize(backup_path) / (1024 * 1024)
            result["path"] = backup_path
            result["size_mb"] = round(backup_size, 2)
            logger.info(f"Backup creado: {backup_path} ({backup_size:.2f} MB)")
        except Exception as e:
            logger.error(f"Error haciendo backup: {e}")
            result["error"] = str(e)
        return result

    def get_backups(self, backup_dir: str = None) -> list:
        if backup_dir is None:
            backup_dir = os.path.join(self.db_dir, "backups")
        if not os.path.exists(backup_dir):
            return []

        backups = []
        try:
            for f in sorted(os.listdir(backup_dir), reverse=True):
                if f.startswith("library_") and f.endswith(".db"):
                    path = os.path.join(backup_dir, f)
                    size_mb = os.path.getsize(path) / (1024 * 1024)
                    date_str = f.replace("library_", "").replace(".db", "")
                    backups.append(
                        {
                            "path": path,
                            "filename": f,
                            "size_mb": round(size_mb, 2),
                            "date": date_str,
                        }
                    )
        except Exception as e:
            logger.error(f"Error listando backups: {e}")
        return backups

    def restore_database(self, backup_path: str) -> bool:
        import shutil

        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup no encontrado: {backup_path}")
                return False

            if not os.path.exists(self.db_path):
                pass
            else:
                for ext in ["", "-wal", "-shm"]:
                    p = self.db_path + ext
                    if os.path.exists(p):
                        os.remove(p)

            shutil.copy2(backup_path, self.db_path)

            wal_backup = backup_path + "-wal"
            if os.path.exists(wal_backup):
                shutil.copy2(wal_backup, self.db_path + "-wal")

            shm_backup = backup_path + "-shm"
            if os.path.exists(shm_backup):
                shutil.copy2(shm_backup, self.db_path + "-shm")

            logger.info(f"BD restaurada desde: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error restaurando backup: {e}")
            return False

    def rebuild_database(self) -> dict:
        from core.reader.mp3_reader import MP3Reader

        result = {"rebuilt": 0, "total": 0, "errors": []}
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT filepath FROM tracks 
                WHERE title IS NULL OR title = '' 
                OR artist IS NULL OR artist = ''
                OR duration IS NULL OR duration = 0
                OR bitrate_header IS NULL OR bitrate_header = 0
            """)
            incomplete = [row["filepath"] for row in cursor.fetchall()]
            conn.close()

            if not incomplete:
                logger.info("Rebuild: no hay pistas con datos incompletos")
                return result

            result["total"] = len(incomplete)
            logger.info(f"Rebuild: {len(incomplete)} pistas con datos incompletos")

            for filepath in incomplete:
                if not os.path.exists(filepath):
                    continue
                try:
                    reader = MP3Reader(filepath)
                    music_file = reader.read(use_cache=False, save_db=True)
                    if music_file:
                        result["rebuilt"] += 1
                except Exception as e:
                    result["errors"].append(f"{os.path.basename(filepath)}: {e}")
                    logger.debug(f"Rebuild error en {filepath}: {e}")

            logger.info(
                f"Rebuild completado: {result['rebuilt']}/{result['total']} reconstruidas"
            )
        except Exception as e:
            logger.error(f"Error en rebuild: {e}")
            result["errors"].append(str(e))
        return result
