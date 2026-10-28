# Changelog - JM-MusicAnalyzer

Tots els canvis significatius en aquest projecte es documenten en aquest fitxer.

## [4.54.23] - 2026-10-28

### Fix definitiu: Lista 2 només carregava 1 track (causa arrel = sorting actiu)
- **Símptoma**: el botó de favorit deia `slow balboa (127 tracks)` però la taula de la Lista 2 (DJ) mostrava **una sola fila** (Harry James — "You Made Me Love You").
- **Causa arrel**: `ui/widgets/playlist_widget.py` activa `table.setSortingEnabled(True)`. `add_track()` (`ui/widgets/playlist_track_ops.py`) omplia les cel·les per índex de fila; el **primer** `setItem(r, 0, …)` dispara un re-ordenament immediat que mou la fila acabada d'inserir, de manera que tots els `setItem(r, col)` següents escrivien en una fila diferent. Resultat: 127 files inserides, només 1 poblada → `_rebuild_all_tracks_from_table()` en recollia 1. `load_m3u` ja funcionava perquè suspèn el sorting al voltant del bucle massiu, i `_add_track_from_db` no toca la columna 0 (clau d'ordenació).
- **Fix**:
  - `ui/widgets/playlist_track_ops.py` → `add_track()` desa `isSortingEnabled()`, crida `setSortingEnabled(False)` abans d'inserir i el restaura en acabar d'omplir (abans del `_rebuild_all_tracks_from_table()` final).
  - `ui/widgets/playlist_source_loaders.py` → `load_from_favorite_folder()` i `_load_folder_to_list()` suspenen/restauren el sorting al voltant de tot el bucle `os.walk` + `add_track`.
  - `ruff --select F,I --fix` va resoldre un `I001` preexistent (import `QDialog` fusionat al bloc `PySide6.QtWidgets`).
- **Verificació offscreen** (carpeta real `C:\Mega\JOSEP\_music\slow balboa`): 127 fitxers al disc → `table rows: 100` (pàgina 1), `all_tracks: 127`, `filtered_tracks: 127`, `page_size: 100`, `total_pages: 2`; taula crua després del bucle: 127 files / 127 a `all_tracks`. `py_compile` OK, `ruff F,I` net.
- **Build**: `dist\JM-MusicAnalyzer\JM-MusicAnalyzer.exe` (14.696.732 bytes, FileVersion **4.54.23**) — BUILD EXITOSO.

## [4.54.22] - 2026-10-28

### Lista 2: càrrega de favorits directament del disc (primer intent, insuficient)
- `ui/widgets/playlist_source_loaders.py` → `load_from_favorite_folder()` reescrit per recórrer la carpeta amb `os.walk` i afegir cada fitxer amb `add_track(..., silent=True)`, en lloc de consultar només `db.get_tracks_by_folder()`. Eliminat el `LoadFolderWorker` asíncron que només llegia de la BD.
- Motiu: el recompte `(127 tracks)` del botó és el nombre de fitxers al disc, però `get_tracks_by_folder()` retorna només les pistes indexades a `library.db`; en aquell moment la BD en tenia 127 (verificat), de manera que la consulta no era el coll d'ampolla real.
- Fix `B007` (`dirs` → `_dirs`). **No va resoldre el bug** — la causa arrel era el sorting (vegeu 4.54.23).

## [4.54.21] - 2026-10-28

### Preescolta CUE exclusiva entre Editor i DJ
- **Nou `core/cue_bus.py`**: bus de senyals singleton basat en `QObject` amb `cue_started(str)` i `cue_stopped()` + `get_cue_bus()`. Qualsevol font de CUE l'emet en arrencar/aturar, i totes les altres fonts s'aturen en rebre'l.
- **Fonts connectades**:
  - Editor: `ui/widgets/file_list_actions.py` (`_toggle_cue_preview` / `_stop_cue_preview`) i `ui/widgets/file_list_widget.py` (connexió + handlers).
  - Playlists DJ: `ui/widgets/playlist_cue.py` (`_on_cue_clicked` / `stop_cue`) i `ui/widgets/playlist_widget.py` (connexió + handlers).
  - Decks DJ: `ui/widgets/deck_controls.py` (`_toggle_cue` / `_stop_cue_internal`) i `ui/widgets/audio_engine_player.py` (connexió + handlers).
