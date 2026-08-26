import logging
import os
import typing

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QBrush, QColor

from ui.widgets.row_preview_player import RowPreviewPlayer

logger = logging.getLogger(__name__)

try:
    from PySide6.QtMultimedia import QMediaPlayer
except ImportError:
    QMediaPlayer = None


class PlaylistCUEMixin:
    def _get_cue_device_index(self):
        """Obtiene el índice del dispositivo CUE configurado en settings."""
        try:
            from services.settings_manager import SettingsManager

            settings = SettingsManager()
            cue_id = settings.get("cue_device_id")
            logger.info(
                f"_get_cue_device_index: cue_id from settings = {cue_id} (type={type(cue_id).__name__})"
            )

            if cue_id is None:
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

        if hasattr(self, "cue_output") and self.cue_output:
            try:
                if isinstance(device, dict):
                    backend = device.get("backend", "")
                    if backend == "qtmultimedia" and "device_obj" in device:
                        self.cue_output.setDevice(device["device_obj"])
                    elif backend == "sounddevice":
                        pass
                    elif "device_obj" in device:
                        self.cue_output.setDevice(device["device_obj"])
                else:
                    self.cue_output.setDevice(device)
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"No se pudo configurar dispositivo de audio: {e}"
                )

        if hasattr(self, "cue_player") and hasattr(self.cue_player, "setDevice"):
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
                    self.cue_player.setDevice(idx)
                    logger.info(
                        f"PlaylistWidget.setAudioDevice: configurado device index={idx}"
                    )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"No se pudo configurar CUE device: {e}"
                )

    def _on_cue_clicked(self, row, path):
        current_row = (
            self._find_row_by_filepath(path) if self.table.isSortingEnabled() else row
        )

        if (
            self._current_preview_row == current_row
            and self._current_preview_path == path
        ):
            self.stop_cue()
        else:
            self.cuePlayStarted.emit()

            if self._current_preview_row >= 0:
                self._reset_row_highlight(self._current_preview_row)
            self._current_preview_row = current_row
            self._current_preview_path = path
            for c in range(self.table.columnCount()):
                it = self.table.item(current_row, c)
                if it:
                    it.setBackground(QColor(0, 100, 120))
            w = self.table.cellWidget(current_row, 1)
            if w:
                rpp = typing.cast("RowPreviewPlayer", w)
                rpp.btn_cue.setChecked(True)
            self.cue_player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            self.cue_player.play()

    def stop_cue(self):
        """Detiene la preescucha CUE."""
        if self._current_preview_row >= 0:
            self._reset_row_highlight(self._current_preview_row)
            self._current_preview_row = -1
            self._current_preview_path = None
        if self.cue_player:
            self.cue_player.stop()
        self.cue_progress.setValue(0)

    def _find_row_by_filepath(self, filepath):
        """Encuentra la fila actual que contiene el archivo (teniendo en cuenta ordenación)."""
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 4)
            if it and it.data(Qt.ItemDataRole.UserRole) == filepath:
                return r
        return -1

    def _reset_row_highlight(self, row):
        if row < 0 or row >= self.table.rowCount():
            return
        for c in range(self.table.columnCount()):
            it = self.table.item(row, c)
            if it:
                it.setBackground(QBrush(Qt.BrushStyle.NoBrush))
        w = self.table.cellWidget(row, 1)
        if w:
            rpp = typing.cast("RowPreviewPlayer", w)
            rpp.btn_cue.setChecked(False)
        self.cue_progress.setValue(0)

    def _update_preview_progress(self):
        if not self.cue_player:
            return

        is_playing = False
        try:
            is_playing = self.cue_player.playbackState() == 1
        except Exception:
            try:
                is_playing = (
                    self.cue_player.playbackState()
                    == QMediaPlayer.PlaybackState.PlayingState
                )
            except Exception:
                pass

        if is_playing:
            try:
                dur = self.cue_player.duration()
                if dur and dur > 0:
                    pos = self.cue_player.position()
                    if pos and dur:
                        self.cue_progress.setValue(int((pos / dur) * 100))
            except Exception:
                pass
        elif self._current_preview_row >= 0:
            try:
                if self.cue_player.playbackState() != 1:
                    try:
                        self.cue_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                    except Exception:
                        pass
                    if self._current_preview_row >= 0:
                        self._reset_row_highlight(self._current_preview_row)
                        self._current_preview_row = -1
                        self.cue_progress.setValue(0)
            except Exception:
                pass
