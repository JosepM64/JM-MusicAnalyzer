import json
import logging
import os

from services.app_paths import get_data_dir
from utils.paths import normalize_path

logger = logging.getLogger(__name__)


class BookmarksManager:
    """
    Gestiona los marcadores de carpetas favoritos del usuario.
    Cada bookmark es un dict: {"path": str, "recursive": bool}
    """

    def __init__(self):
        self.config_dir = get_data_dir()
        self.config_file = os.path.join(self.config_dir, "bookmarks.json")
        self._cache = None
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        if not os.path.exists(self.config_file):
            self.save_bookmarks([])

    def load_bookmarks(self) -> list:
        if self._cache is not None:
            return self._cache
        try:
            with open(self.config_file, encoding="utf-8") as f:
                data = json.load(f)
                if data and isinstance(data[0], str):
                    self._cache = [
                        {"path": normalize_path(p), "recursive": True} for p in data
                    ]
                else:
                    normalized = []
                    for b in data:
                        if isinstance(b, dict):
                            b["path"] = normalize_path(b.get("path", ""))
                            normalized.append(b)
                        else:
                            normalized.append(
                                {"path": normalize_path(b), "recursive": True}
                            )
                    self._cache = normalized
                return self._cache
        except Exception as e:
            logger.error(f"Error cargando marcadores: {e}")
            self._cache = []
            return self._cache

    def save_bookmarks(self, bookmarks: list):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(bookmarks, f, indent=4, ensure_ascii=False)
            self._cache = bookmarks
        except Exception as e:
            logger.error(f"Error guardando marcadores: {e}")

    def add_bookmark(self, path: str, recursive: bool = True):
        normalized_path = normalize_path(path)
        bookmarks = self.load_bookmarks()
        existing = [
            b for b in bookmarks if normalize_path(b.get("path", "")) == normalized_path
        ]
        if not existing:
            bookmarks.append({"path": normalized_path, "recursive": recursive})
            self.save_bookmarks(bookmarks)
            return True
        return False

    def remove_bookmark(self, path: str):
        normalized_path = normalize_path(path)
        bookmarks = self.load_bookmarks()
        bookmarks = [
            b for b in bookmarks if normalize_path(b.get("path", "")) != normalized_path
        ]
        self.save_bookmarks(bookmarks)
        return True

    def is_recursive(self, path: str) -> bool:
        normalized_path = normalize_path(path)
        bookmarks = self.load_bookmarks()
        for b in bookmarks:
            if normalize_path(b.get("path", "")) == normalized_path:
                return b.get("recursive", True)
        return True

    def set_recursive(self, path: str, recursive: bool):
        normalized_path = normalize_path(path)
        bookmarks = self.load_bookmarks()
        for b in bookmarks:
            if normalize_path(b.get("path", "")) == normalized_path:
                b["recursive"] = recursive
                self.save_bookmarks(bookmarks)
                return True
        return False

    def delete_nonexistent_folders(self) -> dict:
        """
        Elimina bookmarks/favoritos cuyas carpetas ya no existen en el disco.
        Retorna dict con {'deleted': int, 'removed': [str]}
        """
        result = {"deleted": 0, "removed": []}

        try:
            bookmarks = self.load_bookmarks()
            valid = []
            nonexistent = []

            for b in bookmarks:
                path = b.get("path", "") if isinstance(b, dict) else b
                if not os.path.exists(path):
                    nonexistent.append(path)
                else:
                    valid.append(b)

            if nonexistent:
                self.save_bookmarks(valid)
                result["deleted"] = len(nonexistent)
                result["removed"] = nonexistent
                logger.info(
                    f"Eliminados {len(nonexistent)} favoritos inexistentes del disco"
                )

        except Exception as e:
            logger.error(f"Error deleting nonexistent folders: {e}")

        return result
