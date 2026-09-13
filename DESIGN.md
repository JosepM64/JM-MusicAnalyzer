# JM-MusicAnalyzer — DESIGN.md
> Design system for the existing PySide6 6.11.2 / Qt Widgets / QSS application. Windows 10/11 dark Operate tool. No HTML, no rewrite. Incremental, QSS-compatible.

**Version:** 4.54.1 | **Platform:** Windows desktop 1100–1920px | **Mode:** Operate (Manager dense, DJ performative) | **Stack:** QSS, QPalette, SQLite, sounddevice, PyInstaller onedir

---

## 1. Visual Philosophy

**“Quiet instrument, not a website.”** Manager = reference library (dense, scannable, neutral). DJ = performance instrument (contrast, immediacy, 2m readability). Both share one dark world so switching modes doesn’t re-learn.

- **Dark is the product:** `#0f0f0f` is not a theme, it’s the room lights off. Surfaces get lighter only to separate functional layers (library < table < panel).
- **Color does work:** Only for state, transport and quality. No decoration. Purple = transport/transition, blue = primary action, green = safe, orange/red = warning/peak.
- **Density on purpose:** Manager earns its 11 columns; DJ earns its negative space. Never trade one for the other.
- **Native first:** Respect Windows conventions (menu bar, Ctrl+O/S/F, F1, focus frames) inside custom dark chrome. Don’t fight QStyle, wrap it.
- **Pixels are physical:** Every `FixedSize` must survive 150% and 200%. Design in px, verify in dpi.

## 2. Layout Principles

**Grid 4/8. Shell → Work → Chrome.**

- **Shell:** `QToolBar 32px` (Manager) / `32px` (DJ) top, `QStatusBar 18px` + `QProgressBar 14px` bottom. Never double-toolbars.
- **Work:** `QSplitter` only. Manager `200|600|320` (tree | table | right panel), DJ `decks_container 0` + `compact_bar 0` exclusive, `bottom_splitter 3:2` (master | info/second list). Splitter handle 8px `#555` → `#0078d4` hover.
- **Chrome:** Cards = `QFrame StyledPanel #252525 1px #333 radius 4px`. No nested cards.
- **Margins:** Outer `4px`. Card inner `8px`. Section stack `8px`. Row stack `4px`. Dense table `2px`.
- **Stretch rule:** One `addStretch` per row, never two. Controls that must stay together are in their own `QHBox` with `setSpacing(4)`.
- **Visibility, not destruction:** Toggle lists/panels with `setVisible`, never recreate. State survives mode switch.

## 3. Spacing Scale (4pt, QSS-friendly)

| Token | px | Use |
|---|---|---|
| `S0` | 0 | Collapsed splitter, borderless |
| `S1` | 4 | Tight stacks, table cell padding, chip gaps |
| `S2` | 8 | Card padding, row gaps, toolbar spacing |
| `S3` | 12 | Section gaps (master | VU) |
| `S4` | 16 | Panel outer, dialog outer |
| `S5` | 24 | Dialog sections |

```
setContentsMargins(S2,S2,S2,S2)  // panels
setContentsMargins(S1,S1,S1,S1)  // rows
setSpacing(S1) // tight  | S2 // normal | S3 // loose
```
No `S` outside this table.

## 4. Typography Hierarchy — Segoe UI, Windows-native

**One family.** `Segoe UI` everywhere. Fallback `sans-serif`. No custom font download.

| Level | Size | Weight | Color | Where |
|---|---|---|---|---|
| `T_TITLE` | 14px | 700 | `#0078d4` | `JM DJ ENGINE`, dialog title |
| `T_SECTION` | 11px | 700 | `#a0a0a0` | `MASTER`, `METADATOS`, group headers |
| `T_BODY` | 11px | 400 | `#e6e6e6` | Toolbar labels, player info |
| `T_BODY_SM` | 10px | 400 | `#cccccc` | Table cells, infoPanel text |
| `T_CAPTION` | 9px | 700 | `#888888` | Scales (0-300), BPM ticks, VU A/B |
| `T_MONO` | 9px | 400 | `monospace #888` | file path, time `00:00/00:00` |
| `T_MICRO` | 8px | 700 | `#888` | Compact bar labels |

Line-height implicit Qt. No `font-size <8px`. QSS: `font-family: 'Segoe UI', sans-serif;`.

## 5. Color Semantics — tokens, not hex soup

