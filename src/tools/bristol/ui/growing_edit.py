"""growing_edit.py — the text field every surface types into.

A one-line field that scrolls sideways hides what was typed before it. This one
wraps, grows downward as the text does, and scrolls vertically once it reaches
its ceiling, so everything typed stays reachable without leaving the field.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QSizePolicy, QTextEdit


class GrowingTextEdit(QTextEdit):
    """A text field ``min_lines`` tall that grows to ``max_lines`` and then
    scrolls.

    ``submitted`` carries what ``QLineEdit.returnPressed`` carried: Return
    posts, Shift+Return opens a line. A field whose Return belongs to the text itself
    takes ``newline_on_return=True`` and never emits.

    ``text()`` and ``setText()`` are QLineEdit's names, so a field swapped for
    this one keeps its callers.
    """

    submitted = Signal()

    def __init__(self, parent=None, *, min_lines: int = 1, max_lines: int = 6,
                 newline_on_return: bool = False) -> None:
        super().__init__(parent)
        self._min_lines = max(1, min_lines)
        self._max_lines = max(self._min_lines, max_lines)
        self._newline_on_return = newline_on_return
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setTabChangesFocus(True)
        self.document().documentLayout().documentSizeChanged.connect(
            lambda _size: self._fit())
        self._fit()

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, value: str) -> None:
        self.setPlainText(value)

    def _fit(self) -> None:
        line = QFontMetrics(self.font()).lineSpacing()
        # The border, the padding the stylesheet sets and the document's own
        # margin are whatever the field's height exceeds its viewport by.
        # // Reading them off the widget keeps the fit correct under a
        # // stylesheet that changes padding.
        chrome = max(self.height() - self.viewport().height(),
                     int(self.document().documentMargin() * 2) + 2)
        content = self.document().size().height()
        floor, ceiling = line * self._min_lines, line * self._max_lines
        self.setFixedHeight(int(min(max(content, floor), ceiling) + chrome))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()

    def keyPressEvent(self, event) -> None:
        plain_return = (event.key() in (Qt.Key_Return, Qt.Key_Enter)
                        and not event.modifiers() & Qt.ShiftModifier)
        if plain_return and not self._newline_on_return:
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)
