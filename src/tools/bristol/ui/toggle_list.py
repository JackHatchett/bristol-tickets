"""ui/toggle_list.py — a list where any number of rows can be chosen, each row a
rounded toggle of its own rather than a row with a checkbox in it.

A chosen row takes the selection fill, a 1 px accent edge and a check mark at
its right end; an unchosen row takes none of the three, and the hover fill
under the pointer. A click anywhere on a row, or Space on the current row,
turns it over. Each item's state is its ``Qt.CheckStateRole``, so a caller
reads and sets it as it would a checkable item.

The styling contract these draw against is ``ui/README.md``; the design
system's Bristol Controls page gives the Toggle Row.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
)

from . import icons
from .theme import C, radius, space

CHECK_SIZE = 14


def _chosen(index) -> bool:
    state = index.data(Qt.ItemDataRole.CheckStateRole)
    return state in (Qt.CheckState.Checked, Qt.CheckState.Checked, 2)


DETAIL_ROLE = Qt.ItemDataRole.UserRole + 1


class _ToggleRowDelegate(QStyledItemDelegate):
    """Paints one toggle row, with its detail line under its text where it has
    one, and turns it over on a click."""

    def __init__(self, view: QListWidget) -> None:
        super().__init__(view)
        self._view = view

    def _text_width(self, option) -> int:
        width = option.rect.width() or self._view.viewport().width()
        return max(1, width - 2 * space("lg") - CHECK_SIZE - space("md"))

    def _detail_rect(self, option, index, width: int) -> QRect:
        detail = index.data(DETAIL_ROLE)
        if not detail:
            return QRect()
        return option.fontMetrics.boundingRect(
            QRect(0, 0, width, 10_000), Qt.TextFlag.TextWordWrap, str(detail)
        )

    def sizeHint(self, option, index) -> QSize:
        line = option.fontMetrics.height()
        detail = self._detail_rect(option, index, self._text_width(option))
        extra = detail.height() + space("xs") if detail.height() else 0
        return QSize(option.rect.width(), line + extra + 2 * space("md"))

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        chosen = _chosen(index)
        enabled = bool(index.flags() & Qt.ItemFlag.ItemIsEnabled)
        turnable = enabled and bool(index.flags() & Qt.ItemFlag.ItemIsUserCheckable)
        rect = QRectF(option.rect).adjusted(0.5, 1.5, -0.5, -1.5)
        corner = radius("md")
        if chosen:
            painter.setPen(QPen(QColor(C["ACCENT"]), 1))
            painter.setBrush(QColor(C["SEL_BG"]))
            painter.drawRoundedRect(rect, corner, corner)
        elif turnable and option.state & QStyle.StateFlag.State_MouseOver:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(C["HOVER_BG"]))
            painter.drawRoundedRect(rect, corner, corner)

        width = self._text_width(option)
        left = rect.left() + space("lg")
        top = rect.top() + space("md") - 1.5
        line = option.fontMetrics.height()
        if not turnable and not chosen:
            color = C["INK_FAINT"]
        elif chosen:
            color = C["ACCENT_DK"]
        else:
            color = C["INK"]
        painter.setFont(option.font)
        painter.setPen(QColor(color))
        text = option.fontMetrics.elidedText(
            str(index.data(Qt.ItemDataRole.DisplayRole) or ""), Qt.TextElideMode.ElideRight, width
        )
        painter.drawText(
            QRectF(left, top, width, line),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            text,
        )
        detail = index.data(DETAIL_ROLE)
        if detail:
            box = self._detail_rect(option, index, width)
            painter.setPen(QColor(C["INK_SOFT"]))
            painter.drawText(
                QRectF(left, top + line + space("xs"), width, box.height()),
                Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                str(detail),
            )

        if chosen:
            mark = icons.pixmap("check", C["ACCENT"], CHECK_SIZE)
            x = rect.right() - space("lg") - CHECK_SIZE
            y = top + (line - CHECK_SIZE) / 2
            painter.drawPixmap(QRectF(x, y, CHECK_SIZE, CHECK_SIZE), mark, QRectF(mark.rect()))
        painter.restore()

    def editorEvent(self, event, model, option, index) -> bool:
        if not (
            index.flags() & Qt.ItemFlag.ItemIsEnabled
            and index.flags() & Qt.ItemFlag.ItemIsUserCheckable
        ):
            return False
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
            and option.rect.contains(event.position().toPoint())
        ):
            self._turn(model, index)
            return True
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
            return event.button() == Qt.MouseButton.LeftButton
        if event.type() == QEvent.Type.KeyPress and event.key() in (
            Qt.Key.Key_Space,
            Qt.Key.Key_Select,
        ):
            self._turn(model, index)
            return True
        return False

    @staticmethod
    def _turn(model, index) -> None:
        model.setData(
            index,
            Qt.CheckState.Unchecked if _chosen(index) else Qt.CheckState.Checked,
            Qt.ItemDataRole.CheckStateRole,
        )


class ToggleList(QListWidget):
    """A list of toggle rows. ``add(text, chosen)`` adds one that can be turned
    over, its key ``key`` or its text; ``add_note(text)`` adds a row that only
    says something. ``turned`` carries a row's key and whether it is now
    chosen, whenever its state changes."""

    turned = Signal(str, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("toggleList")
        self.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.setMouseTracking(True)
        self.setSpacing(0)
        self.setItemDelegate(_ToggleRowDelegate(self))
        # A row's detail wraps to the list's width, so a new width is a new
        # height for every row.
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.itemChanged.connect(self._changed)

    def _changed(self, item: QListWidgetItem) -> None:
        if item.data(Qt.ItemDataRole.CheckStateRole) is not None:
            self.turned.emit(self.key(item), item.checkState() == Qt.CheckState.Checked)

    @staticmethod
    def key(item: QListWidgetItem) -> str:
        return item.data(Qt.ItemDataRole.UserRole) or item.text()

    def find(self, key: str) -> QListWidgetItem | None:
        for i in range(self.count()):
            if self.key(self.item(i)) == key:
                return self.item(i)
        return None

    def is_chosen(self, key: str) -> bool:
        item = self.find(key)
        return item is not None and item.checkState() == Qt.CheckState.Checked

    def set_chosen(self, key: str, chosen: bool, quietly: bool = False) -> None:
        item = self.find(key)
        if item is None:
            return
        was = self.blockSignals(quietly)
        try:
            item.setCheckState(Qt.CheckState.Checked if chosen else Qt.CheckState.Unchecked)
        finally:
            self.blockSignals(was)

    def chosen_keys(self) -> list[str]:
        return [
            self.key(self.item(i))
            for i in range(self.count())
            if self.item(i).checkState() == Qt.CheckState.Checked
        ]

    def fit_rows(self, most: int = 8) -> None:
        """As tall as its rows, up to ``most`` of them."""
        rows = max(1, min(self.count(), most))
        margins = self.contentsMargins()
        self.setFixedHeight(
            rows * self.sizeHintForRow(0) + margins.top() + margins.bottom() + 2 * self.frameWidth()
        )

    def add(
        self, text: str, chosen: bool, key: str = "", detail: str = "", locked: bool = False
    ) -> QListWidgetItem:
        """A row reading ``text``, with ``detail`` under it where given. A
        ``locked`` row shows its state and cannot be turned over."""
        item = QListWidgetItem(text)
        if key:
            item.setData(Qt.ItemDataRole.UserRole, key)
        if detail:
            item.setData(DETAIL_ROLE, detail)
        item.setCheckState(Qt.CheckState.Checked if chosen else Qt.CheckState.Unchecked)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            if locked
            else Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
        )
        self.addItem(item)
        return item

    def add_note(self, text: str) -> QListWidgetItem:
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.addItem(item)
        return item

    def chosen(self) -> list[str]:
        return [
            self.item(i).text()
            for i in range(self.count())
            if self.item(i).checkState() == Qt.CheckState.Checked
        ]