- **Canvi de mode**: `ui/main_window.py` (`_on_switch_to_performance`, `_on_performance_closed`) atura la CUE de l'editor i emet `cue_stopped()`; `ui/performance_window.py` `closeEvent` també emet `cue_stopped()`.
- **Resultat**: només sona una preescolta a la vegada a tota l'aplicació, i canviar de mode (Editor ↔ DJ) atura la que estigui sonant.
- **Fix posterior (crash a l'EXE)**: `RuntimeError: libshiboken: You can't initialize an PySide6.QtCore.QObject object in class CueBus twice!` — `QObject.__init__()` es cridava manualment dins de `__new__` i PySide el tornava a cridar. Solució: `__new__` sense inicialització manual, `CueBus.__init__` només fa `super().__init__()`, i `get_cue_bus()` cacheja la instància.

## [4.54.20] - 2026-10-28

### Lista 2 (DJ): botó 🆕 "Crear nueva playlist"
- `ui/widgets/playlist_widget.py` → nou `btn_new_playlist` (🆕, 28×28, `icon_btn_qss(11)`) només a la playlist master, al costat de 💾.
- `_on_new_playlist_clicked()`: si hi ha canvis sense desar pregunta Desar/Descartar/Cancel·lar; demana el nom amb `QInputDialog.getText` (afegeix `.m3u` si falta); confirma si el fitxer ja existeix; buida taula i llistes, fixa `_current_playlist_path`, registra l'ús amb `pm.record_playlist_usage` i l'afegeix al combo de recents.
- `ui/i18n_help.py` → ajuda actualitzada a ES i CA (`<b>🆕 Nueva playlist</b>` / `<b>🆕 Nova playlist</b>`).
- `JM_MusicAnalizer/__init__.py` → `APP_VERSION` 4.54.19 → 4.54.20. Build OK.
- **Addicional**: `yt-dlp` actualitzat 2026.10.21 → 2026.10.26 i build refet (bundlat a `_internal/yt_dlp`).

## [4.54.19] - 2026-10-04

### Duplicats: columnes Artista/Títol + selecció llegible
- **Columnes noves «Artista» i «Títol»** a la graella de resultats (11 columnes; dades ja disponibles a l'entrada, sense tocar BD). Índexs dependents actualitzats (Qualitat→9, Eliminar→10, auto-selecció, preview, doble clic intacte al path).
- **Fix selecció blanca**: la fila seleccionada es pintava amb fons blanc i text blanc (il·legible, veure foto usuari) → QSS propi `::item:selected` blau (#0078d4, #005a9e inactiu) + text blanc.
- Test offscreen PASS (capçaleres, contingut, QSS, auto-select pitjor), `ruff --select F` net, `verify_automatica.py` 177/0.

## [4.54.18] - 2026-10-04

### Duplicats: filtre per carpetes dins el diàleg
- **Nou panell «Carpetes on cercar duplicats»** a `DuplicateDialog` (`ui/dialogs/duplicate_dialog.py`): checklist amb els favorits com a preset + les altres carpetes pares presents a les dades, totes marcades per defecte (comportament anterior intacte).
- Filtratge abans d'agrupar (`_selected_scope`): coincideix carpeta exacta o subcarpeta d'un favorit marcat; rescaneig en viu en marcar/desmarcar + botons Totes/Cap; el comptador del peu mostra `(X/Y carpetes)`.
- Sense tocar BD ni `find_duplicates`: només ~40 línies al diàleg. Test offscreen PASS (1 grup amb tot → 0 en desmarcar → Totes/Cap OK), `ruff --select F` net, `verify_automatica.py` 177/0.

## [4.54.17] - 2026-10-04

### Ajuda verificada + català (nou `ui/i18n_help.py` ES/CA) + caràtula editable + contrast info tècnica
- **Ajuda bilingüe**: els 6 temes del Manager (`?`) i els 4 del DJ (`❓`) surten en castellà o català segons ⚙ Idioma (mateix patró que `ui/i18n_menu.py` v4.54.16; per defecte ES). Títol del diàleg «Ayuda -» / «Ajuda -».
- **8 errors corregits** (verificats línia a línia contra el codi):
  - Filtres: no existeix cap combo «Estado» → ara «Género / Rating / BPM» (+ arbre i +⭐).
  - Reproductor: no és doble clic → «Clic en una fila» (carrega sense reproduir).
  - Metadatos/Rating: al panell cal GUARDAR (només a la taula es desa sol).
  - Menú contextual: textos exactes reals (`➕ Añadir a Playlist → 🎧 Añadir a Master Playlist (DJ)`, `📑 Duplicar Archivo`, `📋 Copiar a Carpeta...`, `🚚 Mover Archivo...`, `🗑 Eliminar de Disco`, `🔄 Forçar Lectura Metadades`...).
  - DJ: «⏭️ MEZCLAR SIGUIENTE YA» no existeix com a botó → «⏭️ CROSSFADER»; «🔁 LOOP» és efecte visual de 15 s (no repeteix àudio); «Fade Time 0.5-10 s» fals → «Fade/Silencio (s)» (±60, negatiu = silenci); «📂 M3U/M3U8 o carpeta» parcial (master només .m3u, carpeta només a LISTA 2); «Arrastrar reordena» fals (drag desactivat); «🔄 Crossfader»/«📢 Master» no són botons.
- **Nou a l'ajuda**: caràtula 📂/🗑 (s'aplica al GUARDAR), informació tècnica + ✓/✗ espectral, batch (N), `▶ LANZAR MIX`, COMPACT amb matís d'Espai, `🗑 Reset Plays` / `📜 Sessió`.
- **Caràtula editable** (`ui/widgets/cover_widget.py`, `core/writer/tag_writer.py`, `ui/main_window_metadata.py`): 📂 afegeix/canvia des de JPG/PNG i 🗑 la treu, fins i tot amb «SIN CARÁTULA»; preview immediata, escriptura APIC (jpeg/png) al GUARDAR; al DJ és només lectura.
- **Fix contrast info tècnica** (`ui/technical_panel.py`): els valors anaven en negre (`#000`) sobre fons fosc (il·legibles a la foto) → text `TEXT_100` + etiquetes `TEXT_60`.
- **Fallback versió** (`ui/dialogs/about_dialog.py`): `4.43.0` → `4.54.17`.
- **Verificació**: offscreen PASS (ajuda ES+CA, caràtula jpg/png/remove, APIC write/remove); `verify_automatica.py` 176/0.

## [4.54.16] - 2026-10-04

### Nou: barra de menú en català o castellà (⚙ Ajustos → Idioma)
- **Abast**: només la barra de menús (Archivo/Editar/Ver/Modo/Eina + accions). Nou `ui/i18n_menu.py` amb diccionari ES/CA + `menu_text()` que llegeix `settings["language"]`; `_setup_menu_bar` hi delega (mateixos textos ES que abans).
- **Canvi**: selector al diàleg ⚙ + avís bilingüe de reiniciar (s'aplica a l'arrencada, sense re-traducció en calent).
- **Verificació**: headless PASS (ES→«Archivo/Salir», CA→«Arxiu/Surt», totes les claus amb les dues llengües); `verify_automatica.py` 175/0.

## [4.54.15] - 2026-10-04

### Fix: avisos `QMessageBox` amb fons blanc i text il·legible
- **Símptoma** (foto usuari): «Lista Limpia» amb fons blanc i text quasi invisible.
- **Causa** (`ui/styles.py`): el diàleg natiu no tenia regla al QSS (mateixa família que `QMenuBar`/`QToolTip`/`QTableCornerButton`).
- **Fix**: `QMessageBox` fosc (`BG_500`) + `QMessageBox QLabel` clar (`TEXT_100`) al QSS global; els botons ja eren foscos per la regla `QPushButton`.
- **Verificació**: offscreen PASS; `verify_automatica.py` 175/0.

## [4.54.14] - 2026-10-04

### Fix: quadre blanc a la cantonada de la graella de l'editor
- **Símptoma** (foto usuari): cel·la blanca a dalt a l'esquerra de la taula (entre números de fila i capçalera CUE).
- **Causa** (`ui/styles.py`): el `corner button` del `QTableWidget` no tenia regla pròpia → estil natiu blanc en alguns temes de Windows (mateixa família que `QMenuBar` v4.54.6 i `QToolTip` v4.54.13).
- **Fix**: regla `QTableWidget QTableCornerButton::section` fosca (`BG_600` + bordes) al QSS global.
- **Verificació**: offscreen PASS; `verify_automatica.py` 175/0.

## [4.54.13] - 2026-10-04

### Fix: tooltips il·legibles (blancs) en alguns dispositius
- **Símptoma** (foto usuari): el tooltip dels botons sortia en blanc en uns PCs i bé en uns altres.
- **Causa** (`ui/styles.py`): `APP_GLOBAL_QSS` no tenia cap regla `QToolTip` → queia a l'estil natiu de Windows (mateixa família que la barra blanca de v4.54.6): fons del sistema + text clar de la paleta fosca = il·legible.
- **Fix**: regla pròpia `QToolTip` (fons `BG_500`, text `TEXT_100`, borde `STROKE_400`) al QSS global que s'aplica a cada finestra.
- **Verificació**: offscreen PASS (regla present al QSS, `setStyleSheet` sense error, el text del tooltip es conserva).

## [4.54.12] - 2026-10-04

### Fix: el panell Carpetes sortia buit + `build.bat` no arrencava
- **Panell buit** (foto usuari): `_load_initial_state` només carregava favorits — amb 0 favorits l'arbre quedava a 0 ítems. Ara `_refresh_folder_tree()` (`ui/main_window.py`) cau a `default_library_dir` i si no hi ha res mostra «Sense favorits — afegeix amb +⭐ o clic dret» (ítem deshabilitat que no filtra) en comptes de buit.
- **Senyal mort**: `file_tree.addToFavorites` s'emetia al menú contextual però mai connectat → nou `_on_tree_add_favorite()` que desa el favorit i refresca arbre + combo; `+⭐`/`⚙` del panell (`ui/metadata_panel.py`) avisen la finestra via `_notify_tree_changed()`; obrir amb 📁 recarrega si cal (`ui/main_window_menu.py:_on_toggle_folder_tree`).
- **Build aturat**: tots els `.bat` (`build.bat`, `run.bat`, `scripts/cleanup_dist.bat`, `copy_qt_dlls.bat`, `backup_before_commit.bat`) tenien salts LF (Unix) i `cmd.exe` exigeix CRLF → el build s'encallava sense imprimir res (log a 0 bytes, `dist` intacte). Convertits a CRLF sense tocar contingut.
- **Verificació**: headless offscreen PASS (placeholder, clic no filtra, carpeta/favorit carreguen, senyal connectat, fallback a biblioteca); `verify_automatica.py` 175/0.

## [4.54.11] - 2026-09-26

### Millora: el ⏱ de la DJ mostra el compte enrere del fade
- El label sobre CROSSFADER (`lbl_transition_timer`) mostrava «CAMBIANDO...» sense més; ara ensenya els segons restants (`⏱ 4.8s`) calculats de distància/restant del crossfader × durada del fade, i torna a `⏱ --` en acabar.
- **Verificació**: simulació headless (inici → «CAMBIANDO...» → 5.0s → 4.8s… decreixent → `⏱ --`) PASS; `verify_automatica.py` 175/0.

## [4.54.10] - 2026-09-26

### Fix: l'ordre de la Master es perdia (última pista no sonava + silenci amb loads manuals)
- **Símptoma** (usuari): amb SKIP, càrregues manuals a l'altre plat i crossfaders manuals, l'ordre de la Master es perdia («embolic»).
- **Causa 1** (`ui/perf_window_transition.py`, `_start_transition`): amb la cua exhaurida (`_playlist_index >= len`) avortava TOTA la transició → **l'última pista preparada no sonava mai** en automix.
- **Causa 2** (mateix fitxer): el deck destí només rebia `play()` si el flag `_deck_started` era fals; un load manual posterior (deck recarregat en pausa) o una càrrega en el moment deixaven el deck mut → **silenci amb el crossfader al seu costat** i sessió encallada.
- **Fix**: si queda pista preparada es fa la transició igual sense carregar; el destí rep `play()` segons l'**estat real** (`playbackState()`, helper `_deck_is_playing`) en les dues branques (normal i SKIP+MEZCLAR).
- **Verificació**: simulació headless amb decks falsos (7 escenaris: automix complet, SKIP definitiu, crossfade manual + load manual, destí buit, SKIP+MEZCLAR, via `_check_automix`, mode silenci) → **17/17 PASS**; el compacte usa els mateixos mètodes (només visibilitat) → cobert. `verify_automatica.py` 175/0.

## [4.54.9] - 2026-09-26

### Millores: log rotatiu, botons a la principal, plays de sessió compartits, camps d'editor
- **Log** (`utils/logging_utils.py`, `main.py`): `RotatingFileHandler` 2MB × 3 còpies + nivell INFO — `jm_music_analyzer.log` ja no creix sense límit (màx ~8 MB).
- **Principal** (`ui/main_window_menu.py`, `ui/dialogs/settings_dialog.py`, `services/settings_manager.py`, `ui/main_window_scan.py`): botons 🎧 (àudio) i ⚙ (ajustos) al toolbar + `default_library_dir` que obre «Seleccionar carpeta» ja situat a la biblioteca.
- **Sessió** (`ui/widgets/playlist_play_counts.py`, `playlist_widget.py`): comptador únic compartit entre llistes amb refresh en viu creuat i claus normalitzades + botó 📜 Sessió (punxades en ordre fins al Reset, que ho buida tot a tot arreu).
- **Editor** (`ui/metadata_panel.py`, `ui/styles.py`, `ui/perf_window_ui.py`): camps a 24px + `padding: 2px 4px` propi — el QSS global (`padding: 5px` ≈ 26px necessaris vs 20px de caixa) tallava el text.
- **Verificació**: tests offscreen PASS, `verify_automatica.py` 175/0, `ruff --select F` net d'afegits.

## [4.54.8] - 2026-09-26

### Nou: LOOP amb bordes de colors per secció + F11 pantalla completa + reload d'àudio amb reinici assistit
- **LOOP** (`ui/perf_window_transition.py`): fora l'overlay full-screen que tapava els decks; ara cada secció té el seu **borde de color rotatiu** (Master Playlist, Llista 2, panell info, mixer) + decks amb gradient com abans. Causa arrel trobada i resolta: els `border` QSS **no pinten en subclasses de `QWidget` sense `WA_StyledBackground`** (verificat a píxel 0/254 → 254/254); el flag s'activa durant el LOOP i es restaura després amb els estils originals.
- **F11** (`ui/performance_window.py`): la finestra DJ s'obre **maximitzada per defecte** (`showEvent` + `showMaximized`); **F11** alterna pantalla completa real (tapa la barra de tasques de Windows) i **Esc** en surt tornant a l'estat anterior.
- **Àudio en calent** (`ui/dialogs/audio_config_dialog.py`, `services/audio_hardware_service.py`): botó **«🔄 Recargar»** que redetecta dispositius (DAC USB…) sense tocar cap stream — la música no para; els nous apareixen com `[nou 🆕]` via Qt. Límit honest del backend: PortAudio només escaneja a l'inici, així que si el 🆕 no el veu el motor, en desar s'avisa i s'ofereix **«Reiniciar ara»** (reobre l'app sola amb la config desada); `find_device_by_id` amb **match per tokens** perquè el DAC es resolgui sol després del reinici.
- **Verificació**: tests offscreen PASS (bordes/píxels, reload, restart-flow), `verify_automatica.py` 175/0, `ruff --select F` net d'afegits.

