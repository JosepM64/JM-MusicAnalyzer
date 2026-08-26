import logging
import os
import sys

logger = logging.getLogger(__name__)


def get_data_dir() -> str:
    """
    Devuelve el directorio de datos:
    - Si existe 'portable.txt' en la carpeta del exe: usa './data' (portable)
    - Si no: usa ~/.jm_music_analyzer/
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    portable_marker = os.path.join(exe_dir, "portable.txt")

    if os.path.exists(portable_marker):
        data_dir = os.path.join(exe_dir, "data")
        logger.info(f"Modo portable detectado. Usando: {data_dir}")
    else:
        data_dir = os.path.join(os.path.expanduser("~"), ".jm_music_analyzer")
        logger.info(f"Modo instalado detectado. Usando: {data_dir}")

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    return data_dir
