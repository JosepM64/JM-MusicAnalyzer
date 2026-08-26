import logging

from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class PlaylistSortingMixin:
    def _on_sort_changed(self, logicalIndex, order):
        if self._sorting_in_progress:
            return
        if self.is_master:
            self._sort_master_playlist(logicalIndex, order)
            return

        if not self.filtered_tracks:
            return

        column_keys = {
            1: lambda t: t.get("filepath", ""),
            2: lambda t: self.play_counts_manager.get(t.get("filepath", "")),
            3: lambda t: t.get("artist", "").lower(),
            4: lambda t: t.get("title", "").lower(),
            5: lambda t: t.get("duration", 0),
            6: lambda t: t.get("genre", "").lower(),
            7: lambda t: t.get("rating", 0),
        }

        if logicalIndex not in column_keys:
            return

        self._sorting_in_progress = True
        try:
            self.table.setSortingEnabled(False)
            key_func = column_keys[logicalIndex]
            reverse = order == Qt.SortOrder.DescendingOrder
            self.filtered_tracks.sort(key=key_func, reverse=reverse)
            self._update_table_page()
            self.table.horizontalHeader().setSortIndicator(logicalIndex, order)
        finally:
            self.table.setSortingEnabled(True)
            self._sorting_in_progress = False

    def _get_sort_value(self, row, column):
        item = self.table.item(row, column)
        if not item:
            return ""
        if column == 0:
            val = item.data(Qt.ItemDataRole.UserRole)
            return int(val) if val is not None else 0
        if column == 5:
            text = item.text()
            if ":" in text:
                parts = text.split(":")
                try:
                    return int(parts[0]) * 60 + int(parts[1])
                except ValueError:
                    return 0
            return 0
        if column == 7:
            return item.text().count("★")
        if column == 9:
            text = item.text()
            try:
                return int(text)
            except ValueError:
                return -1
        elif column == 10:
            text = item.text()
            if text.endswith("M"):
                try:
                    return float(text[:-1])
                except ValueError:
                    return -1
            return -1
        else:
            return item.text().lower()

    def _sort_master_playlist(self, column, order):
        reverse = order == Qt.SortOrder.DescendingOrder

        rows_data = []
        for r in range(self.table.rowCount()):
            path_item = self.table.item(r, 4)
            if not path_item:
                continue
            filepath = path_item.data(Qt.ItemDataRole.UserRole) or ""
            sort_val = self._get_sort_value(r, column)
            rows_data.append((sort_val, filepath))

        if not rows_data:
            return

        rows_data.sort(key=lambda x: x[0], reverse=reverse)

        self._sorting_in_progress = True
        try:
            self.table.setSortingEnabled(False)
            sorted_paths = [fp for _, fp in rows_data]
            self.table.setRowCount(0)
            self._batch_adding = True
            for i, fp in enumerate(sorted_paths, 1):
                self.add_track(fp, silent=True, skip_file_read=True, playlist_order=i)
            self._batch_adding = False
            self.table.horizontalHeader().setSortIndicator(column, order)
        finally:
            self.table.setSortingEnabled(True)
            self._sorting_in_progress = False
