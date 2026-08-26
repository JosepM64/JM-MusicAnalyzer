import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox, QTableWidgetItem

from ui.widgets.row_preview_player import RowPreviewPlayer

logger = logging.getLogger(__name__)


class PlaylistTableOpsMixin:
    def _refresh_all_widgets(self):
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 4)
            if it:
                p = it.data(Qt.ItemDataRole.UserRole)
                w = RowPreviewPlayer(p)
                w.cueClicked.connect(
                    lambda p_path, row_idx=r: self._on_cue_clicked(row_idx, p_path)
                )
                if r == self._current_preview_row:
                    w.btn_cue.setChecked(True)
                self.table.setCellWidget(r, 1, w)
        self._update_row_numbers()

    def _update_row_numbers(self):
        for r in range(self.table.rowCount()):
            num_item = QTableWidgetItem(f"{r + 1:02d}")
            num_item.setData(Qt.ItemDataRole.UserRole, r + 1)
            self.table.setItem(r, 0, num_item)

    def remove_top_track(self):
        if self.table.rowCount() > 0:
            if self._current_preview_row == 0:
                self.cue_player.stop()
                self._reset_row_highlight(0)
                self._current_preview_row = -1
            elif self._current_preview_row > 0:
                self._current_preview_row -= 1
            self.table.removeRow(0)
            self._refresh_all_widgets()

    def _remove_row(self, row):
        """Elimina una fila y actualiza el highlight de CUE."""
        if row < 0 or row >= self.table.rowCount():
            return
        if self._current_preview_row == row:
            self.cue_player.stop()
            self._reset_row_highlight(row)
            self._current_preview_row = -1
        elif self._current_preview_row > row:
            self._current_preview_row -= 1
        self.table.removeRow(row)
        self._modified = True
        self._refresh_all_widgets()
        if not self.is_master:
            self._rebuild_all_tracks_from_table()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._remove_selected_rows()
        else:
            super().keyPressEvent(event)

    def _remove_selected_rows(self):
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
        for row in sorted(rows, reverse=True):
            self._remove_row(row)

    def _clear_all(self):
        if self.table.rowCount() == 0:
            return
        reply = QMessageBox.question(
            self,
            "Vaciar lista",
            f"Eliminar las {self.table.rowCount()} pistas de la lista?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._current_preview_row >= 0:
                self.cue_player.stop()
                self._current_preview_row = -1
            self.table.setRowCount(0)
            self._modified = True
            self._refresh_all_widgets()
            if not self.is_master:
                self._rebuild_all_tracks_from_table()

    def _swap_rows(self, row1, row2):
        if (
            row1 == row2
            or row1 < 0
            or row2 < 0
            or row1 >= self.table.rowCount()
            or row2 >= self.table.rowCount()
        ):
            return
        sorting_was_enabled = self.table.isSortingEnabled()
        if sorting_was_enabled:
            self.table.setSortingEnabled(False)
        if self._current_preview_row == row1:
            self._current_preview_row = row2
        elif self._current_preview_row == row2:
            self._current_preview_row = row1
        items1 = [
            self.table.takeItem(row1, col) for col in range(self.table.columnCount())
        ]
        items2 = [
            self.table.takeItem(row2, col) for col in range(self.table.columnCount())
        ]
        for col, item in enumerate(items1):
            self.table.setItem(row2, col, item)
        for col, item in enumerate(items2):
            self.table.setItem(row1, col, item)
        widget1 = self.table.cellWidget(row1, 1)
        widget2 = self.table.cellWidget(row2, 1)
        if widget1:
            self.table.removeCellWidget(row1, 1)
            assert isinstance(widget1, RowPreviewPlayer)
            path = widget1.filepath
            new_widget1 = RowPreviewPlayer(path)
            new_widget1.cueClicked.connect(
                lambda p_path, row_idx=row2: self._on_cue_clicked(row_idx, p_path)
            )
            self.table.setCellWidget(row2, 1, new_widget1)
        if widget2:
            self.table.removeCellWidget(row2, 1)
            assert isinstance(widget2, RowPreviewPlayer)
            path = widget2.filepath
            new_widget2 = RowPreviewPlayer(path)
            new_widget2.cueClicked.connect(
                lambda p_path, row_idx=row1: self._on_cue_clicked(row_idx, p_path)
            )
            self.table.setCellWidget(row1, 1, new_widget2)
        self._refresh_all_widgets()
        if sorting_was_enabled:
            self.table.setSortingEnabled(True)
        self._modified = True

    def _move_row_up(self, row):
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self._update_row_numbers()

    def _move_row_down(self, row):
        if row >= self.table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self._update_row_numbers()

    def _move_to_position(self, row):
        current = row + 1
        max_pos = self.table.rowCount()
        new_pos, ok = QInputDialog.getInt(
            self,
            "Mover a posición",
            f"Posición actual: {current}\nNueva posición (1-{max_pos}):",
            current,
            1,
            max_pos,
            1,
        )
        if not ok or new_pos == current:
            return
        if new_pos < current:
            for i in range(row, new_pos - 1, -1):
                self._swap_rows(i, i - 1)
        else:
            for i in range(row, new_pos - 1):
                self._swap_rows(i, i + 1)
        self._update_row_numbers()
