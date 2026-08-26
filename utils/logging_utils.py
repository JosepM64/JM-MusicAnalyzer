from datetime import datetime
import logging
import os
import sys

from utils.version import get_app_version


def setup_logging(level=logging.INFO):
    """Configura el sistema de logging para la aplicación."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    if getattr(sys, "frozen", False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.getcwd()

    log_file = os.path.join(log_dir, "jm_music_analyzer.log")

    logging.Formatter.converter = lambda *args: datetime.now().timetuple()

    handlers = [logging.StreamHandler(sys.stdout)]

    if getattr(sys, "frozen", False):
        try:
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except OSError:
            pass

    logging.basicConfig(level=level, format=log_format, handlers=handlers, force=True)

    version = get_app_version()

    logger = logging.getLogger("Version")
    logger.info("========================================")
    logger.info(f"JM-MusicAnalyzer v{version}")
    logger.info(f"Python {sys.version}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info("========================================")

    logging.getLogger("PySide6").setLevel(logging.WARNING)


def get_logger(name):
    """Devuelve un logger con el nombre especificado."""
    return logging.getLogger(name)
