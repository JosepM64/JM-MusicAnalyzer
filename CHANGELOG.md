# Changelog - JM-MusicAnalyzer

Tots els canvis significatius en aquest projecte es documenten en aquest fitxer.

## [4.54.5] - 2026-09-14

### Fix: botones de la pantalla DJ sin símbolo visible + guarda contra regressions

**Causa**: `APP_GLOBAL_QSS` aplica `QPushButton { padding: 6px 12px }`. En un botón de 24-28 px eso deja **0 px de contenido** (el emoji no se ve), y en un botón de altura fija 22-24 px deja **8-10 px** (texto recortado). Cuatro botones ya "arreglados" en v4.54.4 volvían a romperse porque un `_update_*`/`_on_*` reassignaba el stylesheet sin padding.

**Helper nuevo (`ui/styles.py`)**
- `icon_btn_qss(font_size, extra, pad)` — QSS único para botones de icono: **siempre** sobreescribe el padding (documentado con el porqué).
- Constantes compartidas para los que se reasignan en caliente: `COMPACT_PLAY_OFF_QSS`, `COMPACT_PLAY_ON_QSS`, `COMPACT_STOP_QSS`, `LOOP_BTN_OFF_QSS`, `LOOP_BTN_ON_QSS`.

**21 botones arreglados (verificados con medición: 25/25 `sizeHint <= fixedSize`)**
- `ui/widgets/playlist_widget.py` — barra al lado del selector de lista: `📂` `💾` `🔄` `🗑` `✏` (master) y `📁` `🔄` `📚` `🔄` (2ª lista) + paginación `⏮ ◀ ▶ ⏭`.
- `ui/perf_window_ui.py` — `❓` de ayuda DJ, `▶`/`⏸`/`⏹` compactos (constructor **y** `_update_compact_bar`, que los rompía otra vez), `💾 GUARDAR` (altura 24 con 12 px de padding vertical), LOOP.
- `ui/perf_window_transition.py` — `🔁 LOOP ON`/`OFF` en `_on_loop_toggle` y al final del loop visual (regresión en caliente).
- `ui/widgets/audio_engine_player.py` — `■` (stop) y `🎧` (CUE) de los decks.
- `ui/widgets/cover_widget.py` — `💾` y `🔍` de la carátula (24×18, `border: none` → contenido 0 px).
- `ui/main_window_menu.py` — `?` de ayuda del Manager (detectado por el nuevo check).
- LOOP pasa de 70 a **78 px** ("🔁 LOOP ON" necesitaba exactamente 70: 0 px de margen).

**Guarda contra regressions (`verify_automatica.py`)**
- Nuevo `verify_icon_button_padding()`: recorre `ui/` y `plugins/`, detecta botones con texto y `setFixedSize/Height/Width ≤ 34 px` y avisa (**WARN**, no falla la suite) si **ningún** stylesheet del botón sobreescribe el padding. Resuelve constantes propias con padding (`_ACTION_BTN`, `CUE_BTN_QSS`…) para no dar falsos positivos. Estado actual: **49 botones revisados, 0 avisos**.

**Verificación**: `verify_automatica.py` 177/0 (8 avisos de otros checks), ruff F limpio, medición 25/25 OK y render visual de los 22 botones sin ninguna caja vacía.

## [4.54.4] - 2026-09-14

### Fixes visuales (patrón setFixedSize + padding global del QSS) + limpieza de código muerto

**Bugs visuales**
- `ui/widgets/file_list_data.py` — botones 🎧 de pre-escucha de la graella: el `padding: 6px 12px` del QSS global dejaba 0 px de contenido (símbolo invisible); ahora `padding: 0px` (constante `CUE_BTN_QSS`), 24×15 → **24×17** (necesitaba 16 px de alto) y el texto roto `"??"` de `add_file_row:191` → **🎧**.
- `ui/perf_window_ui.py:709,719` — botones ▶/⏹ de la barra COMPACTA del DJ (22×20 / 20×20) quedaban **invisibles** por el mismo motivo → `padding: 0px`.
- `ui/perf_window_ui.py:578,595,611` — SKIP / CROSSFADER / LOOP → `padding: 0px 4px` (SKIP necesitaba 76 px en 70, LOOP 78 en 70).
- `ui/main_window_menu.py:67,85` — 📁 (32×28) y 🔍♫ (42×28) → `padding: 0px` (necesitaban 42 px).

**Comportamiento**
- `ui/main_window.py:200` `_on_search_reset` — los 3 combos se reiniciaban **sin `blockSignals`** → cada setCurrentIndex(0) disparaba `_apply_filters()` y el botón Reset hacía hasta **4 consultas a la BD**; ahora 1.

