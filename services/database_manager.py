import os

from services.app_paths import get_data_dir
from services.db_connection import DatabaseConnection
from services.db_maintenance import DatabaseMaintenance
from services.db_mutations import DatabaseMutations
from services.db_queries import DatabaseQueries


class DatabaseManager:
    def __init__(self):
        self.db_dir = get_data_dir()
        self.db_path = os.path.join(self.db_dir, "library.db")
        self._connection_module = DatabaseConnection(self.db_dir, self.db_path)
        self._queries = DatabaseQueries(self.db_path)
        self._mutations = DatabaseMutations(self.db_path)
        self._maintenance = DatabaseMaintenance(self.db_dir, self.db_path)

    @property
    def _connection(self):
        return self._connection_module._connection

    def get_all_tracks(self) -> list:
        return self._queries.get_all_tracks()

    def get_cached_filepaths(self, filepaths: list, mtimes: dict = None) -> dict:
        return self._queries.get_cached_filepaths(filepaths, mtimes)

    def get_track(self, filepath: str, mtime: float = None):
        return self._queries.get_track(filepath, mtime)

    def get_unique_values(self, column_name: str) -> list:
        return self._queries.get_unique_values(column_name)

    def get_unique_artists(self) -> list:
        return self._queries.get_unique_artists()

    def get_unique_titles(self) -> list:
        return self._queries.get_unique_titles()

    def get_unique_genres(self) -> list:
        return self._queries.get_unique_genres()

    def get_tracks_by_folder(self, folder_path: str, recursive: bool = True) -> list:
        return self._queries.get_tracks_by_folder(folder_path, recursive)

    def get_tracks_by_filepaths(self, filepaths: list) -> dict:
        return self._queries.get_tracks_by_filepaths(filepaths)

    def search_tracks_filtered(self, criteria=None, **kwargs) -> list:
        return self._queries.search_tracks_filtered(criteria, **kwargs)

    def get_unique_values_by_folder(
        self, folder_path: str, column_names: list = None
    ) -> dict:
        return self._queries.get_unique_values_by_folder(folder_path, column_names)

    def find_duplicates(self):
        return self._queries.find_duplicates()

    def search_tracks(self, query: str, limit: int = 50) -> list:
        return self._queries.search_tracks(query, limit)

    def get_low_quality_tracks(self, min_bitrate: int = 64) -> list:
        return self._queries.get_low_quality_tracks(min_bitrate)

    def get_corrupted_tracks(self) -> list:
        return self._queries.get_corrupted_tracks()

    def get_fake_tracks(self) -> list:
        return self._queries.get_fake_tracks()

    def _track_to_values(self, music_file) -> tuple:
        return self._mutations._track_to_values(music_file)

    def save_track(self, music_file):
        return self._mutations.save_track(music_file)

    def bulk_save_tracks(self, music_files):
        return self._mutations.bulk_save_tracks(music_files)

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
        return self._mutations.update_track_metadata(
            filepath,
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            year=year,
            track_number=track_number,
            bpm=bpm,
            rating=rating,
            comment=comment,
        )

    def delete_track(self, filepath: str) -> bool:
        return self._mutations.delete_track(filepath)

    def clear_database(self):
        return self._mutations.clear_database()

    def delete_nonexistent_tracks(self) -> dict:
        return self._mutations.delete_nonexistent_tracks()

    def optimize_database(self) -> dict:
        return self._maintenance.optimize_database()

    def get_freelist_count(self) -> int:
        return self._maintenance.get_freelist_count()

    def get_db_size(self) -> int:
        return self._maintenance.get_db_size()

    def auto_optimize_if_needed(self, scan_count: int = 0) -> dict:
        return self._maintenance.auto_optimize_if_needed(scan_count)

    def export_tracks_to_txt(self, tracks: list, filepath: str) -> bool:
        return self._maintenance.export_tracks_to_txt(tracks, filepath)

    def get_database_stats(self) -> dict:
        return self._maintenance.get_database_stats()

    def backup_database(self, backup_dir: str = None) -> dict:
        return self._maintenance.backup_database(backup_dir)

    def get_backups(self, backup_dir: str = None) -> list:
        return self._maintenance.get_backups(backup_dir)

    def restore_database(self, backup_path: str) -> bool:
        return self._maintenance.restore_database(backup_path)

    def rebuild_database(self) -> dict:
        return self._maintenance.rebuild_database()
