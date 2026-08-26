# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks.qt import pyside6_library_info
import os
import glob as glob_mod

# Recolectar todo (datas, binaries, hidden) de los paquetes principales
datas_ui, binaries_ui, hidden_ui = collect_all('ui')
datas_core, binaries_core, hidden_core = collect_all('core')
datas_services, binaries_services, hidden_services = collect_all('services')
datas_utils, binaries_utils, hidden_utils = collect_all('utils')
datas_req, binaries_req, hidden_req = collect_all('requests')
datas_acoustid, binaries_acoustid, hidden_acoustid = collect_all('acoustid')
datas_mb, binaries_mb, hidden_mb = collect_all('musicbrainzngs')
datas_sd, binaries_sd, hidden_sd = collect_all('sounddevice')
datas_sf, binaries_sf, hidden_sf = collect_all('soundfile')
datas_mutagen, binaries_mutagen, hidden_mutagen = collect_all('mutagen')
datas_plugins, binaries_plugins, hidden_plugins = collect_all('plugins')
datas_ytdlp, binaries_ytdlp, hidden_ytdlp = collect_all('yt_dlp')
datas_soxr, binaries_soxr, hidden_soxr = collect_all('soxr')

# Collect specific conda Qt/PySide6 DLLs that PyInstaller's hook may miss
# BinariesPath = .../Library/lib/qt6/bin -> ../../.. = .../Library -> bin = .../Library/bin
conda_prefix = os.path.normpath(os.path.join(pyside6_library_info.location['BinariesPath'], '..', '..', '..'))
conda_lib_bin = os.path.join(conda_prefix, 'bin')
qt_binaries = []
for dll_pattern in ['Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'Qt6Network.dll',
                     'shiboken6*.dll', 'pyside6*.dll', 'double-conversion.dll',
                     'jpeg8.dll', 'tiff.dll', 'libwebp*.dll']:
    for dll_path in glob_mod.glob(os.path.join(conda_lib_bin, dll_pattern)):
        dll_name = os.path.basename(dll_path)
        qt_binaries.append((dll_path, '.'))

# Asegurar módulos específicos de widgets
extra_hidden = [
    'ui.widgets.playlist_widget',
    'ui.widgets.playlist_automix',
    'ui.widgets.playlist_cue',
    'ui.widgets.playlist_context_menu',
    'ui.widgets.playlist_file_io',
    'ui.widgets.playlist_filters',
    'ui.widgets.playlist_source_loaders',
    'ui.widgets.playlist_table_ops',
    'ui.widgets.playlist_track_ops',
    'ui.widgets.playlist_sorting',
    'ui.widgets.playlist_play_counts',
    'ui.widgets.audio_engine_player',
    'ui.widgets.deck_vinyl',
    'ui.widgets.deck_controls',
    'ui.widgets.deck_bpm',
    'ui.widgets.player_widget',
    'ui.widgets.cover_widget',
    'ui.widgets.row_preview_player',
    'ui.widgets.file_list_widget',
    'ui.widgets.file_list_columns',
    'ui.widgets.file_list_actions',
    'ui.widgets.file_list_data',
    'ui.main_window_menu',
    'ui.main_window_scan',
    'ui.main_window_metadata',
    'ui.perf_window_ui',
    'ui.perf_window_transition',
    'ui.perf_window_decks',
    'ui.perf_window_crossfader',
    'ui.perf_window_bpm',
    'services.db_connection',
    'services.db_queries',
    'services.db_mutations',
    'services.db_maintenance',
    'plugins.yt_dl.main',
    'ui.dialogs.tracks_inspector_dialog',
    'requests',
    'acoustid',
]
hidden_all = list(set(hidden_ui + hidden_core + hidden_services + hidden_utils + hidden_req + hidden_acoustid + hidden_mb + hidden_sd + hidden_sf + hidden_mutagen + hidden_plugins + hidden_ytdlp + hidden_soxr + extra_hidden))

