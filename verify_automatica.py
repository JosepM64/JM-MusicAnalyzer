#!/usr/bin/env python3
"""
Verificación Automatizada - JM-MusicAnalyzer
=============================================
Proyecto: JM-MusicAnalyzer (Analitzador de música + DJ mode)
Versión: 1.0

Ejecutar: python verify_automatica.py
"""

import ast
import os
import sys

PROJECT_NAME = "JM-MusicAnalyzer"
PROJECT_VERSION = "4.43.0"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = SCRIPT_DIR


class VerificationResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def add_pass(self, test_name, details=""):
        self.passed += 1
        self.results.append(("PASS", test_name, details))

    def add_fail(self, test_name, details=""):
        self.failed += 1
        self.results.append(("FAIL", test_name, details))

    def add_warning(self, test_name, details=""):
        self.warnings += 1
        self.results.append(("WARN", test_name, details))

    def print_summary(self):
        print("\n" + "=" * 60)
        print(f"RESUMEN DE VERIFICACION - {PROJECT_NAME} v{PROJECT_VERSION}")
        print("=" * 60)
        print(f"[OK] PASADOS:   {self.passed}")
        print(f"[X] FALLADOS:  {self.failed}")
        print(f"[!] AVISOS:    {self.warnings}")
        print("=" * 60)

        if self.failed > 0:
            print("\nFALLOS DETECTADOS:")
            for status, test, details in self.results:
                if status == "FAIL":
                    print(f"  [{status}] {test}")
                    if details:
                        print(f"         {details}")

        return self.failed == 0


def read_file(filepath):
    if not os.path.isabs(filepath):
        filepath = os.path.join(PROJECT_DIR, filepath)
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def check_syntax(filepath):
    """Verifica que un fitxer Python tingui sintaxi correcta"""
    full = filepath if os.path.isabs(filepath) else os.path.join(PROJECT_DIR, filepath)
    try:
        with open(full, encoding="utf-8", errors="ignore") as f:
            source = f.read()
        ast.parse(source, filename=filepath)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def verify_project_structure(result: VerificationResult):
    """Verifica estructura del projecte"""
    print("\n[1/10] Estructura del Projecte...")

    os.chdir(PROJECT_DIR)

    key_files = [
        "main.py",
        "app.py",
        "app_state.py",
        "JM_MusicAnalizer/__init__.py",
    ]

    for f in key_files:
        if os.path.exists(f):
            result.add_pass("Estructura", f)
        else:
            result.add_fail("Estructura", f"no encontrado: {f}")

    key_dirs = [
        "core",
        "services",
        "ui",
        "ui/widgets",
        "ui/dialogs",
        "workers",
        "utils",
    ]

    for d in key_dirs:
        if os.path.isdir(os.path.join(PROJECT_DIR, d)):
            result.add_pass("Estructura", f"directorio {d}/")
        else:
            result.add_fail("Estructura", f"directorio no encontrado: {d}/")


def verify_main_entry(result: VerificationResult):
    """Verifica punt d'entrada"""
    print("[2/10] Punto de Entrada...")

    if os.path.exists("main.py"):
        content = read_file("main.py")

        checks = [
            ("QApplication", "QApplication"),
            ("sys.excepthook", "Manejador excepciones"),
            ("multiprocessing", "Multiprocessing freeze support"),
            ("sys.argv", "sys.argv"),
        ]

        for pattern, desc in checks:
            if pattern in content:
                result.add_pass("Main", desc)
            else:
                result.add_warning("Main", f"{desc} no encontrado")
    else:
        result.add_fail("Main", "main.py no encontrado")

    if os.path.exists("app.py"):
        content = read_file("app.py")
        if "class MusicAnalyzerApp" in content:
            result.add_pass("Main", "MusicAnalyzerApp class")
        else:
            result.add_fail("Main", "MusicAnalyzerApp class no encontrada")

        if "APP_VERSION" in content:
            result.add_pass("Main", "APP_VERSION definit")
        else:
            result.add_warning("Main", "APP_VERSION no trobat a app.py")
    else:
        result.add_fail("Main", "app.py no encontrado")

    if os.path.exists("app_state.py"):
        content = read_file("app_state.py")
        if "class AppState" in content:
            result.add_pass("Main", "AppState class")
        else:
            result.add_fail("Main", "AppState class no encontrada")
    else:
        result.add_fail("Main", "app_state.py no encontrado")


