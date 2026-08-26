import os


def normalize_path(path: str) -> str:
    """
    Normaliza un path para compatibilidad Windows x64.
    Convierte forward slashes a backslashes y resolve paths relativos.
    """
    if not path:
        return path
    normalized = path.replace("/", "\\")
    try:
        normalized = os.path.normpath(normalized)
    except Exception:
        pass
    normalized = normalized.replace("/", "\\")
    return normalized
