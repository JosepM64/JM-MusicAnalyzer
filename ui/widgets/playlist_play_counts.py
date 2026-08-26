import json
import logging
import os

logger = logging.getLogger(__name__)


class PlayCountsManager:
    def __init__(self, play_counts_file):
        self._file = play_counts_file
        self._data = self._load()

    def _load(self):
        if os.path.exists(self._file):
            try:
                with open(self._file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save(self):
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self._data, f)
        except Exception:
            pass

    def get(self, path):
        return self._data.get(path, 0)

    def increment(self, path):
        self._data[path] = self._data.get(path, 0) + 1
        self.save()
        return self._data[path]

    def reset(self, path):
        self._data[path] = 0
        self.save()

    def reset_all(self):
        self._data = {}
        self.save()

    @property
    def data(self):
        return self._data
