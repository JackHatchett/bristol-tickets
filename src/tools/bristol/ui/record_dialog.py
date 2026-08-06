"""ui/record_dialog.py — the unified create/edit dialog.

``UnifiedRecordDialog`` is a single modal that handles two record kinds (Task /
Issue, Epic), showing/hiding the relevant field rows as the Kind combo changes.
It reads and writes the database directly and commits on save/delete. The caller
pattern is: construct, ``exec()``, and on ``QDialog.Accepted`` call
``save_data()``.

Kanban model: a task carries a **Stage** (backlog | active |
archive — which tab it lives in) alongside its **Status** (todo | doing | done —
the board column). The dialog exposes both; there is no Sprint kind or Sprint
Link. Saving re-seats a task at the bottom of its
destination list (task.sort_order) whenever its stage or status changes.

The detail pane edits a card's placement fields in place; what remains this
dialog's alone is stated in ``ui/README.md``.
"""

from __future__ import annotations

import os
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .attachments import AttachmentBar
from .links import LinkBar, remove_links_for_task
from .theme import (
    FLEET_AGENTS,
    LAYOUT,
    _mono_font,
    _utcnow,
    log_lines,
    space,
    type_size,
)

# ---------------------------------------------------------------------------
# Record-type description templates
# ---------------------------------------------------------------------------
# A ticket is one of two record types. A *Build* is a thing to build; its
# description is a Story plus Given/When/Then acceptance criteria. A *Fix* is a
# broken thing; its description states the Expected behaviour and the Observed
# divergence. These skeletons pre-populate the Description field so both the
# user and the agents fill in the same shape every time. They are mad-libs:
# constant words with short "[bracketed]" fill-in blanks — replace the whole
# bracket (including the brackets) with your own words. Keep these strings in
# sync with the format rules in src/playbooks/_shared/manage_tickets.md (§Record types).
BUILD_TEMPLATE = (
    "Story:\n"
    "As [owner] I want [what should change] so that [why it matters].\n"
    "\n"
    "Acceptance Criteria:\n"
    "1. Given [starting state], when [action], then [expected result].\n"
)

FIX_TEMPLATE = (
    "Expected:\n"
    "Given [precondition], when [action], then [expected result].\n"
    "\n"
    "Observed:\n"
    "[what happened instead]\n"
)

RECORD_TEMPLATES = {"build": BUILD_TEMPLATE, "fix": FIX_TEMPLATE}

STAGES = ["backlog", "active", "archive"]


def section_widget(name: str) -> QWidget:
    """A section header over its hairline — the one treatment every grouped
    surface opens with, in this dialog and the detail pane alike."""
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


def _captioned(caption: QLabel, widget, stretch: bool = False) -> QWidget:
    """A formCaption above its control — the field treatment the detail pane
    established. ``stretch`` lets a full-width field take its whole row."""
    box = QWidget()
    column = QVBoxLayout(box)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(space("xs"))
    caption.setObjectName("formCaption")
    column.addWidget(caption)
    if stretch:
        column.addWidget(widget)
    else:
        column.addWidget(widget, 0, Qt.AlignLeft)
    return box


def _is_boilerplate(text: str | None) -> bool:
    """True when the Description is safe to (re)fill with a template: it is
    empty, or it still exactly equals one of the templates (i.e. the user has
    not typed anything of their own). Any custom text — even a single edited
    character — makes this False, so user input is never clobbered."""
    t = (text or "").strip()
    if not t:
        return True
    return t in (BUILD_TEMPLATE.strip(), FIX_TEMPLATE.strip())


