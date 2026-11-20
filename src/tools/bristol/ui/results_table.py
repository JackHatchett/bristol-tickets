"""ui/results_table.py — the Search and Archive results, as a sortable table.

One row per record, a header per fact, sorted by clicking a header the way a
Finder or Mail list is. Each cell carries a sort key beside what it shows, so
the number column sorts as numbers and a date sorts as the moment it names
whatever format it is drawn in.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

SORT_ROLE = Qt.ItemDataRole.UserRole + 7
RECORD_ROLE = Qt.ItemDataRole.UserRole


class _Cell(QTableWidgetItem):
    """A cell that sorts by its key rather than by the text it shows."""

    def __lt__(self, other) -> bool:
        mine, theirs = self.data(SORT_ROLE), other.data(SORT_ROLE)
        if mine is None or theirs is None or type(mine) is not type(theirs):
            return str(self.text()).lower() < str(other.text()).lower()
        return mine < theirs


class ResultsTable(QTableWidget):
    """Rows of (cells, record). A cell is its text, or (text, sort key); the
    record is the (id, kind) a click hands on."""

    picked = Signal(int, str)  # a single click: inspect it
    opened = Signal(int, str)  # a double click: edit it

    def __init__(self, headers: list[str], stretch: int, parent=None) -> None:
        super().__init__(0, len(headers), parent)
        self.setObjectName("resultsTable")
        self.setHorizontalHeaderLabels(headers)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for column in range(len(headers)):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.Stretch
                if column == stretch
                else QHeaderView.ResizeMode.ResizeToContents,
            )
        # No column is sorted until one is clicked, so the rows open in the
        # order the view loads them in: newest-archived first on the Archive.
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.setSortingEnabled(True)
        self.cellClicked.connect(lambda row, _c: self._emit(self.picked, row))
        self.cellDoubleClicked.connect(lambda row, _c: self._emit(self.opened, row))

    def set_rows(self, rows) -> None:
        """Replace every row, keeping the column the user last sorted by."""
        header = self.horizontalHeader()
        sorted_by = header.sortIndicatorSection()
        order = header.sortIndicatorOrder()
        self.setSortingEnabled(False)
        self.setRowCount(0)
        for cells, record in rows:
            row = self.rowCount()
            self.insertRow(row)
            for column, cell in enumerate(cells):
                text, key = cell if isinstance(cell, tuple) else (cell, None)
                item = _Cell(str(text))
                item.setData(SORT_ROLE, key)
                item.setData(RECORD_ROLE, record)
                self.setItem(row, column, item)
        self.setSortingEnabled(True)
        if 0 <= sorted_by < self.columnCount() and header.isSortIndicatorShown():
            self.sortItems(sorted_by, order)

    def count(self) -> int:
        return self.rowCount()

    def row_text(self, row: int) -> str:
        """A row's cells read left to right, for a reader that wants the line."""
        return "   ".join(
            self.item(row, c).text()
            for c in range(self.columnCount())
            if self.item(row, c) is not None
        )

    def _emit(self, signal, row: int) -> None:
        item = self.item(row, 0)
        record = item.data(RECORD_ROLE) if item is not None else None
        if record:
            signal.emit(record[0], record[1])


def magnifier_icon(colour: str, size: int = 16) -> QIcon:
    """The search field's leading glass: Lucide's search, drawn in ``colour``."""
    from .icons import icon

    return icon("search", colour, size)
