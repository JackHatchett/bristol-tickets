"""settled_combo.py — loading a picker, and the one that resists a stray gesture.

A plain QComboBox takes the scroll wheel and the arrow keys whenever it holds
focus, so a gesture aimed past it moves the value and every listener fires. A
control whose value decides what a whole session means cannot move that way.
This one moves when its list is open and a row is chosen, and at no other time.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox

# Keys a closed combo would otherwise step through its list with.
_STEPPING_KEYS = (
    Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown,
    Qt.Key_Home, Qt.Key_End,
)


def fill_words(combo: QComboBox, choices, *, hint: str | None = None) -> QComboBox:
    """Load a picker from (stored value, caption) pairs and size it to the widest.

    The value stays in the item's data and the caption is all a reader sees, so
    the two move independently. A combo left at its default policy sizes to
    whichever option happens to be current, so a longer one is drawn truncated
    the moment it is picked.
    """
    for value, caption in choices:
        combo.addItem(caption, value)
    combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
    if hint:
        combo.setToolTip(hint)
    return combo


class SettledComboBox(QComboBox):
    """A combo whose value survives a wheel gesture and a stray arrow key.

    ``picked`` carries the chosen text and fires only on a deliberate choice,
    so a listener that writes somewhere durable can connect to it directly.
    Loading a value with ``setCurrentText`` never emits it.
    """

    picked = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.activated.connect(self._on_activated)

    def _on_activated(self, index: int) -> None:
        text = self.itemText(index)
        if text:
            self.picked.emit(text)

    def wheelEvent(self, event) -> None:
        """Let the gesture through to whatever scrolls behind this."""
        event.ignore()

    def keyPressEvent(self, event) -> None:
        if event.key() in _STEPPING_KEYS and not self.view().isVisible():
            event.ignore()
            return
        super().keyPressEvent(event)
