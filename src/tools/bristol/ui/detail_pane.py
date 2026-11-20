"""ui/detail_pane.py — the detail pane: where a selected card is read and
edited in place.

``DetailPane`` sits right of the board splitter. Status, stage, owner, epic,
tier, size and Blocked are live labelled controls, two to a row: a change writes
through the same connection every other writer uses, so the database triggers
record a pane edit exactly as they record a dialog edit or a board drag. The
fields nobody edits — issue number, record type, originator, created,
modified — render as an aligned key/value grid under Attributes.

The pane reads Title, Description, Links, Attachments, Log, Attributes top to
bottom — the description under a formCaption like the controls above it, the
rest each under a section header and hairline. The description is sized to its content
within a bound; the log is a timeline distinguishing comments from
machine-written change events; the comment composer is pinned to the pane's
foot at full width. The header carries the collapse control — the host window
owns what collapsing does to the splitter.

Every colour, gap, corner and font size resolves through theme.py at use time,
so a scheme swap reaches the pane with no edit here; ``refresh_theme()``
re-renders the one thing that bakes colours in (the timeline HTML).
"""

from __future__ import annotations

import html
import sqlite3
from collections.abc import Callable
from typing import cast

import finishing  # bristol-local: what done means for the board, one rule
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStyle,
    QStyleOptionComboBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .attachments import AttachmentBar
from .board_write import write
from .growing_edit import GrowingTextEdit
from .links import LinkBar, carried_summaries
from .record_dialog import LOG_FILTERS, STAGES, section_widget
from .segmented import SegmentedControl
from .settled_combo import fill_words
from .theme import (
    BLOCK_REASON_CHOICES,
    BLOCK_REASON_HINT,
    LAYOUT,
    SIZE_CHOICES,
    SIZE_HINT,
    STAGE_CHOICES,
    STATUS_CHOICES,
    TIER_CHOICES,
    TIER_HINT,
    C,
    _fmt_dt,
    _utcnow,
    fill_agents,
    fleet_agents,
    log_entries,
    relative_time,
    select_agent,
    space,
    type_size,
)


def _picker_width(combo: QComboBox) -> int:
    """How wide ``combo`` has to be to show its current value whole, in the
    style it is drawn in."""
    option = QStyleOptionComboBox()
    combo.initStyleOption(option)
    metrics = combo.fontMetrics()
    text = QSize(metrics.horizontalAdvance(combo.currentText()), metrics.height())
    return (
        combo.style().sizeFromContents(QStyle.ContentsType.CT_ComboBox, option, text, combo).width()
    )


