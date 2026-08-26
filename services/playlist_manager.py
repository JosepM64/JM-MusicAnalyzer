import json
import logging
import os

from services.app_paths import get_data_dir

logger = logging.getLogger(__name__)


class PlaylistManager:
    """
    Gestiona la lectura y escritura de archivos de lista de reproducción M3U.
    También mantiene un registro de listas recientes y la última usada.
    """

    def __init__(self):
        self.data_dir = get_data_dir()
        self.history_file = os.path.join(self.data_dir, "playlist_history.json")
        self._history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error loading playlist history: {e}")
        return {"last_playlist": None, "recent": []}

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=4)
        except OSError as e:
            logger.error(f"Error saving playlist history: {e}")

    def get_last_playlist(self) -> str:
        return self._history.get("last_playlist")

    def get_recent_playlists(self) -> list:
        return self._history.get("recent", [])

    def record_playlist_usage(self, filepath: str):
        self._history["last_playlist"] = filepath
        if filepath not in self._history["recent"]:
            self._history["recent"].insert(0, filepath)
            self._history["recent"] = self._history["recent"][:10]  # Top 10
        else:
            # Mover al principio
            self._history["recent"].remove(filepath)
            self._history["recent"].insert(0, filepath)
        self._save_history()

    @staticmethod
    def read_m3u(filepath: str) -> list:
        if not filepath or not os.path.exists(filepath):
            return []

        base_dir = os.path.dirname(os.path.abspath(filepath))
        tracks = []

        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if not os.path.isabs(line):
                        full_path = os.path.normpath(os.path.join(base_dir, line))
                    else:
                        full_path = line
                    tracks.append(full_path)
            return tracks
        except Exception as e:
            logger.error(f"Error leyendo M3U: {e}")
            return []

    @staticmethod
    def save_m3u(filepath: str, tracks: list, relative: bool = True):
        base_dir = os.path.dirname(os.path.abspath(filepath))
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for track in tracks:
                    if not track:
                        continue
                    if relative:
                        try:
                            rel_path = os.path.relpath(track, base_dir)
                            f.write(f"#EXTINF:-1,\n{rel_path}\n")
                        except ValueError:
                            f.write(f"#EXTINF:-1,\n{track}\n")
                    else:
                        f.write(f"#EXTINF:-1,\n{track}\n")
            return True
        except Exception as e:
            logger.error(f"Error guardando M3U: {e}")
            return False
