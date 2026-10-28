"""Textos de la barra de menú en els idiomes suportats (ES/CA).

Abast: només `_setup_menu_bar` de la finestra principal. S'aplica a l'arrencada;
canviar d'idioma requereix reiniciar (vegeu `SettingsDialog`).
"""

from services.settings_manager import SettingsManager

LANG_ES = "es"
LANG_CA = "ca"

_MENU = {
    # Menús
    "menu_file": {"es": "Archivo", "ca": "Arxiu"},
    "menu_edit": {"es": "Editar", "ca": "Edita"},
    "menu_view": {"es": "Ver", "ca": "Visualitza"},
    "menu_mode": {"es": "Modo", "ca": "Mode"},
    "menu_tools": {"es": "Eina", "ca": "Eina"},
    # Archivo
    "scan_folder": {"es": "Escanear Carpeta...", "ca": "Escaneja la carpeta..."},
    "quick_scan": {"es": "Escaneo Rapido", "ca": "Escaneig ràpid"},
    "exit": {"es": "Salir", "ca": "Surt"},
    # Editar
    "force_read": {"es": "Forzar Lectura Metadata", "ca": "Força la lectura de metadades"},
    "clear_db": {"es": "Limpiar Base de Datos", "ca": "Neteja la base de dades"},
    "optimize_db": {"es": "Optimizar Base de Datos", "ca": "Optimitza la base de dades"},
    "del_nonexist": {"es": "Eliminar Pistas Inexistentes", "ca": "Elimina les pistes inexistents"},
    "rebuild_db": {"es": "Reconstruir Base de Datos", "ca": "Reconstrueix la base de dades"},
    "backup_db": {"es": "Copia de Seguridad", "ca": "Còpia de seguretat"},
    "restore_db": {"es": "Restaurar Copia de Seguridad", "ca": "Restaura la còpia de seguretat"},
    # Ver
    "low_quality": {"es": "Pistas de Baja Calidad...", "ca": "Pistes de baixa qualitat..."},
    "corrupted": {"es": "Pistas Corruptas...", "ca": "Pistes malmeses..."},
    "duplicates": {"es": "Archivos Duplicados", "ca": "Fitxers duplicats"},
    "duplicates_fav": {"es": "Duplicados en Favoritos", "ca": "Duplicats als favorits"},
    # Modo / Eina
    "to_dj": {"es": "Cambiar a Modo DJ", "ca": "Canvia al mode DJ"},
    "import_yt": {"es": "📥 Importar de YouTube", "ca": "📥 Importa de YouTube"},
}


def get_language() -> str:
    try:
        lang = SettingsManager().get("language", LANG_ES)
    except Exception:
        return LANG_ES
    return lang if lang in (LANG_ES, LANG_CA) else LANG_ES


def menu_text(key: str) -> str:
    return _MENU.get(key, {}).get(get_language(), _MENU.get(key, {}).get(LANG_ES, key))