class DetailPane(QWidget):
    """The board's right-hand pane. ``show_task`` / ``show_epic`` point it at a
    record; ``clear`` empties it. ``on_changed`` fires after any write so the
    host can refresh the board; ``on_collapse`` fires when the collapse control
    is used, and the host decides what that does to the splitter."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QWidget | None = None,
        on_changed: Callable[[], None] | None = None,
        on_collapse: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("detailPane")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(LAYOUT["detail_min_w"])

        self.conn = conn
        self.on_changed = on_changed
        self.on_collapse = on_collapse
        self.task_id: int | None = None
        self.epic_id: int | None = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(space("xl"), space("lg"), space("xl"), space("lg"))
        root.setSpacing(space("md"))

        # ----- header: number and title, and the collapse control -----------
        head = QHBoxLayout()
        head.setSpacing(space("md"))
        self.title = QLabel("")
        self.title.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(type_size("section"))
        title_font.setWeight(QFont.Weight.DemiBold)
        self.title.setFont(title_font)
        self.title.setObjectName("inspectorTitle")
        head.addWidget(self.title, 1)
        self.collapse_btn = QPushButton()
        self.collapse_btn.setObjectName("paneToggle")
        icons.tint(self.collapse_btn, "chevron-right", size=14)
        self.collapse_btn.setToolTip("Collapse the detail pane")
        self.collapse_btn.setAccessibleName("Collapse the detail pane")
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.clicked.connect(self._collapse)
        head.addWidget(self.collapse_btn, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)

        # ----- the live controls: the fields a card is worked with ----------
        self.controls = QWidget()
        grid = QGridLayout(self.controls)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(space("lg"))
        grid.setVerticalSpacing(space("sm"))

        self.status_combo = fill_words(QComboBox(), STATUS_CHOICES)
        self.stage_combo = fill_words(QComboBox(), STAGE_CHOICES)
        self.owner_combo = QComboBox()
        fill_agents(self.owner_combo, fleet_agents())
        self.epic_combo = QComboBox()
        self.size_combo = fill_words(QComboBox(), SIZE_CHOICES, hint=SIZE_HINT)
        self.tier_combo = fill_words(QComboBox(), TIER_CHOICES, hint=TIER_HINT)
        # Blocked says what kind of thing has stopped the card. Which card is the
        # Links section's job, and the prose is a comment under the Log.
        self.block_combo = fill_words(QComboBox(), BLOCK_REASON_CHOICES, hint=BLOCK_REASON_HINT)

        self._control_grid = grid
        self._control_columns = 0
        self._control_rows = []
        for caption, widget in (
            ("Status", self.status_combo),
            ("Stage", self.stage_combo),
            ("Owner", self.owner_combo),
            ("Epic", self.epic_combo),
            ("Tier", self.tier_combo),
            ("Size", self.size_combo),
            ("Blocked", self.block_combo),
        ):
            label = QLabel(caption)
            label.setObjectName("formCaption")
            self._control_rows.append((label, widget))
            widget.currentIndexChanged.connect(lambda _index: self._reflow_controls())
        self._reflow_controls()
        root.addWidget(self.controls)

        self.status_combo.currentIndexChanged.connect(
            lambda _index: self._write_placement("status", self.status_combo.currentData())
        )
        self.stage_combo.currentIndexChanged.connect(
            lambda _index: self._write_placement("stage", self.stage_combo.currentData())
        )
        self.owner_combo.currentIndexChanged.connect(
            lambda _index: self._write_field("assignee", self.owner_combo.currentData())
        )
        self.epic_combo.currentIndexChanged.connect(self._write_epic)
        self.size_combo.currentIndexChanged.connect(self._write_size)
        self.block_combo.currentIndexChanged.connect(self._write_block_reason)
        self.tier_combo.currentIndexChanged.connect(self._write_tier)

        # ----- the scrolling body: Description, Links, Log, Attributes ------
        self._scroll = QScrollArea()
        self._scroll.setObjectName("detailScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(space("md"))
        self._scroll.setWidget(body)
        root.addWidget(self._scroll, 1)

        desc_caption = QLabel("Description")
        desc_caption.setObjectName("formCaption")
        self._body_layout.addWidget(desc_caption)
        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        self.desc.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._body_layout.addWidget(self.desc)

        self._links_header = section_widget("Links")
        self._body_layout.addWidget(self._links_header)
        self.links = LinkBar(self.conn, author="user")
        self.links.header.setVisible(False)  # the section header above stands in
        self.links.on_open_issue = self.show_task
        self._body_layout.addWidget(self.links)
        # What the tickets this one waited on said as they finished. It sits
        # under Links because it is a reading of the `blocks` rows above it,
        # and it is read-only for the same reason: the text belongs to the
        # ticket that wrote it.
        self._handoff_header = section_widget("Carried Summaries")
        self._body_layout.addWidget(self._handoff_header)
        self.handoff_view = QTextEdit()
        self.handoff_view.setReadOnly(True)
        self._body_layout.addWidget(self.handoff_view)

        # Attachments are their own section, not a tail on Links.
        self._attach_header = section_widget("Attachments")
        self._body_layout.addWidget(self._attach_header)
        self.attachments = AttachmentBar(self.conn)
        self._body_layout.addWidget(self.attachments)
        # Controls of equal rank share a width, a height and an edge: the two
        # attach-context buttons take the wider one's size.
        shared = max(
            self.links.add_btn.sizeHint().width(), self.attachments.attach_btn.sizeHint().width()
        )
        self.links.add_btn.setFixedWidth(shared)
        self.attachments.attach_btn.setFixedWidth(shared)

        self._log_header = section_widget("Log")
        self._body_layout.addWidget(self._log_header)
        filter_row = QHBoxLayout()
        self.log_filter = SegmentedControl(LOG_FILTERS)
        self.log_filter.changed.connect(lambda _value: self._render_log())
        filter_row.addWidget(self.log_filter)
        filter_row.addStretch(1)
        self._body_layout.addLayout(filter_row)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(QFontMetrics(self.log_view.font()).lineSpacing() * 8)
        self._body_layout.addWidget(self.log_view, 1)

        self._body_layout.addWidget(section_widget("Attributes"))
        self._attr_grid = QGridLayout()
        self._attr_grid.setContentsMargins(0, 0, 0, 0)
        self._attr_grid.setHorizontalSpacing(space("xl"))
        self._attr_grid.setVerticalSpacing(space("sm"))
        self._body_layout.addLayout(self._attr_grid)

        # ----- the composer, pinned to the pane's foot -----------------------
        composer = QHBoxLayout()
        composer.setSpacing(space("sm"))
        self.comment_input = GrowingTextEdit(max_lines=6)
        self.comment_input.setPlaceholderText("Post a brief progress note…")
        self.comment_input.submitted.connect(self._post_comment)
        composer.addWidget(self.comment_input, 1)
        self.post_btn = QPushButton("Post")
        self.post_btn.clicked.connect(self._post_comment)
        # The composer grows upward from its foot, so the button keeps the
        # field's bottom edge rather than floating at its middle.
        composer.addWidget(self.post_btn, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(composer)

        self.clear()

    # ----- small builders ---------------------------------------------------

    def _set_attributes(self, pairs: list[tuple[str, str]]) -> None:
        """Rebuild the key/value grid: keys aligned in one muted column, values
        in the other."""
        while self._attr_grid.count():
            item = self._attr_grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        for row, (key, value) in enumerate(pairs):
            key_label = QLabel(key)
            key_label.setObjectName("metaText")
            value_label = QLabel(value)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._attr_grid.addWidget(
                key_label, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            self._attr_grid.addWidget(
                value_label, row, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
        self._attr_grid.setColumnStretch(1, 1)

    def _fit(self, view: QTextEdit, low_lines: int, high_lines: int | None) -> None:
        """Size a read-only view to what it contains, within a bound: at least a
        few lines so the section reads as present, and at most ``high_lines``
        where one is given, past which it scrolls inside its own field. With no
        upper bound the view is as tall as its text and the pane's own scroll
        is the only one.

        Called again on every resize, since a narrower pane rewraps the text
        into more lines than it was measured at."""
        document = view.document()
        width = view.viewport().width()
        if width > 0:
            document.setTextWidth(width)
        line = QFontMetrics(view.font()).lineSpacing()
        wanted = int(document.size().height()) + space("md") * 2
        low = line * low_lines
        high = wanted if high_lines is None else line * high_lines
        view.setFixedHeight(max(low, min(wanted, high)))
        view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
            if wanted > high
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    def _fit_description(self) -> None:
        # Unbounded: the card's own text scrolls with the pane, so the pane
        # carries one scroll bar rather than one inside another.
        self._fit(self.desc, 3, None)

    def _fit_handoffs(self) -> None:
        # Bounded at fourteen lines: the card's own text is the tallest thing
        # in the pane, and what it waited on reads under it.
        self._fit(self.handoff_view, 3, 14)

    def _reflow_controls(self) -> None:
        """Lay the pickers out two to a row where the pane is wide enough to
        show every current value whole, and one to a row where it is not."""
        grid = self._control_grid
        gap = grid.horizontalSpacing()
        caption = max(label.sizeHint().width() for label, _widget in self._control_rows)
        pair = caption + gap + max(_picker_width(widget) for _label, widget in self._control_rows)
        width = self.controls.width() or self.width()
        columns = 2 if 2 * pair + gap <= width else 1
        if columns == self._control_columns:
            return
        self._control_columns = columns
        for label, widget in self._control_rows:
            grid.removeWidget(label)
            grid.removeWidget(widget)
        for position, (label, widget) in enumerate(self._control_rows):
            row, column = divmod(position, columns)
            grid.addWidget(label, row, column * 2)
            grid.addWidget(widget, row, column * 2 + 1)
        for column in range(4):
            grid.setColumnStretch(column, 1 if column % 2 and column < 2 * columns else 0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._reflow_controls()
        if self.task_id is not None or self.epic_id is not None:
            self._fit_description()
            self._fit_handoffs()

    def _collapse(self) -> None:
        if callable(self.on_collapse):
            self.on_collapse()

    # ----- pointing the pane at a record ------------------------------------

    def clear(self) -> None:
        """No selection: placeholder title, controls dark, sections empty."""
        self.task_id = None
        self.epic_id = None
        self._loading = True
        self.title.setText("")
        self.controls.setVisible(False)
        self.desc.clear()
        self._fit_description()
        self.links.set_task(None)
        self.links.setVisible(False)
        self.attachments.set_task(None)
        self.attachments.setVisible(False)
        self._links_header.setVisible(False)
        self._attach_header.setVisible(False)
        self._handoff_header.setVisible(False)
        self.handoff_view.setVisible(False)
        self.handoff_view.clear()
        self.log_view.setPlainText("(Select an issue to see its log.)")
        self._set_attributes([])
        self._set_composer_enabled(False)
        self._loading = False

    def show_task(self, task_id: int) -> None:
        """Point the pane at a ticket. Also how a clicked issue link navigates,
        so a chain of related work is walkable in place."""
        try:
            row = self.conn.execute(
                "SELECT t.title, t.description, t.status, t.tier, e.name, "
                "COALESCE(t.assignee,'user'), COALESCE(t.reporter,'user'), "
                "COALESCE(t.estimate,''), e.id, t.created_at, t.updated_at, "
                "COALESCE(t.record_type,'build'), COALESCE(t.stage,'backlog'), "
                "t.epic_id, t.block_reason "
                "FROM task t LEFT JOIN epic e ON t.epic_id = e.id WHERE t.id = ?",
                (task_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return
        if row is None:
            return
        (
            title,
            desc,
            status,
            tier,
            epic_name,
            owner,
            originator,
            estimate,
            joined_epic_id,
            created_at,
            updated_at,
            record_type,
            stage,
            epic_id,
            block_reason,
        ) = row

        self._loading = True
        self.task_id = task_id
        self.epic_id = None

        self.title.setText(f"#{task_id} {title}")

        self.controls.setVisible(True)
        self.status_combo.setCurrentIndex(
            max(
                self.status_combo.findData(
                    status if status in ("todo", "doing", "done") else "todo"
                ),
                0,
            )
        )
        self.stage_combo.setCurrentIndex(
            max(self.stage_combo.findData(stage if stage in STAGES else "backlog"), 0)
        )
        self._select_owner(owner)
        self._load_epics(epic_id)
        size_index = self.size_combo.findData((estimate or "").upper())
        self.size_combo.setCurrentIndex(max(size_index, 0))
        tier_index = self.tier_combo.findData((tier or "").lower() or None)
        self.tier_combo.setCurrentIndex(max(tier_index, 0))
        block_index = self.block_combo.findData(block_reason)
        self.block_combo.setCurrentIndex(max(block_index, 0))

        self.desc.setPlainText(desc or "(No description narrative provided.)")
        self._fit_description()

        self._links_header.setVisible(True)
        self.links.setVisible(True)
        self.links.set_task(task_id)
        self._render_handoffs()
        self._attach_header.setVisible(True)
        self.attachments.setVisible(True)
        self.attachments.set_task(task_id)

        self._render_log()
        self._set_composer_enabled(True)

        record_kind = "Fix" if (record_type or "build").lower() == "fix" else "Build"
        self._set_attributes(
            [
                ("Issue #", str(task_id)),
                ("Record type", record_kind),
                ("Originator", originator),
                ("Created", _fmt_dt(created_at)),
                ("Modified", _fmt_dt(updated_at)),
            ]
        )
        self._loading = False

    def show_epic(self, epic_id: int) -> None:
        try:
            row = self.conn.execute(
                "SELECT name, description, type, status FROM epic WHERE id=?", (epic_id,)
            ).fetchone()
        except sqlite3.OperationalError:
            return
        if row is None:
            return
        name, desc, epic_type, epic_status = row
        self.clear()
        self._loading = True
        self.epic_id = epic_id
        self.title.setText(f"Epic #{epic_id} {name}")
        self.desc.setPlainText(desc or "(No details provided)")
        self._fit_description()
        self._set_attributes(
            [
                ("Epic #", str(epic_id)),
                ("Type", epic_type or "—"),
                ("Status", epic_status or "—"),
            ]
        )
        self._loading = False

    def _select_owner(self, value: str | None) -> None:
        """A legacy owner outside the fleet list is added rather than silently
        rewritten — same contract as the dialog's picker."""
        select_agent(self.owner_combo, value)

    def _load_epics(self, current_epic_id: int | None) -> None:
        """Only active epics are offered, plus the one this ticket already
        carries even when done, so an edit never silently unlinks it."""
        self.epic_combo.blockSignals(True)
        self.epic_combo.clear()
        self.epic_combo.addItem("(no epic)", None)
        try:
            for eid, ename, estatus in self.conn.execute(
                "SELECT id, name, status FROM epic ORDER BY id"
            ).fetchall():
                if (estatus or "").lower() in ("completed", "done") and eid != current_epic_id:
                    continue
                self.epic_combo.addItem(ename, eid)
        except sqlite3.OperationalError:
            pass
        index = self.epic_combo.findData(current_epic_id)
        self.epic_combo.setCurrentIndex(max(index, 0))
        self.epic_combo.blockSignals(False)

    def _set_composer_enabled(self, enabled: bool) -> None:
        self.comment_input.setEnabled(enabled)
        self.post_btn.setEnabled(enabled)
        if not enabled:
            self.comment_input.clear()

    # ----- writes: one field at a time, down the shared path ----------------

    def _write_field(self, field: str, value: object) -> None:
        """One column, one UPDATE, on the connection whose triggers write the
        change log — the same recording a dialog save or a board drag gets."""
        if self._loading or self.task_id is None:
            return
        task_id = self.task_id
        if not write(
            self.conn,
            self,
            f"The change to #{task_id}",
            lambda: self.conn.execute(f"UPDATE task SET {field}=? WHERE id=?", (value, task_id)),
        ):
            self.show_task(task_id)
            return
        self._after_write()

    def _write_placement(self, field: str, value: str) -> None:
        """Status and stage moves re-seat the card at the bottom of its
        destination list, exactly as the dialog and a board drop do; a move to
        done stamps closed_at and a move out of done clears it."""
        if self._loading or self.task_id is None:
            return
        task_id = self.task_id

        def move() -> None:
            current = self.conn.execute(
                "SELECT status, COALESCE(stage,'backlog') FROM task WHERE id=?", (task_id,)
            ).fetchone()
            if current is None:
                return
            status, stage = current
            new_status = value if field == "status" else status
            new_stage = value if field == "stage" else stage
            if new_stage == "active":
                base = self.conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM task "
                    "WHERE stage='active' AND status=?",
                    (new_status,),
                ).fetchone()[0]
            else:
                base = self.conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage=?", (new_stage,)
                ).fetchone()[0]
            closed_at = _utcnow() if new_status == "done" else None
            # A finished card is not blocked; moving out of done leaves whatever
            # reason it had, since nothing here can know it was cleared.
            if new_status == "done":
                self.conn.execute(
                    "UPDATE task SET status=?, stage=?, sort_order=?, closed_at=?, "
                    "block_reason=NULL WHERE id=?",
                    (new_status, new_stage, base + 1, closed_at, task_id),
                )
            else:
                self.conn.execute(
                    "UPDATE task SET status=?, stage=?, sort_order=?, closed_at=? WHERE id=?",
                    (new_status, new_stage, base + 1, closed_at, task_id),
                )
            # A status move is where done means something for the board: a
            # standing card archives itself, a project card waits in Done for
            # its epic to close, and a card taken out of done comes back. A
            # stage move the user made by hand is left as they made it.
            if field == "status" and new_status != status:
                if new_status == "done":
                    finishing.finish(self.conn, task_id)
                else:
                    finishing.reopen(self.conn, task_id)

        if not write(self.conn, self, f"The move of #{task_id}", move):
            self.show_task(task_id)
            return
        self._after_write()

    def _write_epic(self, *args: object) -> None:
        if self._loading or self.task_id is None:
            return
        self._write_field("epic_id", self.epic_combo.currentData())

    def _write_size(self, *args: object) -> None:
        if self._loading or self.task_id is None:
            return
        self._write_field("estimate", self.size_combo.currentData() or None)

    def _write_block_reason(self, *args: object) -> None:
        if self._loading or self.task_id is None:
            return
        self._write_field("block_reason", self.block_combo.currentData())

    def _write_tier(self, *args: object) -> None:
        if self._loading or self.task_id is None:
            return
        self._write_field("tier", self.tier_combo.currentData())

    def _after_write(self) -> None:
        """Refresh what a write changes on screen: the Modified attribute and
        the log here, the board through the host's callback."""
        if self.task_id is not None:
            row = self.conn.execute(
                "SELECT updated_at FROM task WHERE id=?", (self.task_id,)
            ).fetchone()
            if row is not None:
                item = self._attr_grid.itemAtPosition(4, 1)
                if item is not None and item.widget() is not None:
                    cast(QLabel, item.widget()).setText(_fmt_dt(row[0]))
            self._render_log()
        if callable(self.on_changed):
            self.on_changed()

    # ----- carried summaries ------------------------------------------------

    def _render_handoffs(self, *args: object) -> None:
        """Show what each finished blocker said as it closed, oldest first.

        Read live from the `blocks` rows and those tickets' own logs, so the
        section appears when a blocker reaches done and changes when its last
        comment is edited. A ticket nothing finished ahead of shows no section
        at all rather than an empty one."""
        entries = carried_summaries(self.conn, self.task_id)
        self._handoff_header.setVisible(bool(entries))
        self.handoff_view.setVisible(bool(entries))
        if not entries:
            self.handoff_view.clear()
            return
        parts: list[str] = []
        for entry in entries:
            head = html.escape(f"#{entry['id']} {entry['title']}")
            author = html.escape(entry["author"])
            when = html.escape(relative_time(entry["at"]))
            body = html.escape(entry["body"]).replace("\n", "<br>")
            parts.append(
                f'<table width="100%" cellspacing="0" '
                f'cellpadding="{space("md")}" '
                f'style="margin-bottom:{space("sm")}px">'
                f'<tr><td style="background-color:{C["LIST_BG"]};">'
                f'<span style="color:{C["INK"]}"><b>{head}</b></span><br>'
                f'<span style="color:{C["INK_SOFT"]}">{author} · {when}</span><br>'
                f'<span style="color:{C["INK"]}">{body}</span>'
                f"</td></tr></table>"
            )
        self.handoff_view.setHtml("".join(parts))
        self._fit_handoffs()

    # ----- the log timeline -------------------------------------------------

    def _render_log(self, *args: object) -> None:
        if self.task_id is None:
            self.log_view.setPlainText("(Select an issue to see its log.)")
            return
        entries = log_entries(
            self.conn,
            self.task_id,
            comments=self.log_filter.value() in ("all", "comments"),
            changes=self.log_filter.value() in ("all", "changes"),
        )
        if not entries:
            self.log_view.setPlainText("(Nothing to show.)")
            return
        parts: list[str] = []
        for entry in entries:
            author = html.escape(entry["author"])
            when = html.escape(relative_time(entry["at"]))
            if entry["kind"] == "comment":
                body = html.escape(entry["body"]).replace("\n", "<br>")
                parts.append(
                    f'<table width="100%" cellspacing="0" '
                    f'cellpadding="{space("md")}" '
                    f'style="margin-bottom:{space("sm")}px">'
                    f'<tr><td style="background-color:{C["LIST_BG"]};">'
                    f'<span style="color:{C["INK"]}"><b>{author}</b></span>'
                    f"&nbsp;&nbsp;"
                    f'<span style="color:{C["INK_SOFT"]}">{when}</span><br>'
                    f'<span style="color:{C["INK"]}">{body}</span>'
                    f"</td></tr></table>"
                )
            else:
                field = html.escape(entry["field"])
                value = html.escape(entry["value"])
                parts.append(
                    f'<div style="color:{C["INK_SOFT"]}; '
                    f'margin-bottom:{space("xs")}px">'
                    f"{author} · {field}: {value} · {when}</div>"
                )
        self.log_view.setHtml("".join(parts))

    def refresh_theme(self) -> None:
        """Re-render what bakes palette values in: the timeline and the carried
        summaries, both of which are HTML with colours resolved at build time."""
        if self.task_id is not None:
            self._render_log()
            self._render_handoffs()

    def _post_comment(self) -> None:
        if self.task_id is None:
            return
        body = self.comment_input.text().strip()
        if not body:
            return
        task_id = self.task_id
        if not write(
            self.conn,
            self,
            f"The comment on #{task_id}",
            lambda: self.conn.execute(
                "INSERT INTO issue_log (task_id, author, body, created_at) VALUES (?,?,?,?)",
                (task_id, "user", body, _utcnow()),
            ),
        ):
            return
        self.comment_input.clear()
        self._render_log()
