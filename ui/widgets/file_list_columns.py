import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView

logger = logging.getLogger(__name__)


class FileListColumnsMixin:
    """Column setup, column widths, header configuration."""

    def _setup_ui(self):
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.horizontalHeader().setVisible(True)

        self.itemClicked.connect(self._on_item_clicked)
        self.verticalHeader().sectionClicked.connect(self._on_header_clicked)

        self.setSortingEnabled(True)
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(4, 65)
        self.horizontalHeader().sortIndicatorChanged.connect(
            self._on_sort_indicator_changed
        )

        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setDragEnabled(True)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        for col in range(1, 11):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

        self.setColumnWidth(0, 40)
        self.setColumnWidth(1, 160)
        self.setColumnWidth(2, 190)
        self.setColumnWidth(3, 50)
        self.setColumnWidth(4, 65)
        self.setColumnWidth(5, 80)
        self.setColumnWidth(6, 250)
        self.setColumnWidth(7, 180)
        self.setColumnWidth(8, 55)
        self.setColumnWidth(9, 70)
        self.setColumnWidth(10, 45)

        self.itemSelectionChanged.connect(self._on_selection_changed)

        self.setStyleSheet("""
            QTableWidget { background-color: #2b2b2b; color: #e0e0e0; gridline-color: #333; border: 1px solid #444; font-size: 10px; selection-color: white; }
            QTableWidget::item { padding: 1px 2px; border: none; }
            QTableWidget::item:selected { background-color: #0078d4; color: white; }
            QTableWidget::item:hover { background-color: #3a3a3a; }
            QTableWidget::item:selected:hover { background-color: #0078d4; }
            QHeaderView::section { background-color: #333333; color: #ffffff; padding: 4px 8px; border: none; border-right: 1px solid #555; border-bottom: 2px solid #0078d4; font-weight: bold; font-size: 11px; }
            QHeaderView { background-color: #333333; border: none; }
        """)
        self.verticalHeader().setDefaultSectionSize(15)

    def _on_item_clicked(self, item):
        if item:
            row = item.row()
            filepath = self._get_path_at_row(row)
            if filepath:
                self.fileSelected.emit(filepath)

    def _on_header_clicked(self, logicalIndex):
        pass

    def _on_sort_indicator_changed(self, logicalIndex, order):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._reposition_cell_widgets)

    def _reposition_cell_widgets(self):
        self.setUpdatesEnabled(False)
        for row in range(self.rowCount()):
            filepath = self._get_path_at_row(row)
            if not filepath:
                continue
            btn = self._cue_buttons.get(filepath)
            if btn:
                self.setCellWidget(row, 0, btn)
            rw = self._rating_widgets.get(filepath)
            if rw:
                self.setCellWidget(row, 4, rw)
        self.setUpdatesEnabled(True)
