"""
Design tokens — single source of truth per DESIGN.md §3-5.
No logic, only constants. QSS-compatible hex strings + px integers.
Incremental: existing code migrates by importing, no rewrite.
"""

# ── Spacing (4pt grid) ─────────────────────────────────────
S0 = 0
S1 = 4
S2 = 8
S3 = 12
S4 = 16
S5 = 24

# ── Color — base dark scale ────────────────────────────────
BG_900 = "#0f0f0f"  # QMainWindow
BG_800 = "#1a1a1a"  # dialogs, compact_bar
BG_700 = "#222222"  # QToolBar (unifies #222/#333)
BG_600 = "#252525"  # cards, mixer_panel
BG_500 = "#2b2b2b"  # menus, hover
BG_400 = "#333333"  # borders, table header (darkened from #333→#2e2e2e if needed)
STROKE_400 = "#444444"
STROKE_300 = "#555555"

TEXT_100 = "#ffffff"
TEXT_80 = "#e6e6e6"
TEXT_60 = "#a0a0a0"
TEXT_40 = "#9a9a9a"  # was #888 → passes 4.5:1 on BG_400

# ── Semantic ───────────────────────────────────────────────
PRIMARY = "#0078d4"
PRIMARY_HOVER = "#1084d8"
PRIMARY_ACTIVE = "#006abb"
TRANSPORT = "#8a2be2"
TRANSPORT_HOVER = "#9b4de0"
SUCCESS = "#00aa00"
SUCCESS_DIM = "#1a3a1a"
DANGER = "#d32f2f"
WARNING = "#ff9800"
CYAN = "#00d4ff"
FOCUS_PURPLE = "#6a1b9a"

PEAK_RED = "#ff0000"
PEAK_YELLOW = "#ffff00"
PEAK_GREEN = "#00ff00"

# ── Typography — Segoe UI ──────────────────────────────────
FONT_FAMILY = "'Segoe UI', sans-serif"
FONT_MONO = "monospace"

T_TITLE_SIZE = 14  # 700 PRIMARY
T_SECTION_SIZE = 11  # 700 TEXT_60
T_BODY_SIZE = 11  # 400 TEXT_80
T_BODY_SM_SIZE = 10  # 400 #cccccc
T_CAPTION_SIZE = 9  # 700 #888
T_MONO_SIZE = 9
T_MICRO_SIZE = 8

# ── Radius / Borders ───────────────────────────────────────
RADIUS_SM = 3
RADIUS_MD = 4
BORDER_W = 1

# ── Sizing — hit targets ───────────────────────────────────
HIT_MIN = 24  # WCAG 2.5.5
BTN_H_SM = 24
BTN_H_MD = 28
BTN_H_LG = 32
TOOLBAR_H = 32
STATUS_H = 18
SPLITTER_HANDLE = 8
