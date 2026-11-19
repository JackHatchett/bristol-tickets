"""ui/row_card.py — a list row drawn as a card, for the lists that are not the
board: skills and agents.

``RowCardDelegate`` is the board's ``CardDelegate`` with a different footer.
The card itself — its surface, edge, corner, hover and selection fills and the
title — is the board card's, so a skill and a ticket read as the same kind of
object. A row adds the one muted line under the title that a board card leaves
out, and lets its name run to three lines. The footer contains one line of meta text
on the left and neutral pills on the right, where a ticket's shows its id,
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
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QListWidget

from .card_delegate import CardDelegate
from .theme import C, space, type_size


class RowCardDelegate(CardDelegate):
    """A board card whose footer is meta text and neutral pills.

    A row is only as tall as what it says: with no meta text its pills sit
    beside the name, and with neither it has no footer at all. Its pills read at
    body size, since on these lists they are what the row is scanned for."""

    TITLE_LINES = 3
    SHOW_DESCRIPTION = True

    def _small_font(self) -> QFont:
        font = QFont()
        font.setPointSize(type_size("body"))
        return font

    @staticmethod
    def _pills(data: dict) -> list[str]:
        return [str(p) for p in data.get("pills", []) if str(p).strip()]

    def _inline(self, data: dict) -> bool:
        """Whether the pills sit beside the name rather than in a footer."""
        return not (data.get("meta") or "").strip() and bool(self._pills(data))

    def _has_footer(self, data: dict) -> bool:
        return bool((data.get("meta") or "").strip())

    def _title_width(self, content_w: int, data: dict) -> int:
        if not self._inline(data):
            return content_w
        font = self._small_font()
        taken = sum(self._pill_width(p, font) + space("sm")
                    for p in self._pills(data))
        return max(40, content_w - taken)

    def _footer_height(self, data: dict, content_w: int) -> int:
        return self.GAP + self.FOOT_H if self._has_footer(data) else 0

    def paint(self, painter, option, index):
        # Where the name starts, for pills drawn beside it.
        self._title_top = option.rect.top() + self.MARGIN + self.PAD
        super().paint(painter, option, index)

    def _draw_footer(self, painter, data, cx, y, cw) -> None:
        if self._inline(data):
            font = self._small_font()
            x = cx + cw
            for text in reversed(self._pills(data)):
                width = self._pill_width(text, font)
                x -= width
                self._draw_pill(painter, x, self._title_top, text,
                                C["NEUTRAL_BG"], C["NEUTRAL_TX"], font,
                                width=width)
                x -= space("sm")
            return
        if not self._has_footer(data):
            return
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