def verify_version_consistency(result: VerificationResult):
    """Verifica que la versió estigui consistent"""
    print("[3/10] Consistencia de Versió...")

    version_file = "JM_MusicAnalizer/__init__.py"
    if os.path.exists(version_file):
        content = read_file(version_file)
        if 'APP_VERSION = "4.' in content:
            result.add_pass("Version", f"Version source of truth: {content.strip()}")
        else:
            result.add_warning("Version", "APP_VERSION no trobat o format inesperat")
    else:
        result.add_fail("Version", "JM_MusicAnalizer/__init__.py no encontrado")


def verify_core_modules(result: VerificationResult):
    """Verifica mòduls core"""
    print("[4/10] Modulos Core...")

    core_files = {
        "core/audio_engine.py": [
            "class MasterEngine",
            "class Deck",
            "class DeckBuffered",
        ],
        "core/models.py": [
            "class TechnicalInfo",
            "class MetadataInfo",
            "class MusicFile",
        ],
        "core/filter_criteria.py": ["class TrackStatus", "class FilterCriteria"],
        "core/cue_player.py": ["class CUEFallbackPlayer"],
    }

    for filepath, expected_classes in core_files.items():
        if os.path.exists(filepath):
            content = read_file(filepath)
            for cls in expected_classes:
                if cls in content:
                    result.add_pass("Core", f"{filepath}: {cls}")
                else:
                    result.add_fail("Core", f"{filepath}: {cls} no encontrado")
        else:
            result.add_fail("Core", f"archivo no encontrado: {filepath}")

    # Formats
    formats_files = {
        "core/formats/universal_reader.py": ["class UniversalReader"],
        "core/formats/base.py": ["class AudioReader"],
    }

    for filepath, expected_classes in formats_files.items():
        if os.path.exists(filepath):
            content = read_file(filepath)
            for cls in expected_classes:
                if cls in content:
                    result.add_pass("Core", f"{filepath}: {cls}")
                else:
                    result.add_fail("Core", f"{filepath}: {cls} no encontrado")
        else:
            result.add_fail("Core", f"archivo no encontrado: {filepath}")

    # Writer
    writer_files = {
        "core/writer/tag_writer.py": ["class TagWriter"],
    }

    for filepath, expected_classes in writer_files.items():
        if os.path.exists(filepath):
            content = read_file(filepath)
            for cls in expected_classes:
                if cls in content:
                    result.add_pass("Core", f"{filepath}: {cls}")
                else:
                    result.add_fail("Core", f"{filepath}: {cls} no encontrado")
        else:
            result.add_fail("Core", f"archivo no encontrado: {filepath}")


def verify_services(result: VerificationResult):
    """Verifica serveis"""
    print("[5/10] Serveis...")

    service_files = {
        "services/database_manager.py": ["class DatabaseManager"],
        "services/metadata_service.py": ["class MetadataService"],
        "services/settings_manager.py": ["class SettingsManager"],
        "services/bookmarks_manager.py": ["class BookmarksManager"],
        "services/cover_art_service.py": ["class CoverArtService"],
        "services/audio_hardware_service.py": ["class AudioHardwareService"],
        "services/playlist_manager.py": ["class PlaylistManager"],
        "services/online_metadata_service.py": [
            "class MusicBrainzProvider",
            "class OnlineMetadataService",
        ],
    }

    for filepath, expected_classes in service_files.items():
        if os.path.exists(filepath):
            content = read_file(filepath)
            for cls in expected_classes:
                if cls in content:
                    result.add_pass("Services", f"{filepath}: {cls}")
                else:
                    result.add_fail("Services", f"{filepath}: {cls} no encontrado")
        else:
            result.add_fail("Services", f"archivo no encontrado: {filepath}")

    # DB module
    if os.path.exists("services/db.py"):
        content = read_file("services/db.py")
        if "sqlite" in content.lower() or "database" in content.lower():
            result.add_pass("Services", "db.py: database module")
        else:
            result.add_warning("Services", "db.py: contingut no esperat")
    else:
        result.add_fail("Services", "services/db.py no encontrado")


