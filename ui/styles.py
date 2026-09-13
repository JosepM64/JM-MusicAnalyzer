"""
Global design system — normalized per DESIGN.md §3-7,17.
Tokens imported from ui/tokens.py. Backward-compatible: old names kept, now token-driven.
No layout changes. Focus/hover/disabled normalized globally.
"""

from ui.tokens import (
    BG_400,
    BG_500,
    BG_600,
    BG_700,
    BG_800,
    BG_900,
    BORDER_W,
    DANGER,
    FOCUS_PURPLE,
    FONT_FAMILY,
    PRIMARY,
    PRIMARY_HOVER,
    RADIUS_MD,
    RADIUS_SM,
    STROKE_400,
    STROKE_300,
    TEXT_100,
    TEXT_40,
    TEXT_60,
    TEXT_80,
)

# ── Legacy dialog styles (kept for compat, now tokenized) ──
DARK_DIALOG_STYLE = f"""
    QDialog {{ background-color: {BG_800}; color: {TEXT_100}; }}
    QLabel {{ color: {TEXT_100}; font-size: 12px; font-family: {FONT_FAMILY}; }}
    QPushButton {{ background-color: {BG_400}; color: {TEXT_100}; padding: 8px 16px; border-radius: {RADIUS_MD}px; border: {BORDER_W}px solid {STROKE_400}; font-family: {FONT_FAMILY}; }}
    QPushButton:hover {{ background-color: {BG_500}; }}
    QPushButton:pressed {{ background-color: {PRIMARY}; border-color: {PRIMARY}; }}
    QPushButton:disabled {{ background-color: {BG_600}; color: {TEXT_40}; border-color: {BG_400}; }}
    QPushButton:focus {{ border: 1px solid {FOCUS_PURPLE}; }}
"""

DARK_DIALOG_ACCENT_STYLE = f"""
    QDialog {{ background-color: {BG_800}; }}
    QLabel {{ color: {TEXT_100}; font-size: 13px; padding: 10px; font-family: {FONT_FAMILY}; }}
    QPushButton {{ 
        background-color: {PRIMARY}; color: {TEXT_100}; padding: 10px 30px; 
        border-radius: {RADIUS_MD}px; font-size: 13px; font-weight: bold; border: none;
        font-family: {FONT_FAMILY};
    }}
    QPushButton:hover {{ background-color: {PRIMARY_HOVER}; }}
    QPushButton:pressed {{ background-color: {BG_600}; }}
    QPushButton:disabled {{ background-color: {BG_600}; color: {TEXT_40}; }}
"""

DARK_METADATA_DIALOG_STYLE = f"""
    QDialog {{
        background-color: {BG_600};
    }}
    QLabel {{
        color: {TEXT_60};
        font-weight: bold;
        font-family: {FONT_FAMILY};
    }}
    QLineEdit {{
        background-color: {BG_400};
        color: {TEXT_100};
        border: {BORDER_W}px solid {STROKE_400};
        border-radius: {RADIUS_SM}px;
        padding: 5px;
        selection-background-color: {FOCUS_PURPLE};
        font-family: {FONT_FAMILY};
    }}
    QLineEdit:focus {{
        border: 1px solid {FOCUS_PURPLE};
    }}
    QLineEdit:disabled {{ background-color: {BG_600}; color: {TEXT_40}; }}
    QComboBox {{
        background-color: {BG_400};
        color: {TEXT_100};
        border: {BORDER_W}px solid {STROKE_400};
        border-radius: {RADIUS_SM}px;
        padding: 5px;
        font-family: {FONT_FAMILY};
    }}
    QComboBox:focus {{ border: 1px solid {FOCUS_PURPLE}; }}
    QComboBox:disabled {{ background-color: {BG_600}; color: {TEXT_40}; }}
    QComboBox::drop-down {{
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_400};
        color: {TEXT_100};
        selection-background-color: {FOCUS_PURPLE};
    }}
    QPushButton {{
        background-color: {BG_400};
        color: {TEXT_100};
        border: {BORDER_W}px solid {STROKE_300};
        border-radius: {RADIUS_MD}px;
        padding: 8px 15px;
        font-weight: bold;
        font-family: {FONT_FAMILY};
    }}
    QPushButton:hover {{
        background-color: {BG_500};
    }}
    QPushButton:pressed {{ background-color: {PRIMARY}; border-color: {PRIMARY}; }}
    QPushButton:disabled {{ background-color: {BG_600}; color: {TEXT_40}; border-color: {BG_400}; }}
    QPushButton:focus {{
        border: 1px solid {FOCUS_PURPLE};
    }}
"""

# Deprecated white-on-dark — kept for compat, do not use in new code
INPUT_FIELD_STYLE = (
    f"color: {TEXT_100}; background-color: {BG_400}; border: {BORDER_W}px solid {STROKE_400}; font-size: 10px; font-family: {FONT_FAMILY};"
)

# ── New global system (isolated, reversible) ─────────────────
# Applied once per window via setStyleSheet(APP_GLOBAL_QSS). Does NOT override per-widget inline
# QSS that is more specific, but normalizes base + states.

