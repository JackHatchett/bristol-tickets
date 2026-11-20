"""ui/switch.py — an on-off switch for a setting that changes a whole view or
how the app behaves, rather than choosing an item in a list.

A rounded track with a round knob and its label beside it. On, the track is
``ACCENT`` and the knob ``ON_ACCENT`` at the right end; off, the track is the
control face, ``BTN_BG`` with the ``BTN_BORDER`` edge every clickable thing
carries, and the knob ``INK_SOFT`` at the left end. The whole switch and its
label are one click, and Space turns it over with focus on it.

The design system's Bristol Controls page gives the Switch.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QSizePolicy

from .theme import LAYOUT, C, control_height, space

TRACK_W = LAYOUT["switch_track_w"]
TRACK_H = LAYOUT["switch_track_h"]
KNOB_INSET = LAYOUT["switch_knob_inset"]


class Switch(QAbstractButton):
    """A checkable button drawn as a switch; ``toggled`` carries its state."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(text)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        text = self.fontMetrics().horizontalAdvance(self.text())
        gap = space("md") if self.text() else 0
        return QSize(TRACK_W + gap + text + 2, max(control_height(), TRACK_H))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        on = self.isChecked()
        enabled = self.isEnabled()
        top = (self.height() - TRACK_H) / 2
        track = QRectF(0.5, top + 0.5, TRACK_W - 1, TRACK_H - 1)
        corner = track.height() / 2

        if not enabled:
            fill, edge, knob = C["DISABLED_BG"], C["BORDER"], C["DISABLED_TX"]
        elif on:
            fill, edge, knob = C["ACCENT"], C["ACCENT"], C["ON_ACCENT"]
        else:
            fill, edge, knob = C["BTN_BG"], C["BTN_BORDER"], C["INK_SOFT"]
        if enabled and not on and self.underMouse():
            fill = C["BTN_HOVER"]
        painter.setPen(QPen(QColor(edge), 1))
        painter.setBrush(QColor(fill))
        painter.drawRoundedRect(track, corner, corner)

        size = TRACK_H - 2 * KNOB_INSET
        x = (TRACK_W - KNOB_INSET - size) if on else KNOB_INSET
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(knob))
        painter.drawEllipse(QRectF(x, top + KNOB_INSET, size, size))

        if self.hasFocus():
            painter.setPen(QPen(QColor(C["ACCENT"]), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            ring = track.adjusted(-2, -2, 2, 2)
            painter.drawRoundedRect(ring, ring.height() / 2, ring.height() / 2)

        if self.text():
            painter.setPen(QColor(C["INK"] if enabled else C["DISABLED_TX"]))
            painter.setFont(self.font())
            left = TRACK_W + space("md")
            painter.drawText(
                QRectF(left, 0, self.width() - left, self.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self.text(),
            )
        painter.end()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)