def verify_ui_main_windows(result: VerificationResult):
    """Verifica finestres principals UI"""
    print("[6/10] Finestres Principals UI...")

    # MainWindow (Manager mode)
    if os.path.exists("ui/main_window.py"):
        content = read_file("ui/main_window.py")
        if "class MainWindow" in content:
            result.add_pass("UI", "MainWindow class")
        else:
            result.add_fail("UI", "MainWindow class no encontrada")

        key_methods = [
            "def _setup_ui",
            "def _setup_menu",
            "def _on_scan",
            "def _on_open_folder",
        ]

        for method in key_methods:
            if method in content:
                result.add_pass("UI", f"MainWindow: {method}")
            else:
                result.add_warning("UI", f"MainWindow: {method} no encontrado")
    else:
        result.add_fail("UI", "ui/main_window.py no encontrado")

    # PerformanceWindow (DJ mode)
    if os.path.exists("ui/performance_window.py"):
        content = read_file("ui/performance_window.py")
        if "class PerformanceWindow" in content:
            result.add_pass("UI", "PerformanceWindow class")
        else:
            result.add_fail("UI", "PerformanceWindow class no encontrada")

        key_methods = [
            "def _setup_ui",
            "def _init_decks",
            "def _handle_transition_logic",
        ]

        for method in key_methods:
            if method in content:
                result.add_pass("UI", f"PerformanceWindow: {method}")
            else:
                result.add_warning("UI", f"PerformanceWindow: {method} no encontrado")
    else:
        result.add_fail("UI", "ui/performance_window.py no encontrado")


def verify_ui_widgets(result: VerificationResult):
    """Verifica widgets UI"""
    print("[7/10] Widgets UI...")

    widget_files = {
        "ui/widgets/audio_engine_player.py": [
            "class AudioEnginePlayerWidget",
        ],
        "ui/widgets/deck_vinyl.py": ["class VinylWidget"],
        "ui/widgets/playlist_widget.py": ["class PlaylistWidget"],
        "ui/widgets/player_widget.py": [
            "class PlayerWidget",
            "class DeckFallbackPlayer",
        ],
        "ui/widgets/simple_player_widget.py": [
            "class SimplePlayerWidget",
            "class SounddevicePlayer",
        ],
        "ui/widgets/cover_widget.py": ["class CoverWidget"],
        "ui/widgets/file_list_widget.py": [
            "class FileListWidget",
        ],
        "ui/widgets/file_list_data.py": ["class NumericTableWidgetItem"],
        "ui/widgets/file_tree_widget.py": ["class FileTreeWidget"],
        "ui/widgets/rating_widget.py": ["class RatingWidget"],
        "ui/widgets/vu_meter.py": ["class StereoVuMeter"],
        "ui/widgets/row_preview_player.py": ["class RowPreviewPlayer"],
    }

    for filepath, expected_classes in widget_files.items():
        if os.path.exists(filepath):
            content = read_file(filepath)
            for cls in expected_classes:
                if cls in content:
                    result.add_pass("Widgets", f"{cls}")
                else:
                    result.add_fail("Widgets", f"{filepath}: {cls} no encontrado")
        else:
            result.add_fail("Widgets", f"archivo no encontrado: {filepath}")


def verify_ui_dialogs(result: VerificationResult):
    """Verifica diàlegs"""
    print("[8/10] Dialogs...")

    dialog_files = {
        "ui/dialogs/about_dialog.py": ["class AboutDialog"],
        "ui/dialogs/audio_config_dialog.py": ["class AudioConfigDialog"],
        "ui/dialogs/duplicate_dialog.py": ["class DuplicateDialog"],
        "ui/dialogs/favorites_manager_dialog.py": ["class FavoritesManagerDialog"],
        "ui/dialogs/metadata_comparison_dialog.py": ["class MetadataComparisonDialog"],
        "ui/dialogs/quick_scan_dialog.py": ["class QuickScanDialog"],
        "ui/dialogs/settings_dialog.py": ["class SettingsDialog"],
        "ui/dialogs/tracks_inspector_dialog.py": ["class TracksInspectorDialog"],
        "ui/dialogs/track_edit_dialog.py": ["class TrackEditDialog"],
    }

    for filepath, expected_classes in dialog_files.items():
        if os.path.exists(filepath):
            content = read_file(filepath)
            for cls in expected_classes:
                if cls in content:
                    result.add_pass("Dialogs", f"{cls}")
                else:
                    result.add_fail("Dialogs", f"{filepath}: {cls} no encontrado")
        else:
            result.add_fail("Dialogs", f"archivo no encontrado: {filepath}")