**Base scale (dark only, incremental from today):**
```
BG_900 #0f0f0f  // QMainWindow (today #121212 → migrate)
BG_800 #1a1a1a  // dialogs, compact_bar (keep)
BG_700 #222222  // QToolBar (today #222/#333 unify to #222)
BG_600 #252525  // cards, mixer_panel (keep)
BG_500 #2b2b2b  // menus, hover surface
BG_400 #333333  // borders, table header
STROKE_400 #444444 // 1px strokes
TEXT_100 #ffffff // headline
TEXT_80  #e6e6e6  // body
TEXT_60  #a0a0a0  // section / disabled
TEXT_40  #888888  // caption
```

**Semantic:**
```
PRIMARY #0078d4  // primary action, selected row #004a80 is PRIMARY 28%
PRIMARY_HOVER #1084d8
TRANSPORT #8a2be2 // SKIP / CROSSFADER (keep)
TRANSPORT_HOVER #9b4de0
SUCCESS #00aa00  // LOOP ON, best quality, compact play
SUCCESS_DIM #1a3a1a // play idle bg
DANGER  #d32f2f  // delete, clip peak
WARNING #ff9800  // auto-select worst, mb_per_min
PEAK    #ff0000 → #ffff00 → #00ff00 VU gradient (keep)
CYAN    #00d4ff  // now-playing, genre splash
```

**Rule:** No new hue without semantic. White/black `INPUT_FIELD_STYLE` is banned — edits use `BG_400/#333` + `TEXT_100`.

## 6. Widget States — one spec for all

```
QPushButton {
  background: BG_500; color: TEXT_80; border: 1px STROKE_400; padding: 6px 12px; border-radius: 4px; font-weight: 600;
}
QPushButton:hover { background: #3a3a3a; }
QPushButton:pressed { background: PRIMARY; border-color: PRIMARY; }
QPushButton:checked { background: SUCCESS; color: #fff; border-color: SUCCESS; }
QPushButton:disabled { background: BG_600; color: TEXT_40; border-color: BG_400; }
QPushButton:focus { border: 1px solid #6a1b9a; } /* keep existing purple focus */

QLineEdit, QComboBox, QSpinBox {
  background: BG_400; color: TEXT_100; border: 1px STROKE_400; border-radius: 3px; padding: 5px;
}
QLineEdit:focus, QComboBox:focus { border-color: #6a1b9a; }
QComboBox QAbstractItemView { background: BG_400; selection-background: #6a1b9a; }

QSlider::groove:horizontal { height: 6px; background: BG_400; border-radius: 3px; }
QSlider::handle:horizontal { background: PRIMARY; width: 14px; height: 18px; margin: -6px 0; border-radius: 3px; }
QSlider:disabled { opacity: 0.5; }
```

Every button must have `:hover/:pressed/:disabled/:checked/:focus`. No `white` edits.

## 7. Button Hierarchy — DJ needs instant read

| Rank | Style | Example | Size |
|---|---|---|---|
| **Primary** | `PRIMARY` filled | `GUARDAR`, `LANZAR MIX` | `10-16px 30-32h` |
| **Transport** | `TRANSPORT` filled | `SKIP`, `CROSSFADER` 70-115×28 | `11px 700` |
| **Toggle** | `BG_500` → `SUCCESS` checked | `LOOP`, `COMPACT`, `LISTA 2` | `24-28h` |
| **Ghost** | `BG_500` 1px stroke | `VOLVER`, `CONFIG AUDIO`, `Reset Plays` | `28h` |
| **Icon** | `44px circle` | `?` help 24×24 → grow to 28×28 | `12px 700` |
| **Danger** | `DANGER` filled | `Eliminar Seleccionado`, `Sí` confirm | `padding 8x16` |

Never mix `TRANSPORT` and `PRIMARY` in same row except mixer (where crossfader is primary). Debounce disables via `setEnabled(false)` 0.4-0.5s, not visual hide.

## 8. Table Design — Manager earns 11 cols, make them humane

