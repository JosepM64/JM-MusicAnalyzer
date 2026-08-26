# JM-MusicAnalyzer — Projecte

## Descripció
Analitzador de música i eina DJ. Python 3.13 + PySide6.
- **Versió**: 4.51.0 | **Data**: 2026-08-24 | **Build**: ~221 MB

## Estructura
```
JM-MusicAnalizer/
├── main.py                    # Entry point
├── app.py                     # MusicAnalyzerApp
├── app_state.py               # AppState
├── core/                      # Audio engine, models, formats
├── services/                  # BD (SQLite WAL), settings, bookmarks
│   └── database_manager.py    # DB composador + 4 mòduls
├── ui/
│   ├── main_window.py         # Mode Manager (533 + 3 mixins)
│   ├── performance_window.py  # Mode DJ (252 + 5 mixins)
│   └── widgets/               # playlist, audio_engine, file_list
├── workers/                   # Thread d'escaneig
├── config/api_keys.py         # AcoustID key
├── tools/fpcalc.exe           # Chromaprint v1.6.0
└── scripts/                   # Build i verificació
```

## Com executar
```bat
run.bat
```

## Com compilar
```bat
build.bat
# Resultat: dist/JM-MusicAnalyzer/ (~211 MB)
# Control de pes: si >220 MB, revisar cleanup_dist.bat
```

## Canvi de versió
Editar `JM_MusicAnalizer/__init__.py` → canviar `APP_VERSION`. La build genera automàticament:
- `version_info.txt` (via `scripts/generate_version_info.py`)
- L'EXE incorpora la versió al metadata de Windows

## Verificació
```bat
python scripts/verify_automatica.py
# 161/161 tests
```

## Dependències
```
mutagen, numpy, musicbrainzngs, sounddevice, soundfile, soxr (resampleig), pyacoustid, requests
```

## BD SQLite
- `library.db`, mode WAL, auto-vacuum
- Taula `tracks` amb indexes sha256, genre, artist, filepath

## Últimes 3 versions
- **v4.51.0**: Columna BPM a la graella (col 10) + filtre BPM a la toolbar (rangs de ball, inclou "Sense BPM")
- **v4.50.0**: Fix resampleig (soxr substitueix scipy) + build −45 MB (filtres Qt al spec)
- **v4.49.0**: YouTube import select-tot + navegació post-descàrrega a l'editor

 Versions anteriors: veure fitxer de versions o git log

## Regles
- `conda run` NO funciona. Usar path directe python.exe
- PySide6 sempre via pip
- Build.bat: `PYTHONNOUSERSITE=1`
- La build SEMPRE s'executa des de la carpeta del projecte (`build.bat`). El resultat queda a `dist/JM-MusicAnalyzer/`
- Per provar l'executable, llançar `dist\JM-MusicAnalyzer\JM-MusicAnalyzer.exe` directament

## Manteniment
- **2026-08-24**: Neteja de temporals i backups (~33 MB alliberats):
  - `build/` (32,1 MB, intermedi de PyInstaller — build.bat el regenera/esborra sol)
  - `__pycache__/` (15 carpetes, 0,9 MB) i `.ruff_cache/`
  - `_build_run3.log` (log de build v4.50.0)
  - `_test_app.py`, `_test_imports.py` (tests antics 21/06, sense referències) i
    `scripts/_run_test.bat`
  - `dist/JM-MusicAnalyzer/jm_music_analyzer.log` (log runtime — es regenera sol)
- **Regla**: els agents poden esborrar qualsevol fitxer del projecte sense preguntar.

## Errors coneguts (2026-06-30)

### Tots els errors anteriors (ModuleNotFound core.*) — RESOLTS
- Causa: el directori `core/` estava buit (només 3 fitxers)
- Solució: Restaurat complet del backup `E:\OpenCode\backups\JM-MusicAnalizer_backup\core\`
- Build v4.49.0 (18/08/2026): EXE arrenca sense errors d'importació

### cleanup_dist.bat vs plugins Qt — pèrdua d'estil visual (RESOLT v4.50.0, 2026-08-24)
- **Símptoma**: l'EXE obre però sense l'estil fosc (cau a Fusion: files clares il·legibles, combos blanques, aspecte pla) i les caràtules mostren "SIN CARÁTULA"
- **Causa**: cleanup esborrava plugins necessaris de `_internal\PySide6\plugins`:
  - `styles` → Qt 6.7+ NOMÉS inclou `qmodernwindowsstyle.dll`; els filtres antics per noms (`qwindowsvistastyle`/`qfusionstyle`) esborraven l'ÚNIC estil → sense ell no hi ha mode fosc de Windows
  - `imageformats` → sense JPG/ICO no es decodifiquen caràtules ni icones
  - `multimedia`/`tls` → backends de QMediaPlayer i HTTPS de QtNetwork
- **REGLES per no re-trencar-ho**:
  1. MAI esborrar dins `plugins/`: styles, imageformats, iconengines, multimedia, mediaservice, tls, networkinformation, platforminputcontexts, platforms, generic
  2. Layout PySide6 >=6.5: plugins i traduccions són a `_internal\PySide6\` directament (NO a `_internal\PySide6\Qt6\`)
  3. `soxr` NO s'ha d'esborrar mai (resampleig a `core/dsp.py`; la regla antiga de "libs ML no usades" el matava)
  4. Compte amb `Copy-Item -Recurse` sobre carpeta existent i buida: NIDA el contingut un nivell (va passar amb `styles\styles\`) → verificar profunditat després de copiar
- **Verificació visual ràpida**: engegar l'EXE → les files han de ser fosques, les combos fosques i la caràtula visible
