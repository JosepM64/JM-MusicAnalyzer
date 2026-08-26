from services.db import get_db
from services.metadata_service import MetadataService
from services.settings_manager import SettingsManager


class AppState:
    def __init__(self):
        self.db = get_db()
        self.metadata_service = MetadataService()
        self.settings = SettingsManager()
        self.current_playlist_path = ""
        self.selected_filepath = ""
