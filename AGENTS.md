# JM-MusicAnalyzer — Projecte

## Descripció
Analitzador de música i eina DJ. Python 3.13 + PySide6.
- **Versió**: 4.54.7 | **Data**: 2026-09-15 | **Build**: ~211 MB

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
python verify_automatica.py
# o: python scripts/verify_automatica.py  (shim)
# 176/176 tests
```

## Dependències
```
mutagen, numpy, musicbrainzngs, sounddevice, soundfile, soxr (resampleig), pyacoustid, requests
```

## BD SQLite
- `library.db`, mode WAL, auto-vacuum
- Taula `tracks` amb indexes sha256, genre, artist, filepath

## Últimes 3 versions
- **v4.54.7**: Fix descàrrega YouTube amb URL enganxada — `DownloadWorker._download_single` retornava la ruta construïda amb el títol CRU i yt-dlp desa amb el nom SANEJAT (`"` → `＂`) → la ruta no existia i semblava que no s'hagués descarregat; ara es pregunta la ruta a yt-dlp + fallback al fitxer creat; enganxar una URL deixa el resultat marcat i «Descarregar» funciona sense prémer «Cercar»
- **v4.54.6**: Fix `QMenuBar` blanc en un PC amb Windows en mode clar — el QSS no tenia regles per a la barra de menú i la pintava l'estil natiu amb els colors del sistema; ara `APP_GLOBAL_QSS` la pinta (`BG_900` + `::item:selected` `BG_500`)
- **v4.54.5**: Fix botons de la pantalla DJ sense símbol (21 botons: barra de la llista, paginació, compactes, LOOP, ❓, ■/🎧 dels decks, 💾/🔍 caràtula) amb el nou helper `ui/styles.icon_btn_qss()` + constants per als que es reassignen en calent; guarda `verify_icon_button_padding()` a `verify_automatica.py` (WARN) perquè no torni a passar

 Versions anteriors: veure fitxer de versions o git log

## Regles
- `conda run` NO funciona. Usar path directe python.exe
- PySide6 sempre via pip
- Build.bat: `PYTHONNOUSERSITE=1`
- La build SEMPRE s'executa des de la carpeta del projecte (`build.bat`). El resultat queda a `dist/JM-MusicAnalyzer/`
- Per provar l'executable, llançar `dist\JM-MusicAnalyzer\JM-MusicAnalyzer.exe` directament

## Manteniment
- **2026-08-24**: Repositori git inicialitzat — commit inicial `d69492f` (castellà, 119
  fitxers, v4.51.0). `.gitignore` cobreix caches, build/, dist/, logs i
  `config/api_keys.py`; s'ha afegit excepció `!JM-MusicAnalyzer.spec` per versionar
  la config de build. Els binaris `tools/` (ffmpeg, fpcalc) estan versionats per fer
  la build autocontinguda.
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

### Botons d'icona amb padding global — símbol invisible (RESOLT v4.54.4/v4.54.5, 2026-09-14)
- **Símptoma**: botons petits (24-28 px) que es veuen com una caixa buida o amb el text tallat; l'usuari diu "no es veu el que són" (tot i que el tooltip funciona)
- **Causa**: `APP_GLOBAL_QSS` (`ui/styles.py`) aplica `QPushButton { padding: 6px 12px; }` a tota la finestra. En un botó de 28 px queden **2 px** de contingut; en un de 24 px, **−2 px**; en un d'alçada fixa 22-24 px, **8-10 px** (text retallat verticalment)
- **REGLES**:
  1. Tot botó amb `setFixedSize/setFixedHeight` petit ha de sobreescriure el padding: `ui/styles.py:icon_btn_qss(font_size, extra, pad)` (mai escriure el QSS a mà)
  2. Els botons que es **reassignen en calent** (`_update_*`/`_on_*`) han de fer servir les constants de `ui/styles.py` (`COMPACT_PLAY_OFF_QSS`, `COMPACT_PLAY_ON_QSS`, `COMPACT_STOP_QSS`, `LOOP_BTN_OFF_QSS`, `LOOP_BTN_ON_QSS`) — sinó el fix del constructor es perd al primer refresc (va passar amb ▶/⏸ compactes i LOOP a v4.54.4)
  3. `verify_automatica.py:verify_icon_button_padding()` ho vigila (avís WARN) i resol constants pròpies amb padding (`_ACTION_BTN`, `CUE_BTN_QSS`) per no donar falsos positius
- **Verificació**: mesurar `sizeHint()` vs `setFixedSize()` amb la **plataforma real de Windows** (en `offscreen` les mètriques són falses: dona OK a botons que a l'app es tallen) + render de la finestra
- **Relacionat (v4.54.2)**: el tema fosc era dependent del mode de Windows per als widgets que el QSS no cobreix (les files alternes de la graella agafaven `AlternateBase` del sistema) → `app.py:_apply_dark_palette()` fixa la paleta pròpia (Base/AlternateBase/Window/Text/Highlight)
- **Relacionat (v4.54.6)**: **`QMenuBar` no tenia cap regla al QSS** → en un PC amb Windows en mode clar la barra de menú sortia BLANCA mentre la resta de l'app era fosca (l'estil natiu la pinta amb els colors del sistema i no fa cas de la `QPalette`). Regla: qualsevol widget d'un contenidor natiu (menú, barres, indicadors) ha de tenir la seva pròpia regla al QSS; la paleta sola no basta

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
