# Changelog - JM-MusicAnalyzer

Tots els canvis significatius en aquest projecte es documenten en aquest fitxer.

## [4.51.3] - 2026-08-30

### Fix: diàleg de descàrrega congelat + selecció per defecte
- **Congelat**: el diàleg quedava "no respon" després de descarregar. El senyal
  `download_completed` s'emetia amb el diàleg Obert (modal) i el seu handler
  (navegació + càrrega de la carpeta des de la BD, síncron) bloquejava el mateix
  fil. Ara el diàleg es tanca (accept) abans d'emetre el senyal.
- **Barra de progrés**: el rang era 0..N però el worker enviava percentatges
  (0..100) → la barra es quedava a 0 i semblava penjada. Ara rang 0..100.
- **Selecció per defecte**: "Seleccionar / desseleccionar tot" i les files ara
  surten DESMARCADES; si no marques res, el diàleg ho indica.

## [4.51.2] - 2026-08-26

### Fix: la descàrrega de YouTube baixava un vídeo diferent del previsualitzat
- `plugins/yt_dl/main.py` (`_on_download`): abans es re-cercava el títol amb
  `ytsearch1:<títol>` i es baixava el PRIMER resultat d'aquella altra cerca —
  sovint un vídeo diferent (re-pujada, altra versió...). Reproduït: la cerca
  "WWII Swing Era Music 1943 Radio Broadcast" previsualitza el resultat [0] però
  baixava un vídeo de "The Swing Dolls".
- Ara es descarrega la **URL exacta** del resultat marcat: descàrrega ≡
  previsualització ≡ cerca. (Verificat que els IDs ja no discrepen)

## [4.51.1] - 2026-08-26

### Fix (dev): yt_dl resol el ffmpeg del projecte
- `plugins/yt_dl/downloader.py`: en mode desenvolupament, `_get_ffmpeg()` busca primer
  a `tools/ffmpeg.exe` del projecte (el mateix binari que es munta a l'EXE des de
  v4.50.0) i deixa `~/.spotdl/` com a fallback de compatibilitat. Abans depenia de la
  carpeta antiga de spotDL; si faltava, la cerca+descàrrega de YouTube fallaria en dev.
- No afecta l'EXE (mode frozen ja apuntava a `_MEIPASS/tools/ffmpeg.exe`)

## [4.51.0] - 2026-08-24

