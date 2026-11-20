"""ui/scroll_bars.py — a scroll bar styled by the region it scrolls.

A scrolling region builds its two scroll bars in its own constructor, before
the region has its final class or an object name, and the style sheet is
matched once, then. A rule that reaches a bar through its region —
``QListWidget#columnCards QScrollBar`` — therefore never matches unless the bar
is styled again once the region is complete. A region is polished when it is
first shown, with its name set, so this module styles both its bars again at
that moment.

``install(app)`` puts one event filter on the application; every region built
before or after it is covered, and installing twice changes nothing.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QAbstractScrollArea, QApplication


class _ScrollBarStyler(QObject):
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Polish and isinstance(obj, QAbstractScrollArea):
            for bar in (obj.verticalScrollBar(), obj.horizontalScrollBar()):
                bar.style().unpolish(bar)
                bar.style().polish(bar)
        return False


_styler: _ScrollBarStyler | None = None


def install(app: QApplication) -> None:
    """Style every scroll bar in ``app`` by the region it scrolls, once."""
    global _styler
    if app is None or _styler is not None:
        return
    _styler = _ScrollBarStyler(app)
    app.installEventFilter(_styler)
