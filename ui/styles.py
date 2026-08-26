DARK_DIALOG_STYLE = """
    QDialog { background-color: #1a1a1a; color: #ffffff; }
    QLabel { color: #ffffff; font-size: 12px; }
    QPushButton { background-color: #444; color: white; padding: 8px 16px; border-radius: 4px; }
    QPushButton:hover { background-color: #555; }
"""

DARK_DIALOG_ACCENT_STYLE = """
    QDialog { background-color: #1a1a1a; }
    QLabel { color: #ffffff; font-size: 13px; padding: 10px; }
    QPushButton { 
        background-color: #0078d4; color: white; padding: 10px 30px; 
        border-radius: 4px; font-size: 13px; font-weight: bold;
    }
    QPushButton:hover { background-color: #1084d8; }
"""

DARK_METADATA_DIALOG_STYLE = """
    QDialog {
        background-color: #252525;
    }
    QLabel {
        color: #cccccc;
        font-weight: bold;
    }
    QLineEdit {
        background-color: #333;
        color: white;
        border: 1px solid #444;
        border-radius: 3px;
        padding: 5px;
        selection-background-color: #6a1b9a;
    }
    QLineEdit:focus {
        border: 1px solid #6a1b9a;
    }
    QComboBox {
        background-color: #333;
        color: white;
        border: 1px solid #444;
        border-radius: 3px;
        padding: 5px;
    }
    QComboBox::drop-down {
        border: none;
    }
    QComboBox QAbstractItemView {
        background-color: #333;
        color: white;
        selection-background-color: #6a1b9a;
    }
    QPushButton {
        background-color: #444;
        color: white;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 8px 15px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #555;
    }
    QPushButton:focus {
        border: 1px solid #6a1b9a;
    }
"""

INPUT_FIELD_STYLE = (
    "color: #000; background-color: #fff; border: 1px solid #ccc; font-size: 10px;"
)


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
