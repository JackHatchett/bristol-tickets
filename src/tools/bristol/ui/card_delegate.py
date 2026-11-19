"""ui/card_delegate.py — the Kanban card painter.

``CardDelegate`` draws each task as a rounded card entirely with QPainter (no
QTextDocument/HTML), so rendering stays crisp and cannot throw during paint.
One layout pass, ``_footer_layout``, places everything below the title, and
``sizeHint`` and ``paint`` both read it, so the height reserved is the height
drawn at every width.

A card is a flat surface with a 1 px ``BTN_BORDER`` edge and no shadow, as
everything that can be clicked is; a hovered card takes ``HOVER_BG``, and a
selected one ``SEL_BG`` with a 1 px ``ACCENT`` edge. It reads top to bottom:

- the title, wrapping to two lines and eliding after the second;
- who owns it, at body size, on a line of its own;
- one row of pills — Build or Fix, then size, a due date and the epic — with
  the card's number at its right end in caption size, the quietest text on
  the card.

The three blocks sit one GAP apart. The owner is never cut off; the epic
elides where the row is too narrow, and only a column narrower than every
pill wraps the row. A card shows no
description line and no tier: neither is what the board is scanned for, and
the tier sorts nothing (``src/app.md`` Phase 3.3).

A card with no epic carries one accent dot in its top corner instead of an epic
pill. A card with a due date carries it as one more pill, in the Fix tint once
the date has gone by on a card nobody has finished.

Reads its structured payload from ``CARD_ROLE`` (see theme.py). Every colour,
gap, pad, corner and font size it draws with resolves through theme.py at paint
time, so a scheme swap and a token change both reach the card with no edit
here.

Optional bulk-select checkbox: when ``show_checkbox`` is True (set by the
Backlog column), a checkbox is drawn in a left gutter and clicking it toggles
the item's ``Qt.CheckStateRole``. The checked set drives the Backlog's bulk
Activate / Delete actions. Clicking the checkbox is consumed so it neither
selects the card (inspector) nor starts a drag (reorder).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRectF, QRect, QEvent
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from .theme import (
    C,
    CARD_ROLE,
    agent_caption,
    _is_checked,
    size_label,
    radius,
    space,
    type_size,
)


class CardDelegate(QStyledItemDelegate):
    """Paints each task as a rounded Kanban card, entirely with QPainter."""

    # How many lines the title may take before it elides, and whether the
    # card carries a muted description line under it. The board card carries
    # none; a list row (row_card.py) carries one.
    TITLE_LINES = 2
    SHOW_DESCRIPTION = False

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
    def CHECK_W(self) -> int:
        """Left gutter reserved for the bulk-select checkbox."""
        return space("2xl")

    @property
    def CHECK_BOX(self) -> int:
        """Checkbox square size."""
        return space("xl")

    @property
    def PILL_H(self) -> int:
        """Height of a one-line pill: the small font's line box plus its pad."""
        return QFontMetrics(self._small_font()).height() + space("md")

    @property
    def FOOT_H(self) -> int:
        """Height of a one-row footer — the tallest thing in it is a pill."""
        return self.PILL_H

    @property
    def DESC_H(self) -> int:
        """Height of the single description line."""
        return QFontMetrics(self._desc_font()).height()

    @property
    def MARK_D(self) -> int:
        """Diameter of the untriaged mark: the dot on a card nobody has placed
        yet."""
        return space("md")

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

    def _owner_font(self) -> QFont:
        f = QFont()
        f.setPointSize(type_size("body"))
        return f

    def _small_font(self) -> QFont:
        f = QFont()
        f.setPointSize(type_size("caption"))
        return f

    def _content_width(self, total_width: int) -> int:
        return max(40, total_width - self._left_gap() - self.MARGIN - 2 * self.PAD)

    def _title_width(self, content_w: int, data: dict) -> int:
        """What the title has to itself. An untriaged card gives up the corner
        the mark sits in, and sizeHint and paint both ask here so the height
        reserved is the height drawn."""
        if not data.get("untriaged"):
            return content_w
        return max(40, content_w - self.MARK_D - space("sm"))

    def _title_lines(self, title: str, width: int) -> list[str]:
        """The title broken into at most TITLE_LINES lines at word boundaries,
        the last one elided when the title runs on past it."""
        fm = QFontMetrics(self._title_font())
        words = (title or "").split()
        lines: list[str] = []
        current = ""
        for i, word in enumerate(words):
            trial = f"{current} {word}" if current else word
            if fm.horizontalAdvance(trial) <= width or not current:
                current = trial
                continue
            lines.append(current)
            current = word
            if len(lines) == self.TITLE_LINES - 1:
                current = " ".join(words[i:])
                break
        if current:
            lines.append(current)
        lines = lines[:self.TITLE_LINES]
        return [fm.elidedText(line, Qt.ElideRight, width) for line in lines]

    def _title_height(self, title: str, content_w: int) -> int:
        lines = max(1, len(self._title_lines(title, content_w)))
        fm = QFontMetrics(self._title_font())
        return fm.height() + fm.lineSpacing() * (lines - 1)

    def _shows_description(self, data: dict) -> bool:
        return self.SHOW_DESCRIPTION and bool((data.get("description") or "").strip())

    def _footer_height(self, data: dict, content_w: int) -> int:
        """Everything below the title and the gap above it; zero where a card
        has nothing there."""
        return self.GAP + self._footer_layout(data, content_w)[1]

    # Qt asks a card's height many times over in one re-layout, and a restyle
    # re-lays out every list, so a height is measured once per card, width,
    # font and gutter and read back after that.
    _HEIGHT_CACHE_MAX = 8000

    def sizeHint(self, option, index):
        data = index.data(CARD_ROLE) or {}
        widget = option.widget
        if widget is not None and widget.viewport() is not None:
            total_w = widget.viewport().width()
        else:
            total_w = option.rect.width() or 260
        key = (total_w, self.show_checkbox, self._title_font().key(),
               repr(sorted(data.items())))
        cache = self.__dict__.setdefault("_heights", {})
        height = cache.get(key)
        if height is None:
            if len(cache) >= self._HEIGHT_CACHE_MAX:
                cache.clear()
            height = cache[key] = self._measure_height(data, total_w)
        return QSize(total_w, height)

    def _measure_height(self, data: dict, total_w: int) -> int:
        """A card's whole height, margins included, at the given width."""
        content_w = self._content_width(total_w)

        h = self.PAD
        h += self._title_height(data.get("title", ""),
                                self._title_width(content_w, data))
        if self._shows_description(data):
            h += space("sm") + self.DESC_H
        h += self._footer_height(data, content_w) + self.PAD
        return h + 2 * self.MARGIN

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
        corner = radius("sm")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(rect, corner, corner)
        painter.setPen(QColor(fg))
        painter.setFont(font)
        # Elide against the pill less one side's pad: the measured width and
        # the drawn width differ by a fraction of a pixel, and a pill sized to
        # its text would otherwise cut that text.
        inner = int(w - space("lg"))
        painter.drawText(rect, Qt.AlignCenter,
                         QFontMetrics(font).elidedText(
                             text, Qt.ElideRight, inner))
        return w

    # ----- the board card's lower half --------------------------------------
    def _footer_pills(self, data: dict) -> list[tuple[str, str, str]]:
        """The pills in reading order: Build or Fix, the one tinted pill, at
        the left; then the quiet ones together — size, a due date, and the
        epic last, since it is the one that gives up width."""
        pills: list[tuple[str, str, str]] = []
        rtype = (data.get("record_type") or "build").lower()
        if rtype == "fix":
            pills.append(("Fix", C["FIX_BG"], C["FIX_TX"]))
        else:
            pills.append(("Build", C["BUILD_BG"], C["BUILD_TX"]))
        size = size_label(data.get("estimate"))
        if size:
            pills.append((size, C["NEUTRAL_BG"], C["NEUTRAL_TX"]))
        # A due date is a fact about the card rather than a position in a
        # queue, so it reads as one more pill. An overdue one takes the same
        # tint a Fix does, which is the board's one colour for something wrong.
        due = (data.get("due_date") or "").strip()
        if due:
            overdue = bool(data.get("overdue"))
            pills.append((f"Overdue {due}" if overdue else f"Due {due}",
                          C["FIX_BG"] if overdue else C["NEUTRAL_BG"],
                          C["FIX_TX"] if overdue else C["NEUTRAL_TX"]))
        epic_name = (data.get("epic_name") or "").strip()
        if epic_name:
            pills.append((epic_name, C["NEUTRAL_BG"], C["NEUTRAL_TX"]))
        return pills

    def _footer_layout(self, data: dict, cw: int):
        """Where everything under the title goes, relative to its top-left, and
        how tall it is. Returns ``(ops, height)``; each op is
        ``("owner"|"id", rect, text)`` or ``("pill", rect, (text, bg, fg))``.

        The owner has a line to itself. Under it, one row: the pills from the
        left and the number at the right. Where the row is too narrow the epic
        elides first; where even a shortened epic will not fit, the pills wrap
        onto further rows and the number closes the last one."""
        sfont, ofont = self._small_font(), self._owner_font()
        sfm, ofm = QFontMetrics(sfont), QFontMetrics(ofont)
        gap = space("sm")
        ops: list = []

        owner = agent_caption(data.get("owner", "") or "user")
        line_h = ofm.height()
        ops.append(("owner", QRectF(0, 0, cw, line_h),
                    ofm.elidedText(owner, Qt.ElideRight, int(cw))))
        y = line_h + self.GAP

        issue_id = data.get("issue_id")
        id_text = f"#{issue_id}" if issue_id is not None else ""
        id_w = sfm.horizontalAdvance(id_text) if id_text else 0
        id_room = id_w + 2 * gap if id_text else 0

        pills = self._footer_pills(data)
        widths = [min(self._pill_width(text, sfont), cw) for text, _, _ in pills]
        has_epic = bool((data.get("epic_name") or "").strip())
        spare = cw - id_room - sum(widths) - gap * max(0, len(widths) - 1)
        if spare < 0 and has_epic:
            least = self._pill_width("Abc…", sfont)
            widths[-1] = max(least, widths[-1] + spare)

        x, row_h = 0, self.PILL_H
        for (text, bg, fg), w in zip(pills, widths):
            if x and x + w > cw:
                y += row_h + gap
                x = 0
            ops.append(("pill", QRectF(x, y, w, self.PILL_H), (text, bg, fg)))
            x += w + gap
        if id_text:
            if x and x - gap + id_room > cw:
                y += row_h + gap
            ops.append(("id", QRectF(cw - id_w, y, id_w, row_h), id_text))
        return ops, y + row_h

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
            left_gap, self.MARGIN, -self.MARGIN, -self.MARGIN)

        # A card is flat: its edge is the 1 px every clickable thing has, and
        # selection turns that edge to the accent over the selected fill.
        if selected:
            fill, edge = QColor(C["SEL_BG"]), QColor(C["ACCENT"])
        elif hovered:
            fill, edge = QColor(C["HOVER_BG"]), QColor(C["BTN_BORDER"])
        else:
            fill, edge = QColor(C["SURFACE"]), QColor(C["BTN_BORDER"])
        painter.setPen(QPen(edge, 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5),
                                radius("lg"), radius("lg"))

        cx = card.left() + self.PAD
        cw = card.right() - self.PAD - cx
        y = card.top() + self.PAD

        # A card with no epic carries one dot in its top corner, which no other
        # card has: where it belongs is still to be decided, and the decision
        # belongs to whoever is looking at the board. A card in the standing
        # workstream has an epic, so it carries nothing.
        title_w = self._title_width(int(cw), data)
        if data.get("untriaged"):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(C["ACCENT"]))
            painter.drawEllipse(
                QRectF(cx + cw - self.MARK_D,
                       card.top() + self.PAD + (self.MARK_D / 2),
                       self.MARK_D, self.MARK_D))

        # Title — the first thing read, at most TITLE_LINES lines.
        tfont = self._title_font()
        tfm = QFontMetrics(tfont)
        painter.setFont(tfont)
        painter.setPen(QColor(C["INK"]))
        for i, line in enumerate(self._title_lines(data.get("title", "") or "",
                                                   title_w)):
            painter.drawText(QRectF(cx, y + i * tfm.lineSpacing(), title_w,
                                    tfm.height()),
                             int(Qt.AlignLeft | Qt.AlignTop), line)
        y += self._title_height(data.get("title", "") or "", title_w)

        # One muted line of the description, where this card carries one.
        if self._shows_description(data):
            desc = " ".join((data.get("description") or "").split())
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
        """The owner and the number on one line, the pills flowing under it."""
        ops, _ = self._footer_layout(data, int(cw))
        sfont = self._small_font()
        for kind, rect, payload in ops:
            rect = rect.translated(cx, y)
            if kind == "pill":
                text, bg, fg = payload
                self._draw_pill(painter, rect.x(), rect.y(), text, bg, fg,
                                sfont, width=rect.width())
            elif kind == "owner":
                painter.setFont(self._owner_font())
                painter.setPen(QColor(C["INK_SOFT"]))
                painter.drawText(rect, int(Qt.AlignLeft | Qt.AlignVCenter),
                                 payload)
            else:
                painter.setFont(sfont)
                painter.setPen(QColor(C["INK_SOFT"]))
                painter.drawText(rect, int(Qt.AlignRight | Qt.AlignVCenter),
                                 payload)

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
            painter.setPen(QPen(QColor(C["ACCENT"]), 1))
            painter.setBrush(QColor(C["SURFACE"]))
            painter.drawRoundedRect(box, radius("sm"), radius("sm"))
        painter.restore()
