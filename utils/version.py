import logging

logger = logging.getLogger(__name__)


def get_app_version() -> str:
    try:
        import JM_MusicAnalizer

        return getattr(JM_MusicAnalizer, "APP_VERSION", "unknown")
    except Exception:
        pass
    try:
        from app import APP_VERSION

        return APP_VERSION
    except ImportError:
        pass
    return "unknown"
