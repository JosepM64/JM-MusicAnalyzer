import json
import logging
import os
import time
import weakref

from utils.paths import normalize_path

logger = logging.getLogger(__name__)


class PlayCountsManager:
    _shared = {}

    @classmethod
    def shared(cls, play_counts_file):
        mgr = cls._shared.get(play_counts_file)
        if mgr is None:
            mgr = cls(play_counts_file)
            cls._shared[play_counts_file] = mgr
        return mgr

    def __init__(self, play_counts_file):
        self._file = play_counts_file
        self._data = self._load()
        self._session = {}
        self._listeners = weakref.WeakSet()

    @staticmethod
    def _key(path):
        try:
            return normalize_path(path).lower()
        except Exception:
            return path

    def _load(self):
        data = {}
        if os.path.exists(self._file):
            try:
                with open(self._file, encoding="utf-8") as f:
                    raw = json.load(f)
                for k, v in raw.items():
                    try:
                        n = int(v)
                    except Exception:
                        continue
                    nk = self._key(k)
                    data[nk] = data.get(nk, 0) + n
            except Exception:
                pass
        return data

    def save(self):
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self._data, f)
        except Exception:
            pass

    def get(self, path):
        return self._data.get(self._key(path), 0)

    def increment(self, path):
        if not path:
            return 0
        k = self._key(path)
        self._data[k] = self._data.get(k, 0) + 1
        self.save()
        entry = self._session.get(k)
        if entry is None:
            self._session[k] = {"path": path, "count": 1, "first": time.time()}
        else:
            entry["count"] += 1
        self._notify(path)
        return self._data[k]

    def reset(self, path):
        if not path:
            return
        self._data[self._key(path)] = 0
        self.save()
        self._notify(path)

    def reset_all(self):
        self._data = {}
        self._session = {}
        self.save()
        self._notify(None)

    def session_tracks(self):
        return sorted(self._session.values(), key=lambda e: e["first"])

    def add_listener(self, widget):
        try:
            self._listeners.add(widget)
        except Exception:
            pass

    def _notify(self, path):
        for w in list(self._listeners):
            try:
                refresh = getattr(w, "_refresh_play_count_in_table", None)
                if refresh is not None:
                    refresh(path)
            except Exception:
                pass

    @property
    def data(self):
        return self._data