**Código muerto eliminado** (auditoría AST + grep; 0 referencias en cada caso)
- `ui/widgets/vu_meter.py` — módulo entero (194 líneas) + su entrada en `verify_automatica.py`.
- `ui/dialogs/quick_scan_dialog.py` `show_tracks_report` (~40 líneas, nunca llamada; su equivalente vive en `tracks_inspector_dialog.py`).
- Señales nunca emitidas ni conectadas: `folderSelected`, `fileDropped` (file_tree_widget), `trackLoadAuto`, `automixSettingsChanged`, `startAutomix` (+ su connect en `perf_window_ui.py:205`), `coverSaveRequested`, `coverOpenRequested` (cover_widget: los botones 💾/🔍 ya llaman a sus handlers), `bookmarkFolderRequested` (duplicado muerto de `bookmarkSelected`), `addToPlaylist`, `addToCurrentList` (+ handlers `_add_to_playlist`/`_add_to_current_list`).
- Handlers no-op: `_on_header_clicked` (file_list_columns) y `_on_seek_pressed` (simple_player_widget) + sus `connect`.
- 21 funciones/métodos sin referencias: `get_reader_for_file`, `ComparisonResult`, `get_logger`, `pad_audio`, `AudioReader.is_supported`, `extract_from_file`, `search_by_isrc`, `is_recursive`/`set_recursive`/`delete_nonexistent_folders`, `_load_suggestions_from_folder`/`update_suggestions`, `_get_simulated_vu_levels`, `_update_transition_timer`, `_close_player`, `get_rating`, `is_file_duplicate`, `_on_load_playlist_clicked`, `get_duration_seconds`/`get_peak`/`reset_peak`, `flush` (+ estado `_dirty`), `get_unique_values_by_folder` (orfenado en cascada).
- Ruff: **33 → 2** avisos, los 2 intencionales (`shiboken6` ancla de PyInstaller en `main.py:43`, sonda de `sounddevice` en `audio_hardware_service.py:24`).

**Verificación**: `verify_automatica.py` 174/0 (8 avisos), ruff F limpio, build OK + smoke test.

## [4.54.3] - 2026-09-14

### Fix: botó DJ de la pantalla inicial tallava la "J"
- `main_window_menu.py:182` — el botó `🎧 DJ` tenia `setFixedSize(52, 28)` i no sobreescrivia el `padding: 6px 12px` del QSS global, que deixava ~26 px útils per al text → es veia "🎧 D".
- Fix: `padding: 0px` a l'estil propi + amplada 52 → 58 px (marge per si la font canvia en un altre PC). Mateix patró que el fix de velocitat DJ de v4.54.1.

## [4.54.2] - 2026-09-14

### Fix: tema fosc propi (en un PC amb Windows en mode clar es veia blanc)
- **Símptoma**: en copiar `dist` a un altre ordinador (sense Python), la graella sortia amb files blanques/fosques alternes i el tema clar.
- **Causa arrel**: `file_list_columns.py:16` i `file_tree_widget.py:23` activen `setAlternatingRowColors(True)`; Qt pinta les files alternes amb el rol **`AlternateBase` de la paleta del sistema**, que `APP_GLOBAL_QSS` no cobreix → en Windows clar = blanc.
- **Fix**: `app.py` nou `MusicAnalyzerApp._apply_dark_palette()` — paleta fosca pròpia amb els tokens (`Base BG_800`, `AlternateBase BG_700`, `Window BG_900`, `Text TEXT_80`, `Highlight PRIMARY`, disabled `TEXT_40`) + `styleHints().setColorScheme(Dark)`. L'app es veu idèntica amb Windows clar o fosc, i també si l'estil natiu no carrega i Qt cau a Fusion.

## [4.54.1] - 2026-09-14

### Impeccable — Manager densitat + DJ velocitat + tokens
- **Design system**: nou `ui/tokens.py` (S0-S5, BG_900-400, PRIMARY/TRANSPORT/SUCCESS/DANGER/WARNING/CYAN, FOCUS_PURPLE) + `DESIGN.md` v4.54.0 → tokens 4.54.1, `ui/styles.py` tokenitzat + `APP_GLOBAL_QSS` aplicat a `main_window.py:68` i `perf_window_ui.py:48` (hover/pressed/disabled/focus 4 estats)
- **Manager densitat**: `file_list_columns.py:60` header `BG_600 10px 600` + selected `#004a80` + row 18px + `Interactive`; `main_window_menu.py` filtres `Genero120/Rating70/BPM90/Buscar200/Reset60` → `11px/5px BG_400` + focus purple, `CYAN` now_playing, progress `BG_800/PRIMARY`, toolbar `BG_700`
- **Fix DJ velocitat**: `audio_engine_player.py:155` BPM `-10/-5/-1` i `+1/+5/+10` + `R` invisibles per `APP_GLOBAL_QSS` padding 6px 12px a 24×20 → afegit `padding:0px` explícit (funcionaven però no es veien)
- **Fix P0**: `main_window_scan.py:1` `QWidget/QHBoxLayout` missing (Ruff F821), dialogs `DARK_DIALOG_STYLE` tokenitzat (`quick_scan`, `tracks_inspector`, `about`), `file_list_data.py` `TEXT_40/WARNING`, `metadata_panel.py` tokenitzat
- **Verify**: `verify_automatica.py` 176/176 PASS, `ruff --select F821` clean, build ~211 MB

