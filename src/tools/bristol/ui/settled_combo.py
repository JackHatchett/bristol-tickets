"""settled_combo.py — the picker that changes only when someone chooses.

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
