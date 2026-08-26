import logging

from core.writer.tag_writer import TagWriter
from services.db import get_db

logger = logging.getLogger(__name__)


class MetadataService:
    def __init__(self):
        self.db = get_db()

    def save_field(self, filepath, release_player=None, **fields):
        if release_player:
            release_player()
        try:
            writer = TagWriter(filepath)
            if "rating" in fields and len(fields) == 1:
                writer.save_rating(fields["rating"])
            else:
                writer.save_all_metadata(fields)
        except Exception as e:
            logger.error(f"Error writing tags to {filepath}: {e}")
            raise
        self.db.update_track_metadata(filepath, **fields)
        return self.db.get_track(filepath)

    def save_from_panel(self, filepath, data, release_player=None):
        if release_player:
            release_player()
        try:
            writer = TagWriter(filepath)
            writer.save_all_metadata(data)
        except Exception as e:
            logger.error(f"Error writing tags to {filepath}: {e}")
            raise
        self.db.update_track_metadata(
            filepath,
            title=data.get("title"),
            artist=data.get("artist"),
            album=data.get("album"),
            genre=data.get("genre"),
            year=data.get("year"),
            track_number=data.get("track_number"),
            bpm=data.get("bpm"),
            rating=data.get("rating"),
            comment=data.get("comment"),
        )
        return self.db.get_track(filepath)

    def save_rating(self, filepath, rating, release_player=None):
        if release_player:
            release_player()
        try:
            writer = TagWriter(filepath)
            writer.save_rating(rating)
        except Exception as e:
            logger.error(f"Error writing rating to {filepath}: {e}")
            raise
        self.db.update_track_metadata(filepath, rating=rating)

    def batch_update_field(self, filepaths, **fields):
        for fp in filepaths:
            self.db.update_track_metadata(fp, **fields)