- **Header:** `BG_600 #252525`, `10px 600 TEXT_60`, `2px TEXT_60` top rule, `sortIndicator` `PRIMARY`. Fixed height 22px. No `setSectionResizeMode Stretch` globally — use `Interactive` + `saveState` to QSettings.
- **Rows:** 18px `QTableWidget` `verticalHeader default 18px`, `TEXT_80 10px`, `selected #004a80` (`PRIMARY` 28%). Alternating no — dark table would strobe; keep flat `#1a1a1a`.
- **Columns today:** 0:No 30, 1:CUE 30, 2:Plays 35, 3:Artista 120, 4:Título 150, 5:Dur 55, 6:Genero 80, 7:Rating 60, 8:Carpeta 160, 9:Bitrate 50, 10:Peso 55 → **keep widths** but make 8:Carpeta `Interactive` resizable and persist. Add column picker in header `QMenu`.
- **Cells:** 1:CUE `RowPreviewPlayer` 30×20 (`▶` 9px), 7:Rating `gold` stars, 9:Bitrate `?/123` muted, 10:Peso `x.xM`. No icons in text cells.
- **Empty:** `QTableWidget` zero rows → `QLabel` centered `No hi ha pistes — arrossega M3U o Escaneja` (not blank).
- **Density toggle (future):** `Comfortable 18px / Compact 16px` via `verticalHeader setDefaultSectionSize`.

## 9. Dialogs — 3 templates only

- **Confirm** (`Limpiar`, `Reset Plays`): `DARK_DIALOG_STYLE` `400w` | icon 24 + 2-line copy + `No` ghost + `Sí DANGER` | Esc=No.
- **Tool** (`Duplicados`, `Baja Calidad`): `900×500` table `QTableWidget` same header as Manager, `Buscar/Seleccionar Peores` `WARNING`, `Eliminar Seleccionado` `DANGER`, sticky footer.
- **Form** (`TrackEdit`, `AudioConfig`): `DARK_METADATA_DIALOG_STYLE`  `252525` bg, `QLineEdit` `BG_400` 5px padding, `QComboBox` same, focus purple `#6a1b9a`, `GUARDAR PRIMARY` 10px. Never white inputs.

All dialogs `exec()` modal, `X` closes = `Reject`, `showMessage` 3s after close.

## 10. Navigation

**Manager:** MenuBar `Archivo/Editar/Ver/Modo/Eina` (native) is truth; Toolbar is accelerators, not replacement. Order: `lbl_now_playing` → `📁 tree` → `Escanejar` → `Genero/Rating/BPM/Search/Reset` → `CUE:` → `DJ` → `?` → `cores`. Trim to 8 controls max; overflow into `Ver` menu.
**DJ:** Toolbar `VOLVER | CONFIG AUDIO ⚙ | ACERCA | ? | LISTA 2 | COMPACT` `spacer` `BPM` `JM DJ ENGINE`. Mode is a window, not a tab — `hide()` Manager when DJ `show()`, `closed` signal restores Manager. Never embed DJ inside Manager splitter.
**Context:** Right-click on file row = `Añadir a DJ Master / Eliminar / Mover` — keep 3, add `Netejar duplicats` as disabled when no dupes.

## 11. Manager-Specific Rules

- **Information > decoration:** Neutral `#1a1a1a`, no vinyl, no gradients. Color only on `Rating gold`, `Plays` muted, `now_playing` `CYAN` or `CUE orange #ffa500`.
- **Filters:** Keep `Genero 120 / Rating 70 / BPM 90 / Buscar 200 / Reset 60` but increase `font-size 11px`, `padding 5px`, focus purple. Persist `currentText` to `SettingsManager`.
- **Table readability:** `font-size 10px`, `row 18px`, `selection #004a80`, `horizontalHeader 10px`. Add `QToolTip` for truncated `Carpeta`. Keep `isSortingEnabled` true but debounce `filter_timer 300ms`.
- **Right panel:** Fixed 320px is correct; `SimplePlayerWidget 120h` max. `MetadataPanel` white edits → migrate to `BG_400`. `CoverWidget 150×160` keep.
- **Tree:** Hidden by default is wrong for discovery — show on first run with 1 bookmark, else show hint `📁 Favoritos buits → Afegeix`.

## 12. DJ-Specific Rules — performance first

