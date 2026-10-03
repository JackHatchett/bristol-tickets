"""ui/row_card.py — a list row drawn as a card, for the lists that are not the
board: skills and agents.

``RowCardDelegate`` is the board's ``CardDelegate`` with a different footer.
The card itself — its surface, shadow, corner, hover and selection fills, the
title and the one muted line under it — is the board card's, so a skill and a
ticket read as the same kind of object. The footer holds one line of meta text
on the left and neutral pills on the right, where a ticket's holds its id,
owner and kind.

Payload, under ``CARD_ROLE``:

    title        the bold first line
    description  the muted line under it
    meta         the footer's left-hand text
    pills        a list of short strings, drawn right-aligned; the last gives
                 way first when the row is narrow
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import QListWidget

from .card_delegate import CardDelegate
from .theme import C, space


class RowCardDelegate(CardDelegate):
    """A board card whose footer is meta text and neutral pills."""

    def _draw_footer(self, painter, data, cx, y, cw) -> None:
        sfont = self._small_font()
        fm = QFontMetrics(sfont)
        gap = space("sm")

        pills = [str(p) for p in data.get("pills", []) if str(p).strip()]
        widths = [self._pill_width(text, sfont) for text in pills]
        meta = data.get("meta", "") or ""
        min_meta = fm.horizontalAdvance("…") * 4

        # Pills give way from the end until the meta text keeps some room.
        while pills and cw - sum(widths) - gap * len(widths) < min_meta:
            pills, widths = pills[:-1], widths[:-1]
        meta_w = int(cw - sum(widths) - gap * len(widths))

        painter.setFont(sfont)
        painter.setPen(QColor(C["INK_SOFT"]))
        painter.drawText(QRectF(cx, y, meta_w, self.FOOT_H),
                         int(Qt.AlignLeft | Qt.AlignVCenter),
                         fm.elidedText(meta, Qt.ElideRight, max(0, meta_w)))

        x = cx + cw
        for text, w in zip(reversed(pills), reversed(widths)):
            x -= w
            self._draw_pill(painter, x, y, text, C["NEUTRAL_BG"],
                            C["NEUTRAL_TX"], sfont, width=w)
            x -= gap


def card_list() -> QListWidget:
    """A list whose rows are cards: the board column's transparent well, a
    pointer cursor because a row opens on click, and hover tracked so the card
    under the pointer lifts."""
    view = QListWidget()
    view.setObjectName("columnCards")
    view.setItemDelegate(RowCardDelegate(view))
    view.setMouseTracking(True)
    view.viewport().setCursor(Qt.PointingHandCursor)
    view.setUniformItemSizes(False)
    view.setSpacing(0)
    view.setResizeMode(QListWidget.Adjust)
    view.setVerticalScrollMode(QListWidget.ScrollPerPixel)
    return view