APP_GLOBAL_QSS = f"""
/* Base */
QWidget {{ font-family: {FONT_FAMILY}; }}
QMainWindow {{ background-color: {BG_900}; }}
QLabel {{ color: {TEXT_80}; font-family: {FONT_FAMILY}; }}
QToolBar {{ background-color: {BG_700}; border: none; border-bottom: 1px solid {STROKE_400}; padding: 2px; spacing: 4px; }}
QStatusBar {{ background-color: {BG_700}; color: {TEXT_60}; font-size: 9px; border-top: 1px solid {STROKE_400}; }}
QSplitter::handle {{ background-color: {STROKE_300}; border: 1px solid {STROKE_400}; }}
QSplitter::handle:hover {{ background-color: {PRIMARY}; }}

/* Buttons — 4 states + checked */
QPushButton {{
    background-color: {BG_400}; color: {TEXT_80}; border: {BORDER_W}px solid {STROKE_400};
    padding: 6px 12px; border-radius: {RADIUS_MD}px; font-weight: 600; font-family: {FONT_FAMILY};
}}
QPushButton:hover {{ background-color: {BG_500}; }}
QPushButton:pressed {{ background-color: {PRIMARY}; border-color: {PRIMARY}; color: {TEXT_100}; }}
QPushButton:checked {{ background-color: #00aa00; color: {TEXT_100}; border-color: #00aa00; }}
QPushButton:disabled {{ background-color: {BG_600}; color: {TEXT_40}; border-color: {BG_400}; }}
QPushButton:focus {{ border: 1px solid {FOCUS_PURPLE}; }}

/* Inputs — unified dark */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {BG_400}; color: {TEXT_100}; border: {BORDER_W}px solid {STROKE_400};
    border-radius: {RADIUS_SM}px; padding: 5px; selection-background-color: {FOCUS_PURPLE}; font-family: {FONT_FAMILY};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {FOCUS_PURPLE}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ background-color: {BG_600}; color: {TEXT_40}; }}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView, QListView {{
    background-color: {BG_400}; color: {TEXT_100}; selection-background-color: {FOCUS_PURPLE}; border: 1px solid {STROKE_400};
}}
QSlider::groove:horizontal {{ background: {BG_400}; height: 6px; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {PRIMARY}; width: 14px; height: 18px; margin: -6px 0; border-radius: 3px; border: 1px solid {STROKE_300}; }}
QSlider::groove:vertical {{ background: {BG_400}; width: 6px; border-radius: 3px; }}
QSlider::handle:vertical {{ background: {PRIMARY}; height: 14px; width: 18px; margin: 0 -6px; border-radius: 3px; border: 1px solid {STROKE_300}; }}
QSlider:disabled {{ opacity: 0.5; }}

/* Menus */
QMenu {{ background-color: {BG_500}; color: {TEXT_80}; border: 1px solid {STROKE_400}; padding: 4px; font-family: {FONT_FAMILY}; }}
QMenu::item {{ padding: 6px 20px; }}
QMenu::item:selected {{ background-color: {PRIMARY}; color: {TEXT_100}; }}
QMenu::item:disabled {{ color: {TEXT_40}; }}
QMenu::separator {{ height: 1px; background: {STROKE_400}; margin: 4px 8px; }}

/* Tables */
QTableWidget {{ background-color: {BG_800}; color: {TEXT_80}; gridline-color: {BG_600}; font-size: 10px; font-family: {FONT_FAMILY}; }}
QTableWidget::item:selected {{ background-color: #004a80; color: {TEXT_100}; }}
QHeaderView::section {{ background-color: {BG_600}; color: {TEXT_60}; padding: 4px 6px; font-size: 10px; font-weight: 600; border: none; border-right: 1px solid {BG_400}; border-bottom: 1px solid {STROKE_400}; font-family: {FONT_FAMILY}; }}
QHeaderView::section:checked {{ background-color: {BG_500}; }}

/* Progress / Scroll */
QProgressBar {{ background-color: {BG_800}; border: 1px solid {STROKE_400}; border-radius: 3px; text-align: center; font-size: 9px; color: {TEXT_80}; }}
QProgressBar::chunk {{ background-color: {PRIMARY}; border-radius: 2px; }}
QScrollBar:vertical {{ background: {BG_800}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BG_500}; border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {STROKE_300}; }}
"""

# Alias for window-specific apply
DARK_WINDOW_QSS = APP_GLOBAL_QSS
DARK_DJ_QSS = APP_GLOBAL_QSS  # DJ shares same global, extra per-panel overrides stay in perf_window_ui



def load_audio_devices_from_settings(settings, master_widgets=None, cue_widgets=None):
    """Load audio device settings and apply to widgets.

    Args:
        settings: SettingsManager instance
        master_widgets: List of widgets with setAudioDevice(dev) method
        cue_widgets: List of widgets with setAudioDevice(dev) or setCueAudioDevice(dev) method
    Returns:
        (master_dev, cue_dev) tuple of found devices
    """
    from services.audio_hardware_service import AudioHardwareService

    master_dev = None
    cue_dev = None

    master_id = settings.get("master_device_id")
    if master_id:
        master_dev = AudioHardwareService.find_device_by_id(master_id)
        if master_dev and master_widgets:
            for w in master_widgets:
                w.setAudioDevice(master_dev)

    cue_id = settings.get("cue_device_id")
    if cue_id:
        cue_dev = AudioHardwareService.find_device_by_id(cue_id)
        if cue_dev and cue_widgets:
            for w in cue_widgets:
                if hasattr(w, "setCueAudioDevice"):
                    w.setCueAudioDevice(cue_dev)
                else:
                    w.setAudioDevice(cue_dev)

    return master_dev, cue_dev
