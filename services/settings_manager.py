import json
import logging
import os
import threading

from services.app_paths import get_data_dir

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Gestiona la configuración persistente de la aplicación.
    """

    def __init__(self):
        self.settings_path = os.path.join(get_data_dir(), "settings.json")
        self._dirty = False
        self._flush_timer = None
        self.settings = self._load()

    def _load(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error loading settings: {e}")
        return {
            "master_device_id": "",
            "cue_device_id": "",
            "default_playlist_dir": "",
            "last_window_size": [1200, 850],
        }

    def save(self):
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            self._dirty = False
        except OSError as e:
            logger.error(f"Error saving settings: {e}")

    def _schedule_flush(self):
        if self._flush_timer is not None:
            self._flush_timer.cancel()
        self._flush_timer = threading.Timer(1.0, self.save)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self._schedule_flush()

    def get_recent_move_paths(self, limit=10):
        return self.settings.get("recent_move_paths", [])

    def add_recent_move_path(self, path, limit=10):
        recent = self.get_recent_move_paths(limit)
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        if len(recent) > limit:
            recent = recent[:limit]
        self.settings["recent_move_paths"] = recent
        self._schedule_flush()

    def flush(self):
        if self._dirty:
            self.save()
