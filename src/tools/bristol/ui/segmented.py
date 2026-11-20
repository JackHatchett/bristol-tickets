"""A segmented control: two to five choices joined into one control, exactly
one of them chosen, as a Mac segmented control filters one view.

Each segment is a checkable button named ``segment``; the style sheet draws them
on the control face, joined, with the chosen one in the selection fill and the
accent text. ``position`` (first, middle, last) tells the style sheet which
corners round.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget


class SegmentedControl(QWidget):
    """``choices`` as ``(value, caption)`` pairs; ``changed`` carries the value
    of the segment chosen."""

    changed = Signal(str)

    def __init__(
        self,
        choices: list[tuple[str, str]],
        value: str | None = None,
        parent=None,
        *,
        none_chosen: bool = False,
    ) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._values: list[str] = []
        for index, (choice, caption) in enumerate(choices):
            button = QPushButton(caption)
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setAutoDefault(False)
            last = len(choices) - 1
            button.setProperty(
                "position", "first" if index == 0 else "last" if index == last else "middle"
            )
            self._group.addButton(button, index)
            self._values.append(choice)
            row.addWidget(button)
        if value in self._values:
            self._group.button(self._values.index(value)).setChecked(True)
        elif not none_chosen:
            self._group.button(0).setChecked(True)
        self._group.idToggled.connect(self._toggled)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def _toggled(self, index: int, checked: bool) -> None:
        if checked:
            self.changed.emit(self._values[index])

    def value(self) -> str:
        """The chosen segment's value; empty while a control opened with none
        chosen is still unchosen."""
        index = self._group.checkedId()
        return self._values[index] if index >= 0 else ""

    def set_value(self, value: str) -> None:
        if value in self._values:
            self._group.button(self._values.index(value)).setChecked(True)

    def button(self, value: str) -> QPushButton:
        """The segment that chooses ``value``."""
        return self._group.button(self._values.index(value))