### BPM a la graella + filtre BPM
- **Columna BPM** a la graella principal (col 10, ordenable numèricament) — mostra el bpm de la BD (el que escriu BPM Analyzer o l'anàlisi pròpia)
- **Filtre BPM** a la toolbar: Sense BPM / <90 / 90-119 / 120-149 / 150-179 / 180+ — combinable amb Gènere, Rating i cerca
- Complement de **BPM Analyzer** (E:\AI\BPM Analyzer): app independent que calcula BPM (librosa + convenció swing) amb mode tap i escriu el TBPM del MP3 i la BD directament

## [4.50.0] - 2026-08-24

### Build: -45 MB + fix resampleig d'àudio
- **Fix resampleig**: Substituït scipy per **soxr** a `core/dsp.py`. Abans, l'EXE anava sense scipy (exclòs al spec) i els fitxers 44,1 kHz sobre sortida 48 kHz sonaven accelerats/desafinats (fallback silenciós). Ara sempre resampleja correctament (~2 MB vs ~60 MB de scipy).
- **Spec**: Exclou `opengl32sw.dll` (~20 MB), família Qt6Quick/Qml (~11 MB), Qt6Pdf+qpdf (~6 MB), Qt6VirtualKeyboard — verificat amb pefile que cap mòdul usat els importa.
- **Spec**: Traduccions Qt filtrades — només es/ca/en (−5,5 MB).
- **Spec**: ffmpeg ara ve de `tools/ffmpeg.exe` del projecte (autocontingut); eliminada dependència de `~/.spotdl/`.
- **cleanup_dist.bat**: Rutes corregides al layout PySide6 ≥6.5 (`_internal\PySide6\plugins`, no `_internal\PySide6\Qt6\plugins`) — des de l'actualització de PySide6 la neteja no feia res. Ara que funciona, preserva els plugins necessaris (styles, imageformats, iconengines, multimedia, tls): esborrar `styles` feia caure l'app a Fusion (UI sense estil fosc) i esborrar `imageformats` trencava les caràtules JPG.

## [4.49.0] - 2026-07-04

### YouTube Import – Select-tot + cançons noves a l'editor
- **Select-tot**: Checkbox "Seleccionar / desseleccionar tot" a dalt de la cerca; alter/desmarca totes les cançons.
- **Navegació post-descàrrega**: En acabar la descàrrega, la finestra principal obre el mode editor a la carpeta de destí, amb les cançons descarregades a dalt de tot i destacades en taronja ("Descarregada recentment"), editables al moment.

## [4.48.0] - 2026-07-03

### YouTube Import: Fixes + Navegació post-descàrrega
- **Fix**: `import plugins.yt_dl` col·lidía amb el paquet `plugins` de site-packages i impedia obrir el diàleg a mode desenvolupament. Afegit `plugins/__init__.py`.
- **Cerca**: Usa `max_results=15` en lloc de 5.
- **URL directa**: Si s'enganxa una URL de YouTube, s'extreu el vídeo directament en lloc de cercar-ho com a text.
- **Navegació**: En acabar la descàrrega, el diàleg emet un senyal i la finestra principal navega a la carpeta de destí i engega l'anàlisi de metadades (no cal tancar el diàleg).

## [4.47.0] - 2026-06-30

### YouTube Import: Persistència + Auto-navegació
- **yt_dl/main.py**: El diàleg recorda l'última carpeta usada (`last_youtube_folder` a SettingsManager) i la carrega per defecte al obrir
- **main_window_menu.py**: En tancar el diàleg, navega automàticament a la carpeta de destí i fa un escaneig ràpid per verificar metadades

## [4.46.0] - 2026-06-30

### Fix: Previsualització YouTube (yt_dl plugin)
- **downloader.py**: Afegit `_add_ffmpeg_to_path()` — yt-dlp 2026.06.09 no detecta ffmpeg via `ffmpeg_location` quan s'usa `download_ranges`; es posa el directori al PATH abans de cridar yt-dlp
- **downloader.py**: `search_youtube()` ara fa servir `duration` (segons) com a fallback quan `duration_string` no està disponible en mode `extract_flat`
- **main.py**: Barra de progrés mostra mode indeterminat (marquee) durant la previsualització; restaurat a mode determinat per la descàrrega completa

## [4.45.0] - 2026-06-30

### Previsualització YouTube (Menu Eina)
- **yt_dl/downloader.py**: Nou `StreamUrlWorker` — obté URL de streaming directe via yt-dlp
- **yt_dl/main.py**: Botó ▶ per fila + doble clic per previsualitzar àudio abans de baixar
- Reproductor `QMediaPlayer` amb stream directe (format m4a, fallback bestaudio)
- Botó ⏹ Aturar amb estat en temps real
- Gestió d'errors: stream no disponible, còdec no suportat

## [4.44.0] - 2026-06-29

### Nou Plugin: yt_dl (Importar de YouTube)
- **yt_dl/downloader.py**: Descàrrega amb yt-dlp via subprocess (YouTube → MP3)
- **yt_dl/analyzer.py**: Anàlisi post-descàrrega (metadades ID3, bitrate, qualitat)
- **yt_dl/main.py**: Diàleg d'importació amb cerca, selecció carpeta, barra de progrés
- **POC completat**: Cadena YouTube → ffmpeg → MP3 funciona amb Python 3.13
- **Ruff**: 0 errors al plugin

### Canvis
- **PROPUESTA_SPOTDL.md**: Document de proposta amb POC completat
- **spotDL descartat**: Error API Spotify, usat yt-dlp directe

## [4.43.0] - 2026-06-21

### Build: Versió auto-generada + version_info.txt al EXE
- **`scripts/generate_version_info.py`**: Llegeix `APP_VERSION` de `JM_MusicAnalizer/__init__.py` (única font de veritat) i genera `version_info.txt` automàticament
- **`.spec` fix**: Afegit `version='version_info.txt'` a l'EXE — ara l'EXE mostra la versió correcta (abans 0.0.0.0)
- **`build.bat` update**: Executa `generate_version_info.py` abans de PyInstaller
- Per canviar de versió: només cal tocar `JM_MusicAnalizer/__init__.py`

### Refactor SoC + Neteja
- **Splitting massiu de fitxers grans** (6 fitxers → mixins):
  - `playlist_widget.py` (2638 → 473 línies, -82%)
  - `performance_window.py` (2144 → 252 línies, -88%)
  - `database_manager.py` (1068 → 108 línies, -90%)
  - `file_list_widget.py` (1051 → 134 línies, -87%)
  - `audio_engine_player.py` (944 → 562 línies, -40%)
  - `main_window.py` (1296 → 533 línies, -59%)
- **Nous mixins/serveis**: 32 fitxers nous
- **Neteja**: 16 fitxers obsolets eliminats, 5 directoris
- **Ruff**: 109 auto-fixes, 0 errors
- **Tests**: 161/161 passats

## [4.42.0] - 2026-06-20

### Startup accelerat
- **Temps d'inici**: 3.4s → 1.95s
- **Deferred CUE player**: Carga lazy del player
- **DB load via QTimer**: No bloqueja l'inici
- **Spec fix**: `a.binaries` tret de `EXE()` (exe 233→6 MB, total 154 MB)
- **Numpy**: Canviat de MKL (conda, 500+ MB) a OpenBLAS (PyPI, 20 MB)
- **JPEG**: Afegit `jpeg8.dll` al build per caràtules
- **DJ Layout 16:9**: Master playlist 60%, EQ tret, columnes Carpeta/Bitrate/Peso
- **Audio config**: "Predeterminado (Sistema)" als combos
- **Scripts**: `run.bat` i `build.bat` auto-detecten conda path

## [4.24.0]

### DJ Mode
- **Playlist editing**: Tecla Delete per eliminar, multi-select (Ctrl/Shift)
- **Clear All** i obrir M3U amb Notepad
- Botons compactes (24x24)

## [4.23.0]

### DJ Mode
- **Beat Counter**: Comptador visual de beats (1-2-3-4) sincronitzat al BPM del deck

## [4.5.0]

- **Quick scan dialog**: Diàleg per seleccionar carpeta de favoritos a escanejar
- **Informe de pistes**: Mostra pistes de baixa qualitat o corrompudes

## [4.4.0]

- **CUE Player**: Widget de preescolta CUE per files de playlist
- **Track edit dialog**: Diàleg per editar metadades d'una pista

## [4.3.0]

- **Cover art service**: Servei centralitzat per a la gestió de carátules
- **Cover widget**: Millorat amb botons d'acció

---

## Versions anteriors

Les versions anteriors a 4.3.0 no estan documentades en aquest fitxer. Consultar l'historial de git o els fitxers de backup per a més detalls.
