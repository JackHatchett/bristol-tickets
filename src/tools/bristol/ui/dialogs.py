"""ui/dialogs.py — the app's confirmations and notices, in the design system.

One modal shape, built from the tokens in ``theme.py``: a titled window, a
heading, a body, and buttons at the app's own ranks. Every yes/no question and
every notice in Bristol Tickets comes from here, so none of them arrives as the
platform's own message box with its question glyph and its foreign buttons.

The styling contract these draw against is ``ui/README.md``.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import LAYOUT, space

# The three ranks a button in this app carries. A confirmation names the rank of
# the action it is confirming; the way out of the dialog is always ordinary.
PRIMARY = "globalCreateBtn"
DESTRUCTIVE = "deleteBtn"
ORDINARY = ""


def as_sheet(dialog: QDialog) -> bool:
    """Open ``dialog`` as a sheet on its parent's window, where the platform has
    sheets: it drops from that window's title bar and holds that window alone.
    Returns whether it is one.

    A sheet has no title bar, so its title is the heading inside it; a dialog
    in a window of its own carries its title in the title bar and no heading.
    Call before the dialog is shown.
    """
    if sys.platform != "darwin" or dialog.parentWidget() is None:
        return False
    dialog.setWindowFlag(Qt.Sheet, True)
    dialog.setWindowModality(Qt.WindowModal)
    return True


def add_button(label: str, on_add, tip: str = "") -> QPushButton:
    """The one secondary button under an editable list, saying what it adds —
    Add Folder, Add Link. Sized to its words and placed at the list's left
    edge by the caller."""
    button = QPushButton(label)
    button.setAutoDefault(False)
    if tip:
        button.setToolTip(tip)
    button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    button.clicked.connect(lambda _checked=False: on_add())
    return button


def remove_icon(tip: str, on_remove) -> QPushButton:
    """The Quiet Icon ✕ at the end of an editable list's row, which removes
    that row."""
    from . import icons

    button = QPushButton()
    button.setObjectName("quietIcon")
    icons.tint(button, "x")
    button.setFixedWidth(space("2xl"))
    button.setToolTip(tip)
    button.setAccessibleName(tip)
    button.setAutoDefault(False)
    button.clicked.connect(lambda _checked=False: on_remove())
    return button


def removable_item(view: QListWidget, item: QListWidgetItem, tip: str,
                   on_remove, content: QWidget | None = None) -> QWidget:
    """End a list item's row in its ✕. ``content`` is drawn before the ✕ where
    the row is a widget; where it is ``None`` the list draws the item's text,
    selection and hover as before, under a row that carries only the ✕."""
    holder = QWidget()
    holder.setObjectName("removableRow")
    line = QHBoxLayout(holder)
    line.setContentsMargins(space("sm"), 0, space("xs"), 0)
    line.setSpacing(space("sm"))
    if content is None:
        line.addStretch(1)
    else:
        line.addWidget(content, 1)
    line.addWidget(remove_icon(tip, on_remove), 0, Qt.AlignVCenter)
    holder.ensurePolished()
    # A row the list draws keeps the padding the style sheet gives its items,
    # which an item with a size of its own no longer asks the style for.
    padded = QSize(0, view.fontMetrics().height() + 2 * space("md"))
    hint = item.sizeHint()
    if not hint.isValid():
        hint = padded if content is None else QSize(0, 0)
    item.setSizeHint(hint.expandedTo(holder.sizeHint()).expandedTo(
        padded if content is None else QSize(0, 0)))
    view.setItemWidget(item, holder)
    return holder


class RowList(QFrame):
    """An editable list whose rows are widgets: one rounded well with the edge
    every list carries, each row ending in the ✕ that removes it. A list that
    lists nothing is not drawn."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("rowList")
        # As tall as its rows, whatever its host is short of: a squeezed list
        # would draw one row over the next.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._rows = QVBoxLayout(self)
        self._rows.setContentsMargins(space("sm"), space("sm"), space("sm"),
                                      space("sm"))
        self._rows.setSpacing(space("xs"))
        self.setVisible(False)

    def add_row(self, content: QWidget, tip: str, on_remove,
                align=Qt.AlignVCenter) -> QWidget:
        row = QWidget()
        # A row is as tall as its contents, whatever its host is short of.
        row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(space("md"))
        line.addWidget(content, 1)
        line.addWidget(remove_icon(tip, on_remove), 0, align)
        self._rows.addWidget(row)
        self.setVisible(True)
        return row

    def remove_row(self, row: QWidget) -> None:
        self._rows.removeWidget(row)
        row.deleteLater()
        self.setVisible(self.count() > 0)

    def count(self) -> int:
        return self._rows.count()

    def row(self, index: int) -> QWidget | None:
        item = self._rows.itemAt(index)
        return item.widget() if item is not None else None

    def clear(self) -> None:
        while self._rows.count():
            item = self._rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.setVisible(False)


class Modal(QDialog):
    """A titled question or notice with its buttons on one row.

    ``buttons`` is a list of ``(label, rank, result)`` in the order they are
    drawn, left to right. ``default_index`` names the one Return presses, and
    ``escape_index`` the one whose result closing the window or pressing Esc
    returns, the default's unless given.
    """

    def __init__(self, parent, title: str, body: str,
                 buttons: list[tuple[str, str, object]],
                 default_index: int = 0,
                 escape_index: int | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["small_dialog_min_w"])
        if escape_index is None:
            escape_index = default_index
        self._result: object = buttons[escape_index][2] if buttons else None

        heading = QLabel(title)
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)
        heading.setVisible(as_sheet(self))

        text = QLabel(body)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addStretch(1)
        for index, (label, rank, result) in enumerate(buttons):
            button = QPushButton(label)
            if rank:
                button.setObjectName(rank)
            button.setAutoDefault(False)
            button.setDefault(index == default_index)
            button.clicked.connect(
                lambda _checked=False, value=result: self._choose(value)
            )
            row.addWidget(button)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("lg"))
        column.addWidget(heading)
        column.addWidget(text)
        column.addSpacing(space("md"))
        column.addLayout(row)

    def _choose(self, value: object) -> None:
        self._result = value
        self.accept()

    def choice(self) -> object:
        """The result of the button that closed the dialog."""
        return self._result


def confirm(parent, title: str, body: str, accept_label: str,
            cancel_label: str = "Cancel", destructive: bool = False) -> bool:
    """Ask a yes/no question. True when the user chose to go ahead.

    The action's button, at the right, carries the destructive rank where what
    it does cannot be undone and the primary rank otherwise. Return presses the
    action unless it is destructive, when Return presses the way out; Esc and
    the title-bar close always land on the way out.
    """
    dialog = Modal(parent, title, body, [
        (cancel_label, ORDINARY, False),
        (accept_label, DESTRUCTIVE if destructive else PRIMARY, True),
    ], default_index=0 if destructive else 1, escape_index=0)
    dialog.exec()
    return bool(dialog.choice())


def choose(parent, title: str, body: str,
           options: list[tuple[str, str, object]], default_index: int = 0):
    """Ask a question whose answers are not yes and no. Returns the result of
    the option chosen, and of ``default_index`` when the window is closed."""
    dialog = Modal(parent, title, body, options, default_index)
    dialog.exec()
    return dialog.choice()


def notify(parent, title: str, body: str, close_label: str = "OK") -> None:
    """State something the user cannot answer, with one way out."""
    Modal(parent, title, body, [(close_label, PRIMARY, None)]).exec()
