import logging
import os
import threading

from PySide6.QtCore import QThread, Signal

from core.formats import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


class AnalyzeWorker(QThread):
    file_started = Signal(str, int)
    file_finished = Signal(object, int)
    all_finished = Signal()
    error = Signal(str)
    total_files = Signal(int)
    scan_progress = Signal(int, int)
    new_files_detected = Signal(list)  # list of dicts: title, artist, genre, filepath

    def __init__(self, paths: list, recursive: bool = True):
        super().__init__()
        self.paths = paths if isinstance(paths, list) else [paths]
        self.recursive = recursive
        self._files_to_process = []
        self._is_running = threading.Event()
        self._is_running.set()

    def _scan_paths(self):
        for p in self.paths:
            if not p:
                continue
            try:
                ext = os.path.splitext(p.lower())[1]
                if os.path.isfile(p) and ext in SUPPORTED_EXTENSIONS:
                    self._files_to_process.append(p)
                elif os.path.isdir(p):
                    if self.recursive:
                        for root, _, files in os.walk(p):
                            for f in files:
                                ext = os.path.splitext(f.lower())[1]
                                if ext in SUPPORTED_EXTENSIONS:
                                    self._files_to_process.append(os.path.join(root, f))
                    else:
                        for f in os.listdir(p):
                            full_path = os.path.join(p, f)
                            ext = os.path.splitext(f.lower())[1]
                            if (
                                os.path.isfile(full_path)
                                and ext in SUPPORTED_EXTENSIONS
                            ):
                                self._files_to_process.append(full_path)
            except PermissionError as e:
                logger.warning(f"Permiso denegado accediendo a {p}: {e}")
            except OSError as e:
                logger.warning(f"Error accediendo a {p}: {e}")

    def stop(self):
        self._is_running.clear()

    def run(self):
        self._scan_paths()

        if not self._files_to_process:
            self.all_finished.emit()
            return

        from core.models import MusicFile
        from core.reader.mp3_reader import MP3Reader
        from services.db import get_db
        from utils.paths import normalize_path

        db = get_db()
        total = len(self._files_to_process)

        # Obtenir tots els cached d'una sola vegada
        cached = db.get_cached_filepaths(self._files_to_process)
        all_cached = len(cached) == total
        logger.info(
            f"Scan: {total} files, {len(cached)} in cache, {total - len(cached)} to analyze"
        )

        if all_cached:
            # Tot en cache: saltem el per-file i acabem directe
            self.total_files.emit(total)
            self.scan_progress.emit(total, total)
            self.all_finished.emit()
            return

        processed = 0
        batch_to_save = []
        new_files = []

        for idx, filepath in enumerate(self._files_to_process):
            if not self._is_running.is_set():
                break

            try:
                normalized = normalize_path(filepath)
                if normalized in cached:
                    # Cached: només comptem, no fem signals per no bloquejar UI
                    pass
                else:
                    self.file_started.emit(filepath, processed)
                    reader = MP3Reader(filepath, db=db)
                    music_file = reader.read(use_cache=False, save_db=False)
                    folder = os.path.basename(os.path.dirname(filepath))
                    meta = music_file.metadata
                    if not music_file.error:
                        new_files.append(
                            {
                                "title": meta.title if meta else None,
                                "artist": meta.artist if meta else None,
                                "genre": meta.genre if meta else None,
                                "filepath": filepath,
                                "folder": folder,
                            }
                        )
                    if music_file.technical:
                        br = music_file.technical.bitrate or 0
                        br_real = music_file.technical.bitrate_real or 0
                        if br == 0:
                            logger.warning(
                                f"BITRATE ZERO: {filepath} - size={music_file.technical.file_size}, dur={music_file.technical.duration}"
                            )
                        elif br_real == 0:
                            logger.warning(
                                f"BITRATE_REAL ZERO: {filepath} - bitrate={br}"
                            )
                    if music_file.error:
                        logger.warning(f"READ ERROR: {filepath} - {music_file.error}")
                    batch_to_save.append(music_file)
                    self.file_finished.emit(music_file, processed)
            except Exception as e:
                logger.error(f"Error analizando {filepath}: {e}", exc_info=True)
                self.file_finished.emit(MusicFile(filepath, error=str(e)), processed)

            processed += 1
            if processed % 50 == 0 or processed == total:
                if batch_to_save:
                    try:
                        db.bulk_save_tracks(batch_to_save)
                    except Exception as e:
                        logger.error(f"Error en bulk save: {e}")
                    batch_to_save.clear()
                self.scan_progress.emit(processed, total)

        if batch_to_save:
            try:
                db.bulk_save_tracks(batch_to_save)
            except Exception as e:
                logger.error(f"Error en bulk save final: {e}")

        if new_files:
            self.new_files_detected.emit(new_files)

        self.all_finished.emit()
