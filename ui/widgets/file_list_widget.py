import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTableWidget

from core.cue_player import CUEFallbackPlayer
from ui.widgets.file_list_actions import FileListActionsMixin
from ui.widgets.file_list_columns import FileListColumnsMixin
from ui.widgets.file_list_data import FileListDataMixin

logger = logging.getLogger(__name__)


class FileListWidget(
    FileListColumnsMixin, FileListActionsMixin, FileListDataMixin, QTableWidget
):
    fileSelected = Signal(str)
    fileDeleted = Signal(str)
    fileMoved = Signal(str, str)
    addToPlaylist = Signal(str)
    addToCurrentList = Signal(str)
    addToDjMaster = Signal(str)
    createPlaylistAndAdd = Signal(str)
    fileDeleteRequested = Signal(str)
    fileMoveRequested = Signal(str)
    forceReadMetadataRequested = Signal(str)
    fingerprintRequested = Signal(str)
    batchFingerprintRequested = Signal(list)
    batchGenreChangeRequested = Signal(list)
    batchAddToDjMaster = Signal(list)
    ratingChanged = Signal(str, float)
    cuePreviewChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self.setColumnCount(11)
        self.setHorizontalHeaderLabels(
            [
                "CUE",
                "Artista",
                "Título",
                "Duración",
                "Rating",
                "Género",
                "Carpeta",
                "Archivo",
                "BR",
                "Tamaño",
                "BPM",
            ]
        )
        self.horizontalHeader().setVisible(True)
        self._added_paths = set()
        self._modified_rows = set()
        self._rating_widgets = {}
        self._cue_buttons = {}
        self._current_preview_path = None
        self._last_filters = None
        self._suppress_selection_signal = False
        self._setup_ui()
        cue_device_idx = self._get_cue_device_index()
        self._cue_player = CUEFallbackPlayer(device=cue_device_idx)
        self._cue_player.playbackStateChanged.connect(self._on_cue_state_changed)

    def _get_cue_device_index(self):
        try:
            from services.settings_manager import SettingsManager

            settings = SettingsManager()
            cue_id = settings.get("cue_device_id")
            logger.info(
                f"_get_cue_device_index: cue_id from settings = {cue_id} (type={type(cue_id).__name__})"
            )

            if not cue_id:
                return None

            if isinstance(cue_id, int):
                logger.info(
                    f"_get_cue_device_index: returning int device index = {cue_id}"
                )
                return cue_id

            if isinstance(cue_id, str):
                if cue_id.isdigit():
                    idx = int(cue_id)
                    logger.info(
                        f"_get_cue_device_index: returning device index = {idx}"
                    )
                    return idx

                import sounddevice as sd

                try:
                    all_devices = sd.query_devices()
                    if isinstance(all_devices, dict):
                        all_devices = [all_devices]
                    for i, dev in enumerate(all_devices):
                        dev_name = dev.get("name", "")
                        if cue_id in dev_name or dev_name in cue_id:
                            logger.info(
                                f"_get_cue_device_index: matched device {i}: {dev_name}"
                            )
                            return i
                except Exception as e:
                    logger.error(f"_get_cue_device_index: error searching devices: {e}")

        except Exception as e:
            logger.error(f"_get_cue_device_index: error = {e}")
        return None

    def setAudioDevice(self, device):
        if not device:
            return
        if hasattr(self, "_cue_player") and hasattr(self._cue_player, "setDevice"):
            try:
                idx = None
                if isinstance(device, dict):
                    backend = device.get("backend", "")
                    if backend == "sounddevice":
                        idx = device.get("index")
                    elif backend == "qtmultimedia":
                        pass
                    else:
                        idx = device.get("index")
                elif hasattr(device, "index"):
                    idx = device.index
                elif isinstance(device, int):
                    idx = device

                if idx is not None:
                    self._cue_player.setDevice(idx)
                    logger.info(
                        f"FileListWidget.setAudioDevice: configurado device index={idx}"
                    )
            except Exception as e:
                logger.warning(f"No se pudo configurar CUE device: {e}")
