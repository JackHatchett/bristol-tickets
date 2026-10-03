"""ui/popups.py — a picker's open list, drawn as this app's own surface.

A QComboBox on macOS opens the platform's native menu, which no stylesheet
reaches: square, tight, and cut to the picker's width. The stylesheet's
``combobox-popup: 0`` makes every picker open Qt's own list instead, which the
stylesheet does style, and this module finishes the job the stylesheet cannot:

- **The list's window is frameless and transparent**, so the rounded corner the
  stylesheet gives the list is the corner the user sees, with no square behind
  it.
- **The list is as wide as its longest option**, never cut to the picker.

``install(app)`` puts one event filter on the application; every picker built
before or after it is covered, and installing twice changes nothing.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QComboBox, QWidget

from .theme import space

_CONTAINER = "QComboBoxPrivateContainer"


class _PopupStyler(QObject):
    def eventFilter(self, obj, event):  # noqa: N802 (Qt override)
        kind = event.type()
        if kind == QEvent.Polish and isinstance(obj, QWidget) \
                and obj.metaObject().className() == _CONTAINER:
            obj.setWindowFlag(Qt.FramelessWindowHint, True)
            obj.setWindowFlag(Qt.NoDropShadowWindowHint, True)
            obj.setAttribute(Qt.WA_TranslucentBackground, True)
        elif kind == QEvent.Show and isinstance(obj, QWidget) \
                and obj.metaObject().className() == _CONTAINER:
            combo = obj.parentWidget()
            if isinstance(combo, QComboBox):
                view = combo.view()
                wanted = (view.sizeHintForColumn(0) + 4 * space("lg")
                          + view.verticalScrollBar().sizeHint().width())
                if obj.width() < wanted:
                    obj.resize(wanted, obj.height())
        return False


_styler: _PopupStyler | None = None


def install(app) -> None:
    """Style every picker's open list in ``app``, once."""
    global _styler
    if app is None or _styler is not None:
        return
    _styler = _PopupStyler(app)
    app.installEventFilter(_styler)
