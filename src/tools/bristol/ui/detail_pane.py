"""ui/detail_pane.py — the detail pane: where a selected card is read and
edited in place.

``DetailPane`` sits right of the board splitter. Status, stage, owner, epic,
effort and pressure are live labelled controls, two to a row: a change writes
through the same connection every other writer uses, so the database triggers
record a pane edit exactly as they record a dialog edit or a board drag. The
fields nobody edits — issue number, record type, originator, created,
modified — render as an aligned key/value grid under Attributes.

The pane reads Title, Description, Links, Log, Attributes top to bottom, each
under a section header and hairline. The description is sized to its content
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

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .attachments import AttachmentBar
from .links import LinkBar
from .record_dialog import STAGES
from .theme import (
    C,
    EFFORT_WORDS,
    FLEET_AGENTS,
    LAYOUT,
    _fmt_dt,
    _get_epic_badge,
    _utcnow,
    log_entries,
    relative_time,
    space,
    type_size,
)

# How long a run of pressure-spinner clicks may continue before the value is
# written, so stepping 40 → 70 lands as one change-log entry rather than six.
PRESSURE_SETTLE_MS = 600


class DetailPane(QWidget):
    """The board's right-hand pane. ``show_task`` / ``show_epic`` point it at a
    record; ``clear`` empties it. ``on_changed`` fires after any write so the
    host can refresh the board; ``on_collapse`` fires when the collapse control
    is used, and the host decides what that does to the splitter."""

    def __init__(self, conn: sqlite3.Connection, parent=None,
                 on_changed=None, on_collapse=None) -> None:
        super().__init__(parent)
        self.setObjectName("detailPane")
        self.setAttribute(Qt.WA_StyledBackground, True)
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
        self.title = QLabel("Select a card to read and edit it here.")
        self.title.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(type_size("section"))
        title_font.setBold(True)
        self.title.setFont(title_font)
        self.title.setObjectName("inspectorTitle")
        head.addWidget(self.title, 1)
        self.collapse_btn = QPushButton("❯")
        self.collapse_btn.setObjectName("paneToggle")
        self.collapse_btn.setToolTip("Collapse the detail pane")
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.clicked.connect(self._collapse)
        head.addWidget(self.collapse_btn, 0, Qt.AlignTop)
        root.addLayout(head)

        # ----- the live controls: the fields a card is worked with ----------
        self.controls = QWidget()
        grid = QGridLayout(self.controls)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(space("lg"))
        grid.setVerticalSpacing(space("sm"))

        self.status_combo = QComboBox()
        self.status_combo.addItems(["todo", "doing", "done"])
        self.stage_combo = QComboBox()
        self.stage_combo.addItems(STAGES)
        self.owner_combo = QComboBox()
        self.owner_combo.addItems(FLEET_AGENTS)
        self.epic_combo = QComboBox()
        self.effort_combo = QComboBox()
        self.effort_combo.addItem("not sized", "")
        for code, word in EFFORT_WORDS.items():
            self.effort_combo.addItem(word, code)
        self.pressure_spin = QSpinBox()
        self.pressure_spin.setRange(0, 100)

        for position, (caption, widget) in enumerate((
            ("Status", self.status_combo),
            ("Stage", self.stage_combo),
            ("Owner", self.owner_combo),
            ("Epic", self.epic_combo),
            ("Effort", self.effort_combo),
            ("Pressure", self.pressure_spin),
        )):
            row, column = divmod(position, 2)
            label = QLabel(caption)
            label.setObjectName("formCaption")
            grid.addWidget(label, row, column * 2)
            grid.addWidget(widget, row, column * 2 + 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        root.addWidget(self.controls)

        self.status_combo.currentTextChanged.connect(
            lambda value: self._write_placement("status", value))
        self.stage_combo.currentTextChanged.connect(
            lambda value: self._write_placement("stage", value))
        self.owner_combo.currentTextChanged.connect(
            lambda value: self._write_field("assignee", value))
        self.epic_combo.currentIndexChanged.connect(self._write_epic)
        self.effort_combo.currentIndexChanged.connect(self._write_effort)
        self._pressure_timer = QTimer(self)
        self._pressure_timer.setSingleShot(True)
        self._pressure_timer.setInterval(PRESSURE_SETTLE_MS)
        self._pressure_timer.timeout.connect(self._write_pressure)
        self.pressure_spin.valueChanged.connect(self._pressure_moved)

        # ----- the scrolling body: Description, Links, Log, Attributes ------
        self._scroll = QScrollArea()
        self._scroll.setObjectName("detailScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(space("md"))
        self._scroll.setWidget(body)
        root.addWidget(self._scroll, 1)

        self._body_layout.addWidget(self._section("Description"))
        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        self.desc.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._body_layout.addWidget(self.desc)

        self._links_header = self._section("Links")
        self._body_layout.addWidget(self._links_header)
        self.links = LinkBar(self.conn, author="user")
        self.links.header.setVisible(False)  # the section header above stands in
        self.links.on_open_issue = self.show_task
        self._body_layout.addWidget(self.links)
        self.attachments = AttachmentBar(self.conn)
        self._body_layout.addWidget(self.attachments)
        # Controls of equal rank share a width, a height and an edge: the two
        # attach-context buttons take the wider one's size.
        shared = max(self.links.add_btn.sizeHint().width(),
                     self.attachments.attach_btn.sizeHint().width())
        self.links.add_btn.setFixedWidth(shared)
        self.attachments.attach_btn.setFixedWidth(shared)

        self._log_header = self._section("Log")
        self._body_layout.addWidget(self._log_header)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(space("lg"))
        self.log_show_comments = QCheckBox("Comments")
        self.log_show_comments.setChecked(True)
        self.log_show_comments.toggled.connect(self._render_log)
        self.log_show_changes = QCheckBox("Changes")
        self.log_show_changes.setChecked(True)
        self.log_show_changes.toggled.connect(self._render_log)
        filter_row.addWidget(self.log_show_comments)
        filter_row.addWidget(self.log_show_changes)
        filter_row.addStretch(1)
        self._body_layout.addLayout(filter_row)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(
            QFontMetrics(self.log_view.font()).lineSpacing() * 8)
        self._body_layout.addWidget(self.log_view, 1)

        self._body_layout.addWidget(self._section("Attributes"))
        self._attr_grid = QGridLayout()
        self._attr_grid.setContentsMargins(0, 0, 0, 0)
        self._attr_grid.setHorizontalSpacing(space("xl"))
        self._attr_grid.setVerticalSpacing(space("sm"))
        self._body_layout.addLayout(self._attr_grid)

        # ----- the composer, pinned to the pane's foot -----------------------
        composer = QHBoxLayout()
        composer.setSpacing(space("sm"))
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Post a brief progress note…")
        self.comment_input.returnPressed.connect(self._post_comment)
        composer.addWidget(self.comment_input, 1)
        self.post_btn = QPushButton("Post")
        self.post_btn.clicked.connect(self._post_comment)
        composer.addWidget(self.post_btn)
        root.addLayout(composer)

        self.clear()

    # ----- small builders ---------------------------------------------------

    @staticmethod
    def _section(name: str) -> QWidget:
        """A section header and its hairline, the one treatment every pane
        section sits under."""
        box = QWidget()
        column = QVBoxLayout(box)
        column.setContentsMargins(0, space("md"), 0, 0)
        column.setSpacing(space("xs"))
        label = QLabel(name)
        label.setObjectName("sectionHeader")
        rule = QFrame()
        rule.setObjectName("sectionRule")
        rule.setFrameShape(QFrame.HLine)
        rule.setFixedHeight(1)
        column.addWidget(label)
        column.addWidget(rule)
        return box

    def _set_attributes(self, pairs: list[tuple[str, str]]) -> None:
        """Rebuild the key/value grid: keys aligned in one muted column, values
        in the other."""
        while self._attr_grid.count():
            item = self._attr_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for row, (key, value) in enumerate(pairs):
            key_label = QLabel(key)
            key_label.setObjectName("metaText")
            value_label = QLabel(value)
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._attr_grid.addWidget(key_label, row, 0, Qt.AlignLeft | Qt.AlignTop)
            self._attr_grid.addWidget(value_label, row, 1, Qt.AlignLeft | Qt.AlignTop)
        self._attr_grid.setColumnStretch(1, 1)

    def _fit_description(self) -> None:
        """Size the description to what it holds, within a bound: at least a few
        lines so the section reads as present, at most a screenful so a long
        ticket scrolls inside the field instead of pushing the log away."""
        document = self.desc.document()
        width = self.desc.viewport().width()
        if width > 0:
            document.setTextWidth(width)
        line = QFontMetrics(self.desc.font()).lineSpacing()
        wanted = int(document.size().height()) + space("md") * 2
        low, high = line * 3, line * 18
        self.desc.setFixedHeight(max(low, min(wanted, high)))
        self.desc.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded if wanted > high else Qt.ScrollBarAlwaysOff)

    def resizeEvent(self, event):  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        if self.task_id is not None or self.epic_id is not None:
            self._fit_description()

    def _collapse(self) -> None:
        if callable(self.on_collapse):
            self.on_collapse()

    # ----- pointing the pane at a record ------------------------------------

    def clear(self) -> None:
        """No selection: placeholder title, controls dark, sections empty."""
        if self._pressure_timer.isActive():
            self._pressure_timer.stop()
            self._write_pressure()
        self.task_id = None
        self.epic_id = None
        self._loading = True
        self.title.setText("Select a card to read and edit it here.")
        self.controls.setVisible(False)
        self.desc.clear()
        self._fit_description()
        self.links.set_task(None)
        self.links.setVisible(False)
        self.attachments.set_task(None)
        self.attachments.setVisible(False)
        self._links_header.setVisible(False)
        self.log_view.setPlainText("(Select an issue to see its log.)")
        self._set_attributes([])
        self._set_composer_enabled(False)
        self._loading = False

    def show_task(self, task_id: int) -> None:
        """Point the pane at a ticket. Also how a clicked issue link navigates,
        so a chain of related work is walkable in place."""
        # A pressure edit still waiting on its debounce belongs to the card
        # leaving the pane; land it before anything is repointed.
        if self._pressure_timer.isActive():
            self._pressure_timer.stop()
            self._write_pressure()
        try:
            row = self.conn.execute(
                "SELECT t.title, t.description, t.status, t.pressure, e.name, "
                "COALESCE(t.assignee,'user'), COALESCE(t.reporter,'user'), "
                "COALESCE(t.estimate,''), e.id, t.created_at, t.updated_at, "
                "COALESCE(t.record_type,'build'), COALESCE(t.stage,'backlog'), "
                "t.epic_id "
                "FROM task t LEFT JOIN epic e ON t.epic_id = e.id WHERE t.id = ?",
                (task_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return
        if row is None:
            return
        (title, desc, status, pressure, epic_name, owner, originator, estimate,
         joined_epic_id, created_at, updated_at, record_type, stage,
         epic_id) = row

        self._loading = True
        self.task_id = task_id
        self.epic_id = None

        badge = _get_epic_badge(epic_name, joined_epic_id)
        self.title.setText(f"#{task_id} {badge}{title}")

        self.controls.setVisible(True)
        self.status_combo.setCurrentText(
            status if status in ("todo", "doing", "done") else "todo")
        self.stage_combo.setCurrentText(stage if stage in STAGES else "backlog")
        self._select_owner(owner)
        self._load_epics(epic_id)
        effort_index = self.effort_combo.findData((estimate or "").upper())
        self.effort_combo.setCurrentIndex(max(effort_index, 0))
        self.pressure_spin.setValue(pressure or 0)

        self.desc.setPlainText(desc or "(No description narrative provided.)")
        self._fit_description()

        self._links_header.setVisible(True)
        self.links.setVisible(True)
        self.links.set_task(task_id)
        self.attachments.setVisible(True)
        self.attachments.set_task(task_id)

        self._render_log()
        self._set_composer_enabled(True)

        record_kind = "Fix" if (record_type or "build").lower() == "fix" else "Build"
        self._set_attributes([
            ("Issue #", str(task_id)),
            ("Record type", record_kind),
            ("Originator", originator),
            ("Created", _fmt_dt(created_at)),
            ("Modified", _fmt_dt(updated_at)),
        ])
        self._loading = False

    def show_epic(self, epic_id: int) -> None:
        try:
            row = self.conn.execute(
                "SELECT name, description, type, status FROM epic WHERE id=?",
                (epic_id,)).fetchone()
        except sqlite3.OperationalError:
            return
        if row is None:
            return
        name, desc, epic_type, epic_status = row
        self.clear()
        self._loading = True
        self.epic_id = epic_id
        self.title.setText(f"[Epic #{epic_id}] {name}")
        self.desc.setPlainText(desc or "(No details provided)")
        self._fit_description()
        self._set_attributes([
            ("Epic #", str(epic_id)),
            ("Type", epic_type or "—"),
            ("Status", epic_status or "—"),
        ])
        self._loading = False

    def _select_owner(self, value: str | None) -> None:
        """A legacy owner outside the fleet list is added rather than silently
        rewritten — same contract as the dialog's picker."""
        value = (value or "user").strip() or "user"
        index = self.owner_combo.findText(value)
        if index < 0:
            self.owner_combo.addItem(value)
            index = self.owner_combo.findText(value)
        self.owner_combo.setCurrentIndex(index)

    def _load_epics(self, current_epic_id: int | None) -> None:
        """Only active epics are offered, plus the one this ticket already
        carries even when done, so an edit never silently unlinks it."""
        self.epic_combo.blockSignals(True)
        self.epic_combo.clear()
        self.epic_combo.addItem("(no epic)", None)
        try:
            for eid, ename, estatus in self.conn.execute(
                    "SELECT id, name, status FROM epic ORDER BY id").fetchall():
                if (estatus or "").lower() in ("completed", "done") \
                        and eid != current_epic_id:
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

    def _write_field(self, field: str, value) -> None:
        """One column, one UPDATE, on the connection whose triggers write the
        change log — the same recording a dialog save or a board drag gets."""
        if self._loading or self.task_id is None:
            return
        try:
            self.conn.execute(
                f"UPDATE task SET {field}=? WHERE id=?", (value, self.task_id))
            self.conn.commit()
        except sqlite3.OperationalError:
            return
        self._after_write()

    def _write_placement(self, field: str, value: str) -> None:
        """Status and stage moves re-seat the card at the bottom of its
        destination list, exactly as the dialog and a board drop do; a move to
        done stamps closed_at and a move out of done clears it."""
        if self._loading or self.task_id is None:
            return
        try:
            current = self.conn.execute(
                "SELECT status, COALESCE(stage,'backlog') FROM task WHERE id=?",
                (self.task_id,)).fetchone()
            if current is None:
                return
            status, stage = current
            new_status = value if field == "status" else status
            new_stage = value if field == "stage" else stage
            if new_stage == "active":
                base = self.conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM task "
                    "WHERE stage='active' AND status=?", (new_status,)).fetchone()[0]
            else:
                base = self.conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage=?",
                    (new_stage,)).fetchone()[0]
            closed_at = _utcnow() if new_status == "done" else None
            self.conn.execute(
                "UPDATE task SET status=?, stage=?, sort_order=?, closed_at=? "
                "WHERE id=?",
                (new_status, new_stage, base + 1, closed_at, self.task_id))
            self.conn.commit()
        except sqlite3.OperationalError:
            return
        self._after_write()

    def _write_epic(self, *args) -> None:
        if self._loading or self.task_id is None:
            return
        self._write_field("epic_id", self.epic_combo.currentData())

    def _write_effort(self, *args) -> None:
        if self._loading or self.task_id is None:
            return
        self._write_field("estimate", self.effort_combo.currentData() or None)

    def _pressure_moved(self, *args) -> None:
        if self._loading or self.task_id is None:
            return
        self._pressure_timer.start()

    def _write_pressure(self) -> None:
        if self.task_id is None:
            return
        self._write_field("pressure", self.pressure_spin.value())

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
                    item.widget().setText(_fmt_dt(row[0]))
            self._render_log()
        if callable(self.on_changed):
            self.on_changed()

    # ----- the log timeline -------------------------------------------------

    def _render_log(self, *args) -> None:
        if self.task_id is None:
            self.log_view.setPlainText("(Select an issue to see its log.)")
            return
        entries = log_entries(
            self.conn, self.task_id,
            comments=self.log_show_comments.isChecked(),
            changes=self.log_show_changes.isChecked(),
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
                    f'&nbsp;&nbsp;'
                    f'<span style="color:{C["INK_SOFT"]}">{when}</span><br>'
                    f'<span style="color:{C["INK"]}">{body}</span>'
                    f'</td></tr></table>')
            else:
                field = html.escape(entry["field"])
                value = html.escape(entry["value"])
                parts.append(
                    f'<div style="color:{C["INK_SOFT"]}; '
                    f'margin-bottom:{space("xs")}px">'
                    f'{author} · {field}: {value} · {when}</div>')
        self.log_view.setHtml("".join(parts))

    def refresh_theme(self) -> None:
        """Re-render what bakes palette values in: the timeline HTML."""
        if self.task_id is not None:
            self._render_log()

    def _post_comment(self) -> None:
        if self.task_id is None:
            return
        body = self.comment_input.text().strip()
        if not body:
            return
        try:
            self.conn.execute(
                "INSERT INTO issue_log (task_id, author, body, created_at) "
                "VALUES (?,?,?,?)",
                (self.task_id, "user", body, _utcnow()),
            )
            self.conn.commit()
        except sqlite3.OperationalError:
            return
        self.comment_input.clear()
        self._render_log()