def verify_ui_panels(result: VerificationResult):
    """Verifica panells UI"""
    print("[9/11] Panells UI...")

    panel_files = {
        "ui/metadata_panel.py": ["class MetadataPanel"],
        "ui/technical_panel.py": ["class TechnicalPanel"],
    }

    for filepath, expected_classes in panel_files.items():
        if os.path.exists(filepath):
            content = read_file(filepath)
            for cls in expected_classes:
                if cls in content:
                    result.add_pass("Panels", f"{cls}")
                else:
                    result.add_fail("Panels", f"{filepath}: {cls} no encontrado")
        else:
            result.add_fail("Panels", f"archivo no encontrado: {filepath}")


def verify_ytdl_plugin(result: VerificationResult):
    """Verifica el plugin yt_dl (YouTube)"""
    print("[10/11] Plugin yt_dl...")

    plugin_dir = os.path.join(PROJECT_DIR, "plugins", "yt_dl")
    required_files = ["__init__.py", "main.py", "downloader.py", "analyzer.py", "plugin.json"]

    if not os.path.isdir(plugin_dir):
        result.add_fail("yt_dl", "directorio plugins/yt_dl/ no encontrado")
        return

    for f in required_files:
        fp = os.path.join(plugin_dir, f)
        if os.path.isfile(fp):
            result.add_pass("yt_dl", f)
        else:
            result.add_fail("yt_dl", f"falta: {f}")

    required_keys = {"name": "yt_dl", "version": "1.0.0"}
    if os.path.isfile(os.path.join(plugin_dir, "plugin.json")):
        try:
            import json
            with open(os.path.join(plugin_dir, "plugin.json"), encoding="utf-8") as pf:
                cfg = json.load(pf)
            for key, expected in required_keys.items():
                if cfg.get(key) == expected:
                    result.add_pass("yt_dl", f"plugin.json[{key}]")
                else:
                    result.add_fail("yt_dl", f"plugin.json[{key}] esperat={expected} obtingut={cfg.get(key)}")
            if "actions" in cfg and isinstance(cfg["actions"], list) and len(cfg["actions"]) > 0:
                result.add_pass("yt_dl", "plugin.json[actions]")
            else:
                result.add_fail("yt_dl", "plugin.json[actions] buit o absent")
        except Exception as e:
            result.add_fail("yt_dl", f"plugin.json error: {e}")


def verify_syntax_all(result: VerificationResult):
    """Verifica sintaxi de tots els fitxers Python del projecte"""
    print("[11/11] Verificació de Sintaxi...")

    excluded_dirs = {
        "dist",
        "build",
        "__pycache__",
        ".ruff_cache",
        ".opencode",
        "backups",
    }
    excluded_files = {"nul"}

    count = 0
    errors = 0

    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        rel_root = os.path.relpath(root, PROJECT_DIR)
        if any(part in excluded_dirs for part in rel_root.split(os.sep)):
            continue

        for fname in sorted(files):
            if not fname.endswith(".py") or fname in excluded_files:
                continue

            rel_path = os.path.relpath(os.path.join(root, fname), PROJECT_DIR)
            ok, err = check_syntax(rel_path)
            count += 1
            if ok:
                result.add_pass("Syntax", rel_path)
            else:
                result.add_fail("Syntax", f"{rel_path}: {err}")
                errors += 1

    print(f"  Verificats: {count} fitxers, {errors} errors de sintaxi")


def main():
    print("=" * 60)
    print(f"{PROJECT_NAME} - Verificacion Automatizada")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Directorio proyecto: {PROJECT_DIR}")

    os.chdir(PROJECT_DIR)

    result = VerificationResult()

    verify_project_structure(result)
    verify_main_entry(result)
    verify_version_consistency(result)
    verify_core_modules(result)
    verify_services(result)
    verify_ui_main_windows(result)
    verify_ui_widgets(result)
    verify_ui_dialogs(result)
    verify_ui_panels(result)
    verify_ytdl_plugin(result)
    verify_syntax_all(result)

    success = result.print_summary()

    if success:
        print("\n[OK] TODAS LAS VERIFICACIONES PASARON")
        print("El proyecto esta listo para continuar.")
        return 0
    print("\n[X] ALGUNAS VERIFICACIONES FALLARON")
    print("Revisa los fallos antes de continuar.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
