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

        # DESIGN.md §8 — tokenized header/row (BG_500 flat dark, PRIMARY 28% #004a80 selected)
        try:
            from ui.tokens import BG_500, BG_600, PRIMARY, STROKE_400, TEXT_100, TEXT_80

            self.setStyleSheet(f"""
            QTableWidget {{ background-color: {BG_500}; color: {TEXT_80}; gridline-color: {BG_600}; border: 1px solid {STROKE_400}; font-size: 10px; selection-color: {TEXT_100}; font-family: 'Segoe UI', sans-serif; }}
            QTableWidget::item {{ padding: 1px 2px; border: none; }}
            QTableWidget::item:selected {{ background-color: #004a80; color: {TEXT_100}; }}
            QTableWidget::item:hover {{ background-color: #3a3a3a; }}
            QHeaderView::section {{ background-color: {BG_600}; color: {TEXT_100}; padding: 4px 6px; border: none; border-right: 1px solid {STROKE_400}; border-bottom: 2px solid {PRIMARY}; font-weight: 600; font-size: 10px; font-family: 'Segoe UI', sans-serif; }}
            QHeaderView {{ background-color: {BG_600}; border: none; }}
        """)
        except Exception:
            self.setStyleSheet("""
            QTableWidget { background-color: #2b2b2b; color: #e0e0e0; gridline-color: #333; border: 1px solid #444; font-size: 10px; selection-color: white; }
            QTableWidget::item { padding: 1px 2px; border: none; }
            QTableWidget::item:selected { background-color: #004a80; color: white; }
            QTableWidget::item:hover { background-color: #3a3a3a; }
            QHeaderView::section { background-color: #252525; color: #ffffff; padding: 4px 6px; border: none; border-right: 1px solid #444; border-bottom: 2px solid #0078d4; font-weight: 600; font-size: 10px; }
            QHeaderView { background-color: #252525; border: none; }
        """)
        self.verticalHeader().setDefaultSectionSize(18)

    def _on_item_clicked(self, item):
        if item:
            row = item.row()
            filepath = self._get_path_at_row(row)
            if filepath:
                self.fileSelected.emit(filepath)

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
