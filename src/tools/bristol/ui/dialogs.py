"""ui/dialogs.py — the app's confirmations and notices, in the design system.

One modal shape, built from the tokens in ``theme.py``: a titled window, a
heading, a body, and buttons at the app's own ranks. Every yes/no question and
every notice in Bristol Tickets comes from here, so none of them arrives as the
platform's own message box with its question glyph and its foreign buttons.

The styling contract these draw against is ``ui/README.md``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .theme import LAYOUT, space

# The three ranks a button in this app carries. A confirmation names the rank of
# the action it is confirming; the way out of the dialog is always ordinary.
PRIMARY = "globalCreateBtn"
DESTRUCTIVE = "deleteBtn"
ORDINARY = ""


class Modal(QDialog):
    """A titled question or notice with its buttons on one row.

    ``buttons`` is a list of ``(label, rank, result)`` in the order they are
    drawn, left to right. ``default_index`` names the one Enter presses, and
    its result is also what closing the window or pressing Esc returns.
    """

    def __init__(self, parent, title: str, body: str,
                 buttons: list[tuple[str, str, object]],
                 default_index: int = 0) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["small_dialog_min_w"])
        self._result: object = buttons[default_index][2] if buttons else None

        heading = QLabel(title)
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)

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

    The action's button carries the destructive rank where what it does cannot
    be undone and the primary rank otherwise. The way out carries the ordinary
    rank, and is what Enter, Esc and the title-bar close all land on, so no
    stray keypress reaches the action.
    """
    dialog = Modal(parent, title, body, [
        (cancel_label, ORDINARY, False),
        (accept_label, DESTRUCTIVE if destructive else PRIMARY, True),
    ], default_index=0)
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
