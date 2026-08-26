import logging
import multiprocessing
import os
import sys

# Netejar PATH: eliminar entrades de Qt d'altres apps (JMComander)
if not getattr(sys, "frozen", False):
    _path_clean = [
        p for p in os.environ.get("PATH", "").split(";") if "JMComander" not in p
    ]
    os.environ["PATH"] = ";".join(_path_clean)

# Add DLL directories for PySide6 on Windows
if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    conda_env = os.path.dirname(sys.executable)
    dll_dirs = [
        os.path.join(conda_env, "Lib", "site-packages", "PySide6"),
        os.path.join(conda_env, "Lib", "site-packages", "shiboken6"),
    ]
    for d in dll_dirs:
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass

# Forçar raster backend per evitar problemes de renderitzat
os.environ["QT_QPA_PLATFORM"] = "windows"

# Forzar library paths de Qt antes de crear QApplication
from PySide6.QtCore import QCoreApplication

if getattr(sys, "frozen", False):
    plugin_path = os.path.join(sys._MEIPASS, "PySide6", "plugins")
    QCoreApplication.setLibraryPaths([plugin_path])
else:
    pass
    # En mode desenvolupament (conda-forge), els plugins són a Library/lib/qt6/plugins
    # No sobreescriure libraryPaths – Qt ja troba els plugins automàticament

# Garantizar que shiboken6 se incluya en la compilación
try:
    import shiboken6
except ImportError:
    pass

# Solución para DLLs de Qt en entornos Conda
if getattr(sys, "frozen", False):
    # Si estamos en el ejecutable, añadir la carpeta de plugins
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
        sys._MEIPASS, "PySide6", "plugins"
    )
else:
    # Solución para rutas con espacios y acentos en modo desarrollo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

from app import MusicAnalyzerApp
from utils.logging_utils import setup_logging


def main():
    # Soporte para multiprocessing en aplicaciones congeladas (PyInstaller)
    multiprocessing.freeze_support()

    # Setup logging
    setup_logging(level=logging.DEBUG)
    logger = logging.getLogger("Main")
    logger.info("Starting JM-MusicAnalyzer...")

    # Start Application
    app = MusicAnalyzerApp(sys.argv)
    ret = app.exec()
    sys.exit(ret)


if __name__ == "__main__":
    main()