- **Hierarchy (top→bottom):** `decks` (largest) > `crossfader` (second) > `SKIP/CROSSFADER/LOOP` > `VU/MASTER`. Today crossfader 30h is too short — grow to 36h handle 16×20 for 2m grab.
- **Decks:** `AudioEnginePlayerWidget` vinyl 230px keep, `VOL` vertical 45h + `CUE` 35h to the right of vinyl is correct — don't stack below. `lbl_info` 11px bold white single line, `lbl_genre` gradient keep but dim to `12px`.
- **Mixer:** `VU 14×180` correct but increase to 16px for distance; `MASTER 40×180` 0-300% keep, `gradient 16px` is the unit — keep. `CLIP #222/#444` → `#ff0000/white` on peak — make 200ms hold, not flash.
- **Crossfader row:** Keep `A◄ [slider 8px gradient] ►B` 4px spacing, handle white 14×18. Add 8px tick labels `A 50/50 B` below slider for center detent.
- **Transport:** `SKIP 70×28 TRANSPORT` | `CROSSFADER 115×28 TRANSPORT` | `LOOP 70×28 toggle` centered with `addStretch` both sides — keep. `LOOP ON` `#00aa00` is correct success.
- **Separation:** Deck A border `2px #00aaff` when active is too thin — use `QFrame` 2px left accent only, not full gradient (reduces repaint). Keep `qlineargradient` for LOOP mode 15s only.
- **Distraction:** No animation outside LOOP. `compact_bar` progress 8px `#0078d4` keep at 10fps (`100ms` timer) — not 60fps.

## 13. Playlist-Specific Rules

- **Master vs Second:** Master `is_master=true` has `Fade/Silencio -60..60`, `Reset Plays/dull`, `Limpiar`/`Duplicats` `10px`. Second `is_master=false` adds `Genre/Rating/Search` + pagination `10/500` — keep pagination bottom, not top.
- **States:** `LANZAR MIX` checkable large `32h PRIMARY` when idle → `SUCCESS` when active via `_update_automix_button_style` — keep.
- **CUE:** `slider_cue_vol 60w` + `cue_progress 80×4` tiny but correct for pre-listen; no need bigger.
- **Drag:** Disabled today (`setDragEnabled(false)`) but spec says drag & drop for M3U reorder — re-enable with `InternalMove` + `dropIndicator` `PRIMARY`.

## 14. Accessibility (Windows Operate)

- **Contrast:** `TEXT_60 #a0a0a0` on `BG_800 #1a1a1a` 8.1:1 pass; fix `TEXT_40 #888` on `BG_400 #333` fails — darken `BG_400` to `#2e2e2e` or lighten `TEXT_40` to `#9a9a9a` for 4.5:1.
- **Target:** Minimum `24×24` (WCAG 2.5.5). Grow `btn_play 22×20` → `28×24`, `btn_stop 20×20` → `28×24`, `CUE 30×20` keep, `Rating stars 14px` keep + `2px` hit padding.
- **Focus:** Visible `1px #6a1b9a` on every `QPushButton:checked/focus`, `QTableWidget::item:focus` `1px dashed TEXT_60`. Never `outline: none`.
- **Keyboard:** `Ctrl+O` Escanear carpeta, `Ctrl+S` Guardar M3U, `Ctrl+F` focus `search_field`, `Space` compact toggle (already, block when `QLineEdit` focused keep), `Delete` remove row (already), `↑/↓` transport in `SimplePlayerWidget`, `F1` help. Show shortcuts in `QToolTip` `“Escanear (Ctrl+O)”`.
- **Screen reader:** Add `setAccessibleName("Taula fitxers")`, `setAccessibleDescription("11 columnes")`, `RatingWidget` `accessibleName="Puntuació 3 de 5"`.
- **Reduced motion:** Respect `prefers-reduced-motion` via `SettingsManager` bool → disable LOOP 15s vinyl gradient.

## 15. Keyboard Interaction

| Action | Shortcut | Where |
|---|---|---|
| Escanejar carpeta | `Ctrl+O` | Manager |
| Escaneig ràpid | `Ctrl+Shift+O` | Manager |
| Guardar M3U | `Ctrl+S` | Playlist master |
| Buscar | `Ctrl+F` | Manager (focus `search_field`) |
| Reset filtres | `Esc` when `search_field` focused | Manager |
| Play/Pause | `Space` (when table focused) / `▶` btn | Manager + DJ deck |
| Next/Prev track | `Ctrl+→` / `Ctrl+←` | Manager |
| Afegir a DJ Master | `Ctrl+D` | Manager row context + `Enter` |
| CROSSFADER | `Ctrl+·` / `C` | DJ both views |
| SKIP | `Ctrl+Shift+→` | DJ |
| LOOP toggle | `L` | DJ |
| COMPACT toggle | `Space` (blocked in edits, keep) | DJ |
| Ajuda | `F1` | Both |