## [4.54.7] - 2026-09-15

### Fix: descàrrega amb URL enganxada — la ruta del fitxer era incorrecta
- **Símptoma** (usuari): cercant funciona, però «quan enganxes la URL del vídeo no el descarrega»: la descàrrega acabava i l'app no trobava cap fitxer → la graella no s'actualitzava i l'anàlisi posterior no tenia res per analitzar.
- **Causa** (`plugins/yt_dl/downloader.py`, `DownloadWorker._download_single`): la ruta es construïa a mà amb el títol **cru** (`Path(output_dir) / f"{info['title']}.mp3"`), però **yt-dlp desa amb el nom SANEJAT** per a Windows (cometes `"` → `＂`, dos punts `:` → `：`…). Amb un títol amb caràcters reservats (p.ex. `Gene Krupa "Sing, Sing, Sing"`) la ruta retornada **no existia** → 0 bytes → "no s'ha descarregat" tot i que l'MP3 era al disc.
- **Fix**: preguntar la ruta a yt-dlp (`requested_downloads[].filepath`, `info['filepath']`, `prepare_filename()` + extensió final) i, si cap existeix, fer servir el fitxer amb l'extensió final creat durant aquesta descàrrega; si no se'n troba cap, s'emet un **error explícit** (abans fallava en silenci).
- **Millora UX**: enganxar una URL ara deixa el resultat **marcat automàticament** (`_on_search` amb 1 resultat d'URL) i el botó «📥 Descarregar» funciona encara que no s'hagi premut «Cercar» (`_on_download` fa servir la URL del camp de text).
- **Verificació**: descàrrega real amb una URL de títol problemàtic → ruta retornada **existent** (7.540.605 bytes; MP3 5:27 / 184 kbps / ID3 ✓) i fitxer present al disc amb el nom sanejat; abans retornava una ruta inexistent de 0 bytes.

## [4.54.6] - 2026-09-14

### Fix: la barra de menú (QMenuBar) se veía blanca en un PC con Windows en modo claro
- **Síntoma** (en un PC nuevo, Windows en modo claro): el resto de la app se veía oscura (barra de herramientas, rejilla, paneles) pero la **barra de menú superior** (Archivo/Editar/Ver/Modo/Eina) salía con fondo **blanco**.
- **Causa**: `APP_GLOBAL_QSS` estiliza `QMenu` (los desplegables) pero **no tenía ninguna regla para `QMenuBar`**; sin regla propia lo pinta el estilo nativo de Windows con los colores del sistema, que no respetan la `QPalette` propia de la app (`app.py:_apply_dark_palette`).
- **Fix**: `ui/styles.py` — reglas nuevas para `QMenuBar` (fondo `BG_900`, texto `TEXT_80`, borde inferior `STROKE_400`) y sus ítems (`::item` transparente con padding, `::item:selected` `BG_500`, `::item:pressed` `PRIMARY`).
- **Verificación**: render de un `QMainWindow` con barra de menú + `APP_GLOBAL_QSS` + la paleta de la app → muestreo de píxeles del fondo: **#0F0F0F** (antes lo pintaba el estilo nativo) y captura visual con los 5 menús legibles.

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