class UnifiedRecordDialog(QDialog):
    def __init__(self, parent, conn, mode="task", record_id: int | None = None,
                 initial_status: str | None = None, epic_id: int | None = None,
                 initial_stage: str | None = None):
        super().__init__(parent)
        self.conn = conn
        self.mode = mode
        self.record_id = record_id
        self.initial_status = initial_status
        self.initial_stage = initial_stage
        self.fallback_epic_id = epic_id
        # Remembered so save_data can tell whether stage/status changed and thus
        # whether to re-seat the task in its destination list.
        self._loaded_stage = None
        self._loaded_status = None

        self.setWindowTitle("Edit Record" if record_id else "Create New Record")
        self.setMinimumWidth(LAYOUT["dialog_min_w"])

        # The dialog is a fixed frame with a SCROLLING body. Everything that can
        # grow — the form, links, log, attachments — lives inside the scroll
        # area; the OK / Cancel / Delete row is deliberately outside it, pinned
        # to the bottom, so the save button can never be pushed off-screen by a
        # ticket that happens to carry a lot of links or a long description.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        # No visible bars: the wheel/trackpad still scrolls, and a permanent
        # gutter on a form this narrow is more intrusive than the thing it fixes.
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        self._scroll.setWidget(body)
        outer.addWidget(self._scroll, 1)

        self.main_layout = QVBoxLayout(body)
        self.main_layout.setContentsMargins(space("xl"), space("lg"),
                                            space("xl"), space("lg"))
        self.main_layout.setSpacing(space("md"))

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Task / Issue", "Epic"])
        self.type_combo.setCurrentIndex(1 if mode == "epic" else 0)
        if record_id is not None:
            self.type_combo.setEnabled(False)

        # Record Type: Build vs Fix — drives which description template
        # pre-populates below. Task-only; hidden for epics.
        self.recordtype_combo = QComboBox()
        self.recordtype_combo.addItem("Build", "build")
        self.recordtype_combo.addItem("Fix", "fix")
        self.recordtype_label = QLabel("Record Type")

        # The title takes the dialog's full width, so a real title reads
        # whole rather than scrolling inside a short box.
        self.title_label = QLabel("Title *")
        self.title_edit = QLineEdit()

        # The description's height comes from the mad-lib skeleton it opens
        # with; its face is monospace only while the text still IS that
        # skeleton, and switches to the body face once prose replaces it.
        self.desc_edit = QTextEdit()
        mono_line = QFontMetrics(_mono_font()).lineSpacing()
        self.desc_edit.setMinimumHeight(mono_line * 8)
        self.desc_edit.setMaximumHeight(mono_line * 11)
        self._desc_is_mono = True
        self.desc_edit.setFont(_mono_font())
        self.desc_edit.textChanged.connect(self._sync_desc_font)
        self.desc_label = QLabel("Description")

        # Stage (backlog | active | archive) — which tab the task lives in;
        # orthogonal to Status.
        self.stage_combo = QComboBox()
        self.stage_combo.addItems(STAGES)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["todo", "doing", "done"])
        if initial_status:
            self.status_combo.setCurrentText(initial_status)

        # Owner is a picker of the fleet agents + 'user' so ownership
        # is always a real, spellable slug.
        self.owner_edit = QComboBox()
        self.owner_edit.addItems(FLEET_AGENTS)
        self.originator_edit = QLineEdit()

        if record_id is None:
            # A new task opens on the stage of the tab Create was pressed on
            # (main_window._stage_for_current_tab), appended to the bottom of
            # that list on save.
            self.stage_combo.setCurrentText(initial_stage or "backlog")
            self._select_owner("user")
            active_agent = os.environ.get("AGENT_NAME", "user")
            self.originator_edit.setText(active_agent)

        # Only ACTIVE epics are offered for linking — a done epic
        # shouldn't collect new work. An existing task already linked to a done
        # epic keeps that link: _load_data re-adds its epic to the combo so
        # editing the task doesn't silently unlink it.
        self.epic_combo = QComboBox()
        self.epic_combo.addItem("(no epic)", None)
        for eid, ename, estatus in conn.execute(
                "SELECT id, name, status FROM epic ORDER BY id").fetchall():
            if (estatus or "").lower() in ("completed", "done"):
                continue
            self.epic_combo.addItem(ename, eid)

        self.pressure_spin = QSpinBox()
        self.pressure_spin.setRange(0, 100)

        # Effort: how much of a full usage budget this card would take. The
        # scale and its anchors are defined once in src/app.md (Effort sizing);
        # the blank first entry means "not sized yet".
        self.estimate_combo = QComboBox()
        for value, label in (("", "not sized"),
                             ("S", "S — under a tenth of a budget"),
                             ("M", "M — a tenth to about half"),
                             ("L", "L — half a budget or more"),
                             ("XL", "XL — more than one budget; split it")):
            self.estimate_combo.addItem(label, value)

        self.epic_type_combo = QComboBox()
        self.epic_type_combo.addItems(["Epic (bounded)", "Epic (unbounded)"])
        self.epic_status_combo = QComboBox()
        self.epic_status_combo.addItems(["not started", "in progress", "completed", "on hold"])

        # Every short field sits at the width its contents ask for: a combo
        # sizes to its longest entry, the pressure spinner to three digits, the
        # originator to the longest agent slug. Only the title and description
        # keep an Expanding policy and take the dialog's width.
        metrics = QFontMetrics(self.font())
        for combo in (self.type_combo, self.recordtype_combo, self.stage_combo,
                      self.status_combo, self.owner_edit, self.epic_combo,
                      self.estimate_combo, self.epic_type_combo,
                      self.epic_status_combo):
            combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            combo.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.pressure_spin.setMaximumWidth(
            metrics.horizontalAdvance("100") + space("2xl") * 2)
        self.originator_edit.setMaximumWidth(
            max(metrics.horizontalAdvance(slug) for slug in FLEET_AGENTS)
            + space("2xl") * 2)

        # Every group opens with a section header over a hairline, and every
        # field is a formCaption above its control, two to a row — the same
        # vocabulary the detail pane established. The entity picker is "Kind";
        # the Build/Fix picker is "Record Type".
        self.main_layout.addWidget(section_widget("Record"))
        record_grid = QGridLayout()
        record_grid.setContentsMargins(0, 0, 0, 0)
        record_grid.setHorizontalSpacing(space("lg"))
        record_grid.setVerticalSpacing(space("sm"))
        record_grid.addWidget(_captioned(QLabel("Kind"), self.type_combo), 0, 0)
        self._recordtype_cell = _captioned(self.recordtype_label,
                                           self.recordtype_combo)
        record_grid.addWidget(self._recordtype_cell, 0, 1)
        record_grid.addWidget(
            _captioned(self.title_label, self.title_edit, stretch=True),
            1, 0, 1, 2)
        record_grid.addWidget(
            _captioned(self.desc_label, self.desc_edit, stretch=True),
            2, 0, 1, 2)
        record_grid.setColumnStretch(0, 1)
        record_grid.setColumnStretch(1, 1)
        self.main_layout.addLayout(record_grid)

        self._placement_section = section_widget("Placement")
        self.main_layout.addWidget(self._placement_section)
        self._placement_host = QWidget()
        placement_grid = QGridLayout(self._placement_host)
        placement_grid.setContentsMargins(0, 0, 0, 0)
        placement_grid.setHorizontalSpacing(space("lg"))
        placement_grid.setVerticalSpacing(space("sm"))
        for position, (caption, widget) in enumerate((
            ("Status", self.status_combo),
            ("Stage", self.stage_combo),
            ("Owner", self.owner_edit),
            ("Originator", self.originator_edit),
            ("Epic Link", self.epic_combo),
            ("Effort", self.estimate_combo),
            ("Pressure (0-100)", self.pressure_spin),
        )):
            row, column = divmod(position, 2)
            placement_grid.addWidget(_captioned(QLabel(caption), widget),
                                     row, column)
        placement_grid.setColumnStretch(0, 1)
        placement_grid.setColumnStretch(1, 1)
        self.main_layout.addWidget(self._placement_host)

        self._epic_section = section_widget("Epic")
        self.main_layout.addWidget(self._epic_section)
        self._epic_host = QWidget()
        epic_grid = QGridLayout(self._epic_host)
        epic_grid.setContentsMargins(0, 0, 0, 0)
        epic_grid.setHorizontalSpacing(space("lg"))
        epic_grid.setVerticalSpacing(space("sm"))
        epic_grid.addWidget(
            _captioned(QLabel("Epic Type"), self.epic_type_combo), 0, 0)
        epic_grid.addWidget(
            _captioned(QLabel("Epic Status"), self.epic_status_combo), 0, 1)
        epic_grid.setColumnStretch(0, 1)
        epic_grid.setColumnStretch(1, 1)
        self.main_layout.addWidget(self._epic_host)

        # Links — above the Log, since a link is context for reading the ticket
        # rather than a note about working it. Unlike the Log, links may be
        # entered while the ticket is still being *created*: they buffer in the
        # widget and save_data flushes them once the INSERT yields an id.
        self._links_section = section_widget("Links")
        self.main_layout.addWidget(self._links_section)
        self.links = LinkBar(self.conn, allow_pending=True, author="user")
        self.links.header.setVisible(False)  # the section header above stands in
        self.main_layout.addWidget(self.links)

        # Log section — comments and mechanical field changes in one list,
        # newest first. Only meaningful when editing an existing task.
        self._log_section = section_widget("Log")
        self.log_filter_row = QHBoxLayout()
        self.log_filter_row.setSpacing(space("lg"))
        self.log_show_comments = QCheckBox("Comments")
        self.log_show_comments.setChecked(True)
        self.log_show_comments.toggled.connect(self._render_log)
        self.log_show_changes = QCheckBox("Changes")
        self.log_show_changes.setChecked(True)
        self.log_show_changes.toggled.connect(self._render_log)
        self.log_filter_row.addWidget(self.log_show_comments)
        self.log_filter_row.addWidget(self.log_show_changes)
        self.log_filter_row.addStretch(1)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(
            QFontMetrics(self.log_view.font()).lineSpacing() * 7)
        self.log_post_row = QHBoxLayout()
        self.log_post_input = QLineEdit()
        self.log_post_input.setPlaceholderText("Post a brief progress note…")
        self.log_post_input.returnPressed.connect(self._post_log_entry)
        self.log_post_btn = QPushButton("Post")
        self.log_post_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.log_post_btn.clicked.connect(self._post_log_entry)
        self.log_post_row.addWidget(self.log_post_input)
        self.log_post_row.addWidget(self.log_post_btn)
        self.main_layout.addWidget(self._log_section)
        self.main_layout.addLayout(self.log_filter_row)
        self.main_layout.addWidget(self.log_view)
        self.main_layout.addLayout(self.log_post_row)
        self._attach_section = section_widget("Attachments")
        self.main_layout.addWidget(self._attach_section)
        self.attachments = AttachmentBar(self.conn)
        self.main_layout.addWidget(self.attachments)
        # Leftover vertical space collects below the last section, so hiding a
        # section (the Epic kind) never opens gaps between the ones that remain.
        self.main_layout.addStretch(1)
        self._log_widgets = [self._log_section, self.log_show_comments,
                             self.log_show_changes, self.log_view,
                             self.log_post_input, self.log_post_btn,
                             self._attach_section, self.attachments]

        self.button_box = QHBoxLayout()
        if record_id is not None:
            self.delete_btn = QPushButton("Delete")
            self.delete_btn.setObjectName("deleteBtn")
            self.delete_btn.clicked.connect(self._handle_delete)
            self.button_box.addWidget(self.delete_btn)

        self.button_box.addStretch()
        # Delete sits far left as the destructive action (added above when
        # editing); Cancel and OK sit right as secondary and primary, in the
        # same button ranks the rest of the app uses.
        standard_buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        standard_buttons.accepted.connect(self.accept)
        standard_buttons.rejected.connect(self.reject)
        self.button_box.addWidget(standard_buttons)
        # Held disabled while a required field is empty. Save silently dropped
        # such a record — including a long Description the user had just typed —
        # so the button must not be pressable in the state that would lose it.
        self.ok_button = standard_buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setObjectName("globalCreateBtn")
        # Pinned OUTSIDE the scroll area — the save button stays reachable no
        # matter how tall the body grows.
        self.button_box.setContentsMargins(space("lg"), space("md"),
                                           space("lg"), space("lg"))
        outer.addLayout(self.button_box)

        # Never taller than the screen it opens on. Past that the scroll area
        # takes over instead of the window growing off the bottom.
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.setMaximumHeight(int(screen.availableGeometry().height() * 0.9))

        self.type_combo.currentIndexChanged.connect(self._update_visible_fields)
        self.recordtype_combo.currentIndexChanged.connect(self._apply_template_if_boilerplate)
        self.title_edit.textChanged.connect(self._refresh_required_state)

        if record_id is not None:
            self._load_existing_data()
        self._update_visible_fields()
        self._apply_template_if_boilerplate()
        self._refresh_required_state()
        self.attachments.set_task(self.record_id)
        self.links.set_task(self.record_id)

        # Molly guard: remember the field state as loaded so a
        # Cancel / window-close with edits in flight can warn before discarding.
        # Captured last, after load + template fill, so an untouched dialog reads
        # as clean.
        self._baseline_signature = self._field_signature()

    def showEvent(self, event):  # noqa: N802 (Qt override)
        """Open tall enough to show the whole ticket, capped at the screen. Qt's
        default would size the dialog to a squat sizeHint and make you scroll
        through content that would have fitted."""
        super().showEvent(event)
        body = self._scroll.widget()
        if body is not None:
            chrome = self.height() - self._scroll.viewport().height()
            wanted = body.sizeHint().height() + chrome
            self.resize(self.width(), min(wanted, self.maximumHeight()))
        event.accept()

    # ----- unsaved-changes guard ------------------------------

    def _field_signature(self) -> tuple:
        """A comparable snapshot of every editable field. Two signatures differ
        iff the user changed something, so it drives the unsaved-changes prompt."""
        return (
            self.title_edit.text(),
            self.desc_edit.toPlainText(),
            self.type_combo.currentIndex(),
            self.recordtype_combo.currentIndex(),
            self.stage_combo.currentText(),
            self.status_combo.currentText(),
            self.owner_edit.currentText(),
            self.originator_edit.text(),
            self.epic_combo.currentIndex(),
            self.pressure_spin.value(),
            self.estimate_combo.currentData(),
            self.epic_type_combo.currentText(),
            self.epic_status_combo.currentText(),
            # Links buffered on a not-yet-saved ticket are unsaved work too, so
            # cancelling with one queued should warn like any other edit.
            self.links.pending_signature() if hasattr(self, "links") else (),
        )

    def _is_dirty(self) -> bool:
        return self._field_signature() != getattr(self, "_baseline_signature", None)

    def _confirm_discard(self) -> bool:
        """Return True if it's OK to close (no edits, or the user chose to discard
        them). Shows a warning with Close / Cancel, Cancel highlighted as the safe
        default so a stray keypress doesn't throw work away."""
        if not self._is_dirty():
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Unsaved changes")
        box.setText("You have unsaved changes.")
        close_btn = box.addButton("Close", QMessageBox.DestructiveRole)
        cancel_btn = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(cancel_btn)
        box.setEscapeButton(cancel_btn)
        box.exec()
        return box.clickedButton() is close_btn

    def accept(self):
        """Belt and braces: OK is already disabled while a required field is
        empty, but Enter and programmatic accepts reach here too. Refuse rather
        than close, since closing is what used to discard the user's typing."""
        missing = self._missing_required()
        if missing:
            self._refresh_required_state()
            missing[0].setFocus()
            return
        super().accept()

    def reject(self):
        """Cancel button / Esc: guard unsaved edits before discarding."""
        if self._confirm_discard():
            super().reject()

    def closeEvent(self, event):
        """Window-close (the title-bar X): same guard as Cancel."""
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _select_owner(self, value: str | None) -> None:
        """Point the Owner picker at ``value``. If a legacy record carries an
        owner not in FLEET_AGENTS, add it as an option so editing never silently
        rewrites its owner."""
        value = (value or "user").strip() or "user"
        idx = self.owner_edit.findText(value)
        if idx < 0:
            self.owner_edit.addItem(value)
            idx = self.owner_edit.findText(value)
        self.owner_edit.setCurrentIndex(idx)

    def _current_record_type(self) -> str:
        return self.recordtype_combo.currentData() or "build"

    def _apply_template_if_boilerplate(self, *args) -> None:
        """Fill the Description with the current record type's template, but only
        when the field is still boilerplate. User input supersedes the template
        except when blank. No-op unless the entity is a Task/Issue."""
        if self.type_combo.currentText() != "Task / Issue":
            return
        if _is_boilerplate(self.desc_edit.toPlainText()):
            self.desc_edit.setPlainText(RECORD_TEMPLATES[self._current_record_type()])
        self._sync_desc_font()

    def _sync_desc_font(self, *args) -> None:
        """Monospace is reserved for the mad-lib skeletons and their bracketed
        blanks; prose renders in the body face. The switch follows the text: a
        Description that still IS a template lines its blanks up in monospace,
        and the first edit past it moves the field to the reading face."""
        mono = _is_boilerplate(self.desc_edit.toPlainText())
        if mono == self._desc_is_mono:
            return
        self._desc_is_mono = mono
        if mono:
            self.desc_edit.setFont(_mono_font())
        else:
            body = QFont()
            body.setPointSize(type_size("section"))
            self.desc_edit.setFont(body)

    # ----- required fields ------------------------------------

    def _missing_required(self) -> list:
        """The required widgets that are currently empty. Title is the only
        required field for either kind: everything else the dialog collects has
        a default (Stage, Status, Owner, Pressure) or is legitimately optional
        (Description, Epic Link, links, attachments). Return widgets, not names,
        so the caller can mark exactly what it found."""
        missing = []
        if not self.title_edit.text().strip():
            missing.append(self.title_edit)
        return missing

    @staticmethod
    def _set_missing(widget, missing: bool) -> None:
        """Flip the dynamic ``fieldMissing`` property and force a restyle. Qt does
        not re-evaluate property selectors on its own, so without the
        unpolish/polish the red border would never appear or never clear."""
        if widget.property("fieldMissing") == missing:
            return
        widget.setProperty("fieldMissing", missing)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _refresh_required_state(self, *args) -> None:
        """Mark every empty required field red and hold OK unclickable until none
        are left. Called on construction and on every keystroke in a required
        field, so the button and the borders can never disagree with the form."""
        missing = self._missing_required()
        self._set_missing(self.title_edit, self.title_edit in missing)
        self._set_missing(self.title_label, self.title_edit in missing)
        if getattr(self, "ok_button", None) is not None:
            self.ok_button.setEnabled(not missing)
            self.ok_button.setToolTip(
                f"{self.title_label.text().rstrip(' *')} is required"
                if missing else ""
            )

    def _update_visible_fields(self):
        is_task = (self.type_combo.currentText() == "Task / Issue")
        is_epic = not is_task

        self.title_label.setText("Epic Name *" if is_epic else "Task Title *")

        # A cell hides its caption and control together; a section hides its
        # header, hairline and grid together.
        self._recordtype_cell.setVisible(is_task)
        self._placement_section.setVisible(is_task)
        self._placement_host.setVisible(is_task)
        self._epic_section.setVisible(is_epic)
        self._epic_host.setVisible(is_epic)

        show_log = is_task and self.record_id is not None
        for w in getattr(self, "_log_widgets", []):
            w.setVisible(show_log)
        # Links show for any task, saved or not — that is the whole point of the
        # pending buffer. Epics have no links.
        if hasattr(self, "links"):
            self._links_section.setVisible(is_task)
            self.links.setVisible(is_task)

        # The required field's LABEL changes with the kind ("Task Title *" vs
        # "Epic Name *"), so its red state and the OK tooltip are recomputed
        # whenever the kind does.
        self._refresh_required_state()

    def _load_existing_data(self):
        try:
            if self.mode == "task":
                row = self.conn.execute(
                    "SELECT title, description, status, pressure, epic_id, "
                    "COALESCE(assignee, 'user'), COALESCE(reporter, 'user'), COALESCE(estimate, ''), "
                    "COALESCE(record_type, 'build'), COALESCE(stage, 'backlog') "
                    "FROM task WHERE id=?", (self.record_id,)
                ).fetchone()
                if row:
                    self.title_edit.setText(row[0] or "")
                    self.desc_edit.setPlainText(row[1] or "")
                    current_status = row[2] if row[2] in ["todo", "doing", "done"] else "todo"
                    self.status_combo.setCurrentText(current_status)
                    self.pressure_spin.setValue(row[3] or 0)
                    if row[4] is not None:
                        idx = self.epic_combo.findData(row[4])
                        if idx < 0:
                            # Task is linked to an epic the picker filtered out
                            # (a done epic). Re-add it so the existing link
                            # is preserved and visible rather than silently lost.
                            er = self.conn.execute(
                                "SELECT name FROM epic WHERE id=?", (row[4],)
                            ).fetchone()
                            if er:
                                self.epic_combo.addItem(f"{er[0]} [Done]", row[4])
                                idx = self.epic_combo.findData(row[4])
                        if idx >= 0:
                            self.epic_combo.setCurrentIndex(idx)
                    self._select_owner(row[5])
                    self.originator_edit.setText(row[6])
                    est_idx = self.estimate_combo.findData((row[7] or "").upper())
                    self.estimate_combo.setCurrentIndex(max(est_idx, 0))
                    rt_idx = self.recordtype_combo.findData((row[8] or "build").lower())
                    if rt_idx >= 0:
                        self.recordtype_combo.setCurrentIndex(rt_idx)
                    stage = row[9] if row[9] in STAGES else "backlog"
                    self.stage_combo.setCurrentText(stage)
                    self._loaded_stage = stage
                    self._loaded_status = current_status

                self._render_log()

            elif self.mode == "epic":
                row = self.conn.execute("SELECT name, description, type, status FROM epic WHERE id=?", (self.record_id,)).fetchone()
                if row:
                    self.title_edit.setText(row[0] or "")
                    self.desc_edit.setPlainText(row[1] or "")
                    self.epic_type_combo.setCurrentText(row[2] or "Epic (bounded)")
                    self.epic_status_combo.setCurrentText(row[3] or "not started")
        except sqlite3.OperationalError:
            pass

    def _render_log(self, _checked=None):
        if self.record_id is None:
            return
        lines = log_lines(
            self.conn, self.record_id,
            comments=self.log_show_comments.isChecked(),
            changes=self.log_show_changes.isChecked(),
        )
        self.log_view.setPlainText("\n".join(lines) if lines else "(Nothing to show.)")

    def _post_log_entry(self):
        if self.record_id is None:
            return
        body = self.log_post_input.text().strip()
        if not body:
            return
        try:
            self.conn.execute(
                "INSERT INTO issue_log (task_id, author, body, created_at) VALUES (?,?,?,?)",
                (self.record_id, "user", body, _utcnow()),
            )
            self.conn.commit()
        except sqlite3.OperationalError:
            return
        self.log_post_input.clear()
        self._render_log()

    def _handle_delete(self):
        reply = QMessageBox.question(self, "Confirm Delete", f"Permanently delete this {self.mode}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.mode == "task":
                self.conn.execute("DELETE FROM issue_log WHERE task_id=?", (self.record_id,))
                self.conn.execute("DELETE FROM task_event WHERE task_id=?", (self.record_id,))
                self.conn.execute("DELETE FROM attachment WHERE task_id=?", (self.record_id,))
                # Both ends of every link, so nothing is left pointing at a
                # ticket that no longer exists.
                remove_links_for_task(self.conn, self.record_id)
                self.conn.execute("DELETE FROM task WHERE id=?", (self.record_id,))
            elif self.mode == "epic":
                self.conn.execute("UPDATE task SET epic_id=NULL WHERE epic_id=?", (self.record_id,))
                self.conn.execute("DELETE FROM epic WHERE id=?", (self.record_id,))
            self.conn.commit()
            # (behaviour preserved from the pre-split monolith): callers do
            # `if dlg.exec() == Accepted: dlg.save_data()`, so save_data() runs
            # once more after delete. Harmless — its statements target the now-
            # deleted record_id and affect zero rows — and it lets the caller's
            # refresh path run.
            self.done(QDialog.Accepted)

    def _append_order(self, stage: str, status: str) -> int:
        """sort_order that appends a task to the BOTTOM of its destination list:
        the Backlog is one combined list (keyed on stage), the active Board is a
        list per status column (keyed on stage+status)."""
        if stage == "active":
            row = self.conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) FROM task "
                "WHERE stage='active' AND status=?", (status,)).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage=?",
                (stage,)).fetchone()
        return int(row[0]) + 1

    def save_data(self, fallback_epic=None):
        title = self.title_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()
        if not title:
            # Unreachable through the UI: OK is disabled and accept() refuses
            # while the title is empty. Kept because a titleless write is worse
            # than no write, and _handle_delete deliberately re-enters here.
            return

        chosen_type = self.type_combo.currentText()

        if chosen_type == "Task / Issue":
            status = self.status_combo.currentText()
            stage = self.stage_combo.currentText()
            pressure = self.pressure_spin.value()
            epic_id = self.epic_combo.currentData() or fallback_epic or self.fallback_epic_id
            owner = self.owner_edit.currentText().strip() or "user"
            originator = self.originator_edit.text().strip() or "user"
            estimate = self.estimate_combo.currentData() or None
            record_type = self._current_record_type()
            closed_at = _utcnow() if status == "done" else None

            if self.record_id is None:
                sort_order = self._append_order(stage, status)
                ts = _utcnow()
                cur = self.conn.execute(
                    "INSERT INTO task (epic_id, title, description, status, stage, sort_order, "
                    "pressure, assignee, reporter, estimate, record_type, closed_at, "
                    "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (epic_id, title, desc, status, stage, sort_order, pressure, owner,
                     originator, estimate, record_type, closed_at, ts, ts),
                )
                # The ticket now has an id, so links entered during creation can
                # finally be written against it.
                self.links.flush_pending(cur.lastrowid)
            else:
                # Re-seat at the bottom of the destination list only if the task
                # actually changed tab or column; otherwise keep its position.
                moved = (stage != self._loaded_stage) or (status != self._loaded_status)
                # Every field this write changes reaches the change log through
                # the database triggers, so an edit made here is recorded the
                # same way as a drag on the board, and updated_at follows from
                # the newest entry.
                if moved:
                    sort_order = self._append_order(stage, status)
                    self.conn.execute(
                        "UPDATE task SET epic_id=?, title=?, description=?, status=?, stage=?, "
                        "sort_order=?, pressure=?, assignee=?, reporter=?, estimate=?, "
                        "record_type=?, closed_at=? WHERE id=?",
                        (epic_id, title, desc, status, stage, sort_order, pressure, owner,
                         originator, estimate, record_type, closed_at, self.record_id),
                    )
                else:
                    self.conn.execute(
                        "UPDATE task SET epic_id=?, title=?, description=?, status=?, stage=?, "
                        "pressure=?, assignee=?, reporter=?, estimate=?, record_type=?, "
                        "closed_at=? WHERE id=?",
                        (epic_id, title, desc, status, stage, pressure, owner, originator,
                         estimate, record_type, closed_at, self.record_id),
                    )

        elif chosen_type == "Epic":
            etype = self.epic_type_combo.currentText()
            estatus = self.epic_status_combo.currentText()
            if self.record_id is None:
                self.conn.execute("INSERT INTO epic (name, description, type, status) VALUES (?,?,?,?)", (title, desc, etype, estatus))
            else:
                self.conn.execute("UPDATE epic SET name=?, description=?, type=?, status=? WHERE id=?", (title, desc, etype, estatus, self.record_id))

        self.conn.commit()