# Combinar datas y binaries (Qt DLLs from conda env first to take priority)
all_datas = datas_ui + datas_core + datas_services + datas_utils + datas_req + datas_acoustid + datas_mb + datas_sd + datas_sf + datas_mutagen + datas_plugins + datas_ytdlp + datas_soxr
all_binaries = qt_binaries + binaries_ui + binaries_core + binaries_services + binaries_utils + binaries_req + binaries_acoustid + binaries_mb + binaries_sd + binaries_sf + binaries_mutagen + binaries_plugins + binaries_ytdlp + binaries_soxr
# Filtrar DLLs MKL de numpy (570 MB innecesarios - no usamos BLAS/MKL)
mkl_patterns = ['mkl_', 'libmkl_']
all_binaries = [(src, dst) for src, dst in all_binaries
                if not any(p in os.path.basename(src).lower() for p in mkl_patterns)]

# ffmpeg (essentials) i fpcalc viuen a tools/ del projecte -> bundling via ('tools', 'tools')

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=all_binaries,
    datas=all_datas + [('resources', 'resources'), ('tools', 'tools')],
    hiddenimports=hidden_all,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'scipy',
        'scipy.libs',
        'cryptography',
        'PIL',
        'Pillow',
        'matplotlib',
        'pandas',
        'sympy',
        'psutil',
        'py7zr',
        'pywin32',
        'pywin32-ctypes',
        'backports.zstd',
        'brotli',
        'inflate64',
        'multivolumefile',
        'pybcj',
        'pycryptodomex',
        'pyppmd',
        'texttable',
    ],
    noarchive=False,
    optimize=0,
)

# Filtrar system DLLs que deben venir del SO (Windows 10+)
# ucrtbase.dll y api-ms-win-*.dll del conda pueden diferir de la version del sistema
# y causar "DLL load failed while importing pyexpat: El sistema operativo no puede ejecutar %1"
# a.binaries entries are 3-tuples: (dest_name, source_path, typecode)
system_dll_patterns = ['ucrtbase.dll', 'api-ms-win-']
a.binaries = [(name, src_path, typecode) for name, src_path, typecode in a.binaries
              if not any(p in os.path.basename(src_path).lower() for p in system_dll_patterns)]

# Excloure renderitzador OpenGL per software i moduls Qt sense ús
# (verificat amb pefile: Qt6Multimedia NO depèn de Quick/Qml; qpdf depén de Qt6Pdf)
drop_patterns = [
    'opengl32sw',      # renderitzador OpenGL software (~20 MB)
    'qt6quick',        # QML/Quick: no s'usa al codi (~11 MB amb familia)
    'qt6qml',
    'qt6virtualkeyboard',
    'qt6pdf',          # PDF: no s'usa (~4,5 MB amb qpdf)
    'qpdf',
]
a.binaries = [(name, src_path, typecode) for name, src_path, typecode in a.binaries
              if not any(p in os.path.basename(name).lower() for p in drop_patterns)]
a.datas = [(name, src_path, typecode) for name, src_path, typecode in a.datas
           if not any(p in os.path.basename(name).lower() for p in drop_patterns)]

# Traduccions Qt: mantenir només es/ca/en
def _keep_translation(dest_name):
    norm = dest_name.replace('\\', '/').lower()
    if '/translations/' not in norm:
        return True
    return norm.endswith(('_es.qm', '_ca.qm', '_en.qm'))

a.datas = [(name, src_path, typecode) for name, src_path, typecode in a.datas
           if _keep_translation(name)]

# Force correct libexpat.dll from user's conda env (PyInstaller often picks the
# wrong one from Miniconda3 base, which causes "cannot execute %1" with pyexpat)
libexpat_correct = os.path.join(conda_lib_bin, 'libexpat.dll')
if os.path.exists(libexpat_correct):
    a.binaries = [(name, src_path, typecode) for name, src_path, typecode in a.binaries
                  if os.path.basename(name).lower() != 'libexpat.dll']
    a.binaries.append(('libexpat.dll', libexpat_correct, 'BINARY'))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='JM-MusicAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources\\icons\\JM_MusicAnalyzer.ico'],
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JM-MusicAnalyzer',
)