No single-key `Space` for transport when table focused — reserve for compact.

## 16. High-DPI Windows

- **Units:** Replace `setFixedSize(70,28)` with `QSize(70,28)` * `devicePixelRatio` via `self.devicePixelRatio()` or use `em` via `QFontMetrics`. Minimum: wrap `fixedSize` in `int(70 * self.logicalDpiX()/96)`.
- **Icons:** Replace emoji unicode (`📁🔍🎧`) with `QIcon(":/icons/...svg")` from `resources/icons` sprite; `JM_MusicAnalyzer.ico` provide `16/32/48/256` already — add `svg` for toolbar to stay crisp at 150/200%.
- **Images:** `CoverWidget 150×160` use `QPixmap` scaled with `Qt.SmoothTransformation` + `devicePixelRatio`; vinyl 230px `VinylWidget` paint at `size * dpr`.
- **Borders:** `1px` stays `1px` physical — set `border: 1 * dpr` via `qproperty` or keep hairline but test at 200%.
- **Verify:** Test 100/125/150/200% in Windows Display settings, 1366×768 minimum. No `FixedWidth 200` for `file_tree` — use `setMinimumWidth(180)` + `maximumWidth 320` with splitter.

## 17. QSS Guidelines — how to author inside this codebase

- **One file, two scopes:** Keep `styles.py` as token source, but apply QSS per-shell not globally. `MainWindow` → `setStyleSheet(DARK_WINDOW)` once; `PerformanceWindow` → `setStyleSheet(DARK_DJ)` once. No `setStyleSheet` inside `add_track` loops.
- **Selector discipline:** `QPushButton`, `QPushButton:hover`, `:pressed`, `:checked`, `:disabled`, `:focus` only. No `QWidget#name` unless unique.
- **No inline hex:** `color: #888` inside `file_list_data.py:148` is banned — use `TEXT_40`. Extract to `tokens.py: TEXT_40 = "#9a9a9a"`.
- **Specificity:** `QTableWidget::item:selected` not `QTableWidget::item:selected:checked`. `QHeaderView::section` 2px padding max.
- **Performance:** QSS reparses on every `setStyleSheet`; batch in `_apply_dark_theme` once, not per `add_track` (today `playlist_track_ops.py` creates `RowPreviewPlayer` per row — ok, but no `setStyleSheet` there).
- **Migration path (no rewrite):** Day 1 extract `tokens.py` 12 vars, replace 5 worst `white #fff` edits to `BG_400`. Day 2 unify 4 `setStyleSheet` in `perf_window_ui._apply_dark_theme` to tokens. Day 3 table header. No file renamed.

## 18. Reusable Component Guidelines

- **Button:** `AppButton(QPushButton)` subclass with `variant: primary/transport/ghost/toggle/danger` + `size: sm/md/lg`. One `paintEvent`, QSS via `property variant`. Replace 170 inline `setStyleSheet`.
- **Chip/Tag:** `GenreLabel` already exists — promote to `StatusChip` for `BPM`, `CLIP`, `Vu A/B` labels.
- **Slider:** `CueSlider(QSlider)` 6px groove 14px handle `PRIMARY` — reuse for `vol_master` (vertical 40×180) + `crossfader` (horizontal 8px) via `orientation` property.
- **Table:** `FileTable(QTableWidget)` encapsulate `11 cols`, `saveState/restoreState`, `emptyView QLabel`, `RatingWidget` per row. Use in Manager + DJ master (same class, different `is_master`).
- **Dialog:** `AppDialog(QDialog)` base with `DARK_DIALOG_STYLE` + `accent` header, footer `No/Sí` order. Inherit `DuplicateDialog` + `TracksInspector`.
- **InfoPanel:** `MetadataForm(QFrame)` with `QLineEdit` `BG_400` + `RatingWidget` + `GUARDAR PRIMARY` — used in Manager right + DJ infoPanel (same, not duplicate).
- **Icon:** `IconButton(QPushButton)` 24×24 circle `?` help — unified.

---

**What not to change now:** audio `MasterEngine 44.1k/block 1024`, DB `limit 500/WAL`, worker `cpu_count-2`, `spec` plugin allowlist, `tools/` paths — visual only. Tokens first, then Manager density (header + filter bar), then DJ immediacy (crossfader 36h + VU 16px), then a11y. Two bounded polish passes max.
