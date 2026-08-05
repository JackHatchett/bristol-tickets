"""ui/card_delegate.py — the Kanban card painter.

``CardDelegate`` draws each task as a rounded card entirely with QPainter (no
QTextDocument/HTML), so rendering stays crisp and cannot throw during paint —
the failure mode of earlier drafts. All geometry is derived from one set of
token-backed properties shared between ``sizeHint`` and ``paint`` so the
reserved height always matches what is drawn.

A card is the only raised surface on the board: a soft shadow, a full corner
radius, and a fill that carries hover and selection on its own. It reads top to
bottom as the title, one muted line of the description, and a footer holding
who owns it, how big it is, how hard it is pushing, what kind of record it is
and which epic it belongs to.

Pressure is drawn in the same neutral treatment as every other footer fact. It
sorts nothing and gates nothing (``src/app.md`` Phase 3.3), so nothing on the
card ramps it from green to red.

Reads its structured payload from ``CARD_ROLE`` (see theme.py). Every colour,
gap, pad, corner and font size it draws with resolves through theme.py at paint
time — the live scheme for colour, the token scales for the rest — so a scheme
swap and a token change both reach the card with no edit here. Row heights come
from the font metrics of the token they are sized in, so the type scale governs
them too.

Optional bulk-select checkbox: when ``show_checkbox`` is True (set
by the Backlog column), a checkbox is drawn in a left gutter and clicking it
toggles the item's ``Qt.CheckStateRole``. The checked set drives the Backlog's
bulk Activate / Delete actions. Clicking the checkbox is consumed so it neither
selects the card (inspector) nor starts a drag (reorder).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRectF, QRect, QEvent
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from .theme import (
    C,
    CARD_ROLE,
    _is_checked,
    effort_label,
    radius,
    space,
    type_size,
)


class CardDelegate(QStyledItemDelegate):
    """Paints each task as a rounded Kanban card, entirely with QPainter."""

    def __init__(self, parent=None, show_checkbox: bool = False):
        super().__init__(parent)
        self.show_checkbox = show_checkbox

    # ----- geometry, all of it from the token scales ------------------------
    @property
    def MARGIN(self) -> int:
        """Gap between the item rect edge and the card."""
        return space("sm")

    @property
    def PAD(self) -> int:
        """Inner card padding."""
        return space("lg")

    @property
    def GAP(self) -> int:
        """Vertical gap between blocks inside the card."""
        return space("md")

    @property
    def SHADOW_D(self) -> int:
        """How far the soft shadow falls below the card."""
        return space("sm")

    @property
    def CHECK_W(self) -> int:
        """Left gutter reserved for the bulk-select checkbox."""
        return space("2xl")

    @property
    def CHECK_BOX(self) -> int:
        """Checkbox square size."""
        return space("xl")

    @property
    def PILL_H(self) -> int:
        """Height of a pill: the small font's line box plus its own pad."""
        return QFontMetrics(self._small_font()).height() + space("sm")

    @property
    def FOOT_H(self) -> int:
        """Height of the footer row — the tallest thing in it is a pill."""
        return self.PILL_H

    @property
    def DESC_H(self) -> int:
        """Height of the single description line."""
        return QFontMetrics(self._desc_font()).height()

    def _left_gap(self) -> int:
        """Left offset of the card body from the item rect: the base margin plus
        the checkbox gutter when this column shows checkboxes."""
        return self.MARGIN + (self.CHECK_W if self.show_checkbox else 0)

    def _title_font(self) -> QFont:
        f = QFont()
        f.setPointSize(type_size("title"))
        f.setWeight(QFont.DemiBold)
        return f

    def _desc_font(self) -> QFont:
        f = QFont()
        f.setPointSize(type_size("body"))
        return f

    def _small_font(self) -> QFont:
        f = QFont()
        f.setPointSize(type_size("caption"))
        return f

    def _content_width(self, total_width: int) -> int:
        return max(40, total_width - self._left_gap() - self.MARGIN - 2 * self.PAD)

    def _title_height(self, title: str, content_w: int) -> int:
        fm = QFontMetrics(self._title_font())
        rect = fm.boundingRect(0, 0, content_w, 10_000,
                               int(Qt.TextWordWrap), title or "")
        # cap runaway titles at ~3 lines
        return min(rect.height(), fm.lineSpacing() * 3 + space("xs"))

    def sizeHint(self, option, index):
        data = index.data(CARD_ROLE) or {}
        widget = option.widget
        if widget is not None and widget.viewport() is not None:
            total_w = widget.viewport().width()
        else:
            total_w = option.rect.width() or 260
        content_w = self._content_width(total_w)

        h = self.PAD
        h += self._title_height(data.get("title", ""), content_w)
        if (data.get("description") or "").strip():
            h += space("sm") + self.DESC_H
        h += self.GAP + self.FOOT_H + self.PAD
        return QSize(total_w, h + 2 * self.MARGIN + self.SHADOW_D)

    def _checkbox_rect(self, option) -> QRect:
        """The clickable checkbox square, vertically centred in the left gutter."""
        r = option.rect
        x = r.left() + (self.CHECK_W - self.CHECK_BOX) // 2 + space("xs")
        y = r.top() + (r.height() - self.CHECK_BOX) // 2
        return QRect(x, y, self.CHECK_BOX, self.CHECK_BOX)

    def _pill_width(self, text: str, font: QFont) -> int:
        return QFontMetrics(font).horizontalAdvance(text) + space("lg") * 2

    def _draw_pill(self, painter, x, y, text, bg, fg, font, width=None):
        w = self._pill_width(text, font) if width is None else width
        h = self.PILL_H
        rect = QRectF(x, y, w, h)
        corner = radius("pill")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(rect, corner, corner)
        painter.setPen(QColor(fg))
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter,
                         QFontMetrics(font).elidedText(
                             text, Qt.ElideRight, int(w - space("lg"))))
        return w

    def editorEvent(self, event, model, option, index):
        """Toggle the bulk-select checkbox on a click inside its square, and
        consume that click so it doesn't also select the card or begin a drag.
        All other events fall through to the default handling."""
        if (self.show_checkbox
                and event.type() in (QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick)
                and self._checkbox_rect(option).contains(event.position().toPoint())):
            if event.type() == QEvent.MouseButtonRelease:
                checked = _is_checked(index.data(Qt.CheckStateRole))
                model.setData(index, Qt.Unchecked if checked else Qt.Checked,
                              Qt.CheckStateRole)
            return True
        return super().editorEvent(event, model, option, index)

    def paint(self, painter, option, index):
        data = index.data(CARD_ROLE) or {}
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        if self.show_checkbox:
            self._paint_checkbox(painter, option, index)

        left_gap = self._left_gap()
        card = QRectF(option.rect).adjusted(
            left_gap, self.MARGIN, -self.MARGIN, -self.MARGIN - self.SHADOW_D)

        # Selection and hover are carried by the surface itself: the fill
        # changes and, for a selected card, the shadow deepens. Nothing gains a
        # heavier outline.
        if selected:
            fill = QColor(C["SEL_BG"])
        elif hovered:
            fill = QColor(C["HOVER_BG"])
        else:
            fill = QColor(C["SURFACE"])

        self._draw_shadow(painter, card, deep=selected)
        painter.setPen(QPen(QColor(C["BORDER"]), 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(card, radius("lg"), radius("lg"))

        cx = card.left() + self.PAD
        cw = card.right() - self.PAD - cx
        y = card.top() + self.PAD

        # Title — the first thing read.
        title = data.get("title", "") or ""
        painter.setFont(self._title_font())
        painter.setPen(QColor(C["INK"]))
        th = self._title_height(title, int(cw))
        painter.drawText(QRectF(cx, y, cw, th),
                         int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop),
                         title)
        y += th

        # One muted line of the description, under the title.
        desc = " ".join((data.get("description") or "").split())
        if desc:
            y += space("sm")
            dfont = self._desc_font()
            painter.setFont(dfont)
            painter.setPen(QColor(C["INK_SOFT"]))
            painter.drawText(
                QRectF(cx, y, cw, self.DESC_H),
                int(Qt.AlignLeft | Qt.AlignVCenter),
                QFontMetrics(dfont).elidedText(desc, Qt.ElideRight, int(cw)))
            y += self.DESC_H

        y += self.GAP
        self._draw_footer(painter, data, cx, y, cw)
        painter.restore()

    def _draw_footer(self, painter, data, cx, y, cw) -> None:
        """One row: who owns it and how hard it is pushing on the left, then the
        soft-tinted pills right-aligned — effort, record type, epic. Each pill's
        text colour comes from its own tint. The epic is the one that gives up
        width first, because the board is usually already filtered by epic."""
        sfont = self._small_font()
        fm = QFontMetrics(sfont)

        pills: list[tuple[str, str, str]] = []
        effort = effort_label(data.get("estimate"))
        if effort:
            pills.append((effort, C["NEUTRAL_BG"], C["NEUTRAL_TX"]))
        rtype = (data.get("record_type") or "build").lower()
        if rtype == "fix":
            pills.append(("Fix", C["FIX_BG"], C["FIX_TX"]))
        else:
            pills.append(("Build", C["BUILD_BG"], C["BUILD_TX"]))
        epic_name = (data.get("epic_name") or "").strip()
        if epic_name:
            pills.append((epic_name, C["AMBER_BG"], C["AMBER_TX"]))

        owner = data.get("owner", "") or "user"
        pressure = int(data.get("pressure", 0) or 0)
        issue_id = data.get("issue_id")
        prefix = f"#{issue_id}  ·  " if issue_id is not None else ""
        suffix = f"  ·  pr {pressure}"
        left_text = prefix + owner + suffix
        wanted_left = fm.horizontalAdvance(left_text)

        gap = space("sm")
        widths = [self._pill_width(text, sfont) for text, _, _ in pills]

        def spare() -> int:
            return int(cw - wanted_left - sum(widths) - gap * len(widths))

        # The epic gives up width first: it shrinks to what is left, and is
        # dropped once it is too narrow to say anything. Only then does the
        # left-hand text elide, and the id, the owner and the pressure reading
        # are what it holds — each of them appearing exactly once.
        if spare() < 0 and epic_name:
            shrunk = widths[-1] + spare()
            if shrunk < self._pill_width("…", sfont) * 2:
                pills, widths = pills[:-1], widths[:-1]
            else:
                widths[-1] = shrunk
        left_w = max(0, min(wanted_left, wanted_left + spare()))
        if left_w < wanted_left:
            # The owner is the elastic part: the id and the pressure reading
            # each stay whole, and a long slug is what gives up characters.
            fixed = fm.horizontalAdvance(prefix + suffix)
            left_text = (prefix
                         + fm.elidedText(owner, Qt.ElideRight,
                                         max(0, left_w - fixed))
                         + suffix)

        painter.setFont(sfont)
        painter.setPen(QColor(C["INK_SOFT"]))
        painter.drawText(QRectF(cx, y, left_w, self.FOOT_H),
                         int(Qt.AlignLeft | Qt.AlignVCenter),
                         fm.elidedText(left_text, Qt.ElideRight, left_w))

        x = cx + cw
        for (text, bg, fg), w in zip(reversed(pills), reversed(widths)):
            x -= w
            self._draw_pill(painter, x, y, text, bg, fg, sfont, width=w)
            x -= gap

    def _draw_shadow(self, painter, card: QRectF, deep: bool) -> None:
        """A soft drop shadow, drawn as a few offset rounded rects fading out
        under the card. A selected card sits one step higher."""
        base = QColor(C["SHADOW"])
        steps = 4 if deep else 3
        painter.setPen(Qt.NoPen)
        for step in range(steps, 0, -1):
            layer = QColor(base)
            layer.setAlpha(max(1, base.alpha() // (step + 1)))
            painter.setBrush(layer)
            rect = card.adjusted(-step + 1, step, step - 1, step)
            painter.drawRoundedRect(rect, radius("lg"), radius("lg"))

    def _paint_checkbox(self, painter, option, index) -> None:
        """Draw the bulk-select checkbox in the left gutter: a rounded square,
        filled with the accent and bearing a check mark when checked."""
        box = QRectF(self._checkbox_rect(option))
        checked = _is_checked(index.data(Qt.CheckStateRole))
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        if checked:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(C["ACCENT"]))
            painter.drawRoundedRect(box, radius("sm"), radius("sm"))
            pen = QPen(QColor(C["ON_ACCENT"]), 2)
            painter.setPen(pen)
            painter.drawLine(int(box.left() + space("sm")), int(box.center().y()),
                             int(box.center().x() - 1), int(box.bottom() - space("sm")))
            painter.drawLine(int(box.center().x() - 1), int(box.bottom() - space("sm")),
                             int(box.right() - space("xs")), int(box.top() + space("sm")))
        else:
            painter.setPen(QPen(QColor(C["INK_SOFT"]), 1.4))
            painter.setBrush(QColor(C["SURFACE"]))
            painter.drawRoundedRect(box, radius("sm"), radius("sm"))
        painter.restore()
