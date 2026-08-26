from services.database_manager import DatabaseManager

_instance = None


def get_db() -> DatabaseManager:
    global _instance
    if _instance is None:
        _instance = DatabaseManager()
    return _instance