## [4.54.0] - 2026-09-10

### DJ: botó Duplicats a la playlist
- **UI**: `playlist_widget.py:293` nou `🔍 Duplicats` al costat de `🧹 Limpiar` + `playlist_filters.py:297` `cleanup_duplicates_in_playlist()` (filepath/SHA256/títol+artista, manté primera, elimina resta de la TAULA, no disc). Disponible a DJ master i Manager.
- **Clarificació**: `🧹 Limpiar` només treu mortes (`!exists`/`read` fail), `🗑 Reset Plays` només plays; duplicats ara té botó propi.

## [4.53.3] - 2026-09-10

### DJ: elimina CROSSFADER duplicat (imatge)
- **UI**: elimina `btn_next_now` de la toolbar (duplicat vist a captura 4.53.2). Queda únic `SKIP | CROSSFADER | LOOP` a mixer (NORMAL) i nou `btn_compact_crossfader` al compact bar (COMPACT) → 1 CROSSFADER per vista, 0 duplicats. `perf_window_ui.py:102,651` + `perf_window_transition.py` disable per ambdós.

## [4.53.2] - 2026-09-10

### DJ: restaura CROSSFADER a COMPACT
- **UI**: restaura `btn_next_now` a toolbar només visible en COMPACT (`perf_window_ui.py:102` + `performance_window.py:167` + `perf_window_ui.py:840`); `btn_crossfader_mixer` només en NORMAL → 1 CROSSFADER per vista, sense duplicat (4.53.0).

## [4.53.1] - 2026-09-10

### DJ: treure CROSSFADER duplicat
- **UI**: eliminat `btn_next_now` de la toolbar (`perf_window_ui.py:102`); queda únic `btn_crossfader_mixer` a `trans_row` → `SKIP | CROSSFADER | LOOP` (vista normal). Neteja `performance_window.py:166` i `perf_window_ui.py:830` (toggle visible).

## [4.53.0] - 2026-09-10

### DJ: CROSSFADER al costat de SKIP/LOOP + fix doble reproducció
- **UI**: `perf_window_ui.py` — `btn_crossfader_mixer` (115×28, #8a2be2) afegit a `trans_row` → `SKIP | CROSSFADER | LOOP`. `btn_next_now` (toolbar) només visible en COMPACT, `btn_crossfader_mixer` només en NORMAL (evita duplicat) via `performance_window.py` i `perf_window_ui.py:_toggle_compact_mode`.
- **Fix doble so**: `perf_window_transition.py` — `_get_next_playlist_path()` amb fallback visual, guards unificats (`_transition||_fade`) + debounce 0.4/0.5s, evita `expected==from` i `dest==from`, sync `playlist_index` i `removeRow` exacte. `_start_transition` i `_handle_transition_logic` bloquegen botons durant fade i eviten càrrega duplicada al deck alliberat.

## [4.52.1] - 2026-08-30

### Fix: després de la descàrrega tornava a la llista anterior en lloc de la carpeta
- **Causa arrel**: `_on_tree_folder_clicked` reiniciava els combos Rating i BPM
  SENSE bloquejar senyals. Amb qualsevol filtre actiu (p.ex. "Sense BPM"),
  `setCurrentIndex(0)` disparava `_apply_filters()` i posava `_current_folder = None`
  → en acabar l'anàlisi, la carpeta de descàrrega no es restaurava.
- Fix: els dos combos ara es reinicien amb `blockSignals`, i `_on_scan_finished_batch`
  fa servir `_current_folder` o `_last_scanned_paths` (que `_on_youtube_downloaded`
  també fixa) com a font de la carpeta a mostrar.

## [4.52.0] - 2026-08-30

### Diàleg "Archivos nuevos" accionable + carpeta de descàrrega visible
- El diàleg que surt en detectar fitxers nous després d'una descàrrega (o escaneig)
  ja NO és només informatiu: cada fila té **✏️ Editar etiquetes bàsiques**
  (títol/artista/gènere/rating amb autocompletat de la BD) i **🔍 MusicBrainz**
  (fingerprint AcoustID + cerca i aplicació de metadades completes).
- **Fix**: en acabar l'anàlisi, la graella tornava a la llista global (500 pistes)
  i la carpeta de descàrrega es perdia de vista ("el fitxer no està al directori").
  Ara es manté visible la carpeta que s'estava escanejant, amb el fitxer nou a dalt.

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
