"""ui/card_delegate.py — the Kanban card painter.

``CardDelegate`` draws each task as a rounded card entirely with QPainter (no
QTextDocument/HTML), so rendering stays crisp and cannot throw during paint —
the failure mode of earlier drafts. All geometry is derived from a single set
of layout constants shared between ``sizeHint`` and ``paint`` so the reserved
height always matches what is drawn.

Reads its structured payload from ``CARD_ROLE`` (see theme.py); colours and the
pressure-colour helper also come from theme.py.

Optional bulk-select checkbox: when ``show_checkbox`` is True (set
by the Backlog column), a checkbox is drawn in a left gutter and clicking it
toggles the item's ``Qt.CheckStateRole``. The checked set drives the Backlog's
bulk Activate / Delete actions. Clicking the checkbox is consumed so it neither
selects the card (inspector) nor starts a drag (reorder).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRectF, QRect, QEvent
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from .theme import C, CARD_ROLE, _is_checked, _pressure_color


class CardDelegate(QStyledItemDelegate):
    """Paints each task as a rounded Kanban card, entirely with QPainter."""

    # layout constants (px)
    MARGIN = 5        # gap between the item rect edge and the card
    PAD = 11          # inner card padding
    ACCENT_W = 5      # left pressure accent stripe
    PILL_H = 18       # pressure pill height
    BADGE_H = 19      # epic pill height
    FOOT_H = 16       # footer row height
    GAP = 7           # vertical gap between blocks
    CHECK_W = 24      # left gutter reserved for the bulk-select checkbox
    CHECK_BOX = 16    # checkbox square size

    def __init__(self, parent=None, show_checkbox: bool = False):
        super().__init__(parent)
        self.show_checkbox = show_checkbox

    def _left_gap(self) -> int:
        """Left offset of the card body from the item rect: the base margin plus
        the checkbox gutter when this column shows checkboxes."""
        return self.MARGIN + (self.CHECK_W if self.show_checkbox else 0)

    def _title_font(self) -> QFont:
        f = QFont()
        f.setPointSize(11)
        f.setBold(True)
        return f

    def _small_font(self) -> QFont:
        f = QFont()
        f.setPointSize(8)
        f.setBold(True)
        return f

    def _content_width(self, total_width: int) -> int:
        return max(40, total_width - self._left_gap() - self.MARGIN
                   - self.ACCENT_W - 2 * self.PAD)

    def _title_height(self, title: str, content_w: int) -> int:
        fm = QFontMetrics(self._title_font())
        rect = fm.boundingRect(0, 0, content_w, 10_000,
                               int(Qt.TextWordWrap), title or "")
        # cap runaway titles at ~4 lines
        return min(rect.height(), fm.lineSpacing() * 4 + 2)

    def sizeHint(self, option, index):
        data = index.data(CARD_ROLE) or {}
        widget = option.widget
        if widget is not None and widget.viewport() is not None:
            total_w = widget.viewport().width()
        else:
            total_w = option.rect.width() or 260
        content_w = self._content_width(total_w)

        h = self.PAD
        h += self.PILL_H + self.GAP
        h += self._title_height(data.get("title", ""), content_w) + self.GAP
        if data.get("epic_name"):
            h += self.BADGE_H + self.GAP
        h += self.FOOT_H + self.PAD
        return QSize(total_w, h + 2 * self.MARGIN)

    def _checkbox_rect(self, option) -> QRect:
        """The clickable checkbox square, vertically centred in the left gutter."""
        r = option.rect
        x = r.left() + (self.CHECK_W - self.CHECK_BOX) // 2 + 2
        y = r.top() + (r.height() - self.CHECK_BOX) // 2
        return QRect(x, y, self.CHECK_BOX, self.CHECK_BOX)

    def _draw_pill(self, painter, x, y, text, bg, fg, font, min_w=0, radius=6):
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(text)
        w = max(min_w, tw + 16)
        h = fm.height() + 4
        rect = QRectF(x, y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(QColor(fg))
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, text)
        return w, h

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

        if selected:
            fill, border, border_w = QColor(C["SEL_BG"]), QColor(C["ACCENT"]), 1.6
        elif hovered:
            fill, border, border_w = QColor(C["HOVER_BG"]), QColor(C["HOVER_BORDER"]), 1.0
        else:
            fill, border, border_w = QColor(C["SURFACE"]), QColor(C["BORDER"]), 1.0

        # card body
        painter.setPen(QPen(border, border_w))
        painter.setBrush(fill)
        painter.drawRoundedRect(card, 9, 9)

        # left pressure accent stripe, clipped to the rounded card outline
        pressure = int(data.get("pressure", 0) or 0)
        painter.save()
        clip_path = QPainterPath()
        clip_path.addRoundedRect(card, 9, 9)
        painter.setClipPath(clip_path)
        painter.setPen(Qt.NoPen)
        painter.setBrush(_pressure_color(pressure))
        painter.drawRect(QRectF(card.left(), card.top(),
                                self.ACCENT_W, card.height()))
        painter.restore()

        cx = card.left() + self.ACCENT_W + self.PAD
        cw = card.right() - self.PAD - cx
        y = card.top() + self.PAD

        # pressure pill (+ issue number to its right, so cards are referenceable)
        pcolor = _pressure_color(pressure)
        pill_w, _ = self._draw_pill(painter, cx, y, f"PR{pressure}",
                                    pcolor.name(), "#ffffff", self._small_font())
        issue_id = data.get("issue_id")
        if issue_id is not None:
            idfont = self._small_font()
            idfont.setBold(False)
            painter.setFont(idfont)
            painter.setPen(QColor(C["INK_SOFT"]))
            painter.drawText(QRectF(cx + pill_w + 6, y, cw - pill_w - 6, self.PILL_H),
                             int(Qt.AlignLeft | Qt.AlignVCenter), f"#{issue_id}")

        # record-type pill (Build/Fix), right-aligned on the pressure row so the
        # two kinds of ticket read apart at a glance.
        rtype = (data.get("record_type") or "build").lower()
        if rtype == "fix":
            rt_text, rt_bg, rt_fg = "FIX", C["FIX_BG"], C["FIX_TX"]
        else:
            rt_text, rt_bg, rt_fg = "BUILD", C["BUILD_BG"], C["BUILD_TX"]
        rt_font = self._small_font()
        rt_fm = QFontMetrics(rt_font)
        rt_w = rt_fm.horizontalAdvance(rt_text) + 16
        self._draw_pill(painter, card.right() - self.PAD - rt_w, y, rt_text,
                        rt_bg, rt_fg, rt_font)
        y += self.PILL_H + self.GAP

        # title (word-wrapped, elided if it overflows the cap)
        title = data.get("title", "") or ""
        tfont = self._title_font()
        painter.setFont(tfont)
        painter.setPen(QColor(C["INK"]))
        th = self._title_height(title, int(cw))
        title_rect = QRectF(cx, y, cw, th)
        painter.drawText(title_rect,
                         int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop),
                         title)
        y += th + self.GAP

        # epic badge (the sprint badge was removed with sprints)
        epic_name = data.get("epic_name")
        if epic_name:
            bfont = self._small_font()
            fm = QFontMetrics(bfont)
            txt = fm.elidedText(f"◆ {epic_name}", Qt.ElideRight, int(cw))
            self._draw_pill(painter, cx, y, txt,
                            C["AMBER_BG"], C["AMBER_TX"], bfont)
            y += self.BADGE_H + self.GAP

        # divider + footer (owner left, story points right)
        painter.setPen(QPen(QColor(C["BORDER"]), 1))
        painter.drawLine(int(cx), int(y), int(card.right() - self.PAD), int(y))
        y += 4
        ffont = self._small_font()
        ffont.setBold(False)
        painter.setFont(ffont)
        fm = QFontMetrics(ffont)
        owner = data.get("owner", "") or "user"
        owner_txt = fm.elidedText(f"○ {owner}", Qt.ElideRight, int(cw * 0.6))
        painter.setPen(QColor(C["INK_SOFT"]))
        painter.drawText(QRectF(cx, y, cw, self.FOOT_H),
                         int(Qt.AlignLeft | Qt.AlignVCenter), owner_txt)
        # Effort: how much of one working session this card takes (src/app.md
        # Phase 4). Absent on a card nobody has sized, and drawn as-is.
        est = str(data.get("estimate", "") or "").upper()
        if est:
            pfont = self._small_font()
            painter.setFont(pfont)
            painter.setPen(QColor(C["ACCENT_DK"]))
            painter.drawText(QRectF(cx, y, cw, self.FOOT_H),
                             int(Qt.AlignRight | Qt.AlignVCenter), est)

        painter.restore()

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
            painter.drawRoundedRect(box, 4, 4)
            pen = QPen(QColor("#ffffff"), 2)
            painter.setPen(pen)
            painter.drawLine(int(box.left() + 4), int(box.center().y()),
                             int(box.center().x() - 1), int(box.bottom() - 4))
            painter.drawLine(int(box.center().x() - 1), int(box.bottom() - 4),
                             int(box.right() - 3), int(box.top() + 4))
        else:
            painter.setPen(QPen(QColor(C["INK_SOFT"]), 1.4))
            painter.setBrush(QColor(C["SURFACE"]))
            painter.drawRoundedRect(box, 4, 4)
        painter.restore()
