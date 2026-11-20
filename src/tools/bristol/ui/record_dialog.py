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
from types import ModuleType
from typing import cast

import finishing  # bristol-local: what done means for the board, one rule
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QCloseEvent, QFont, QFontMetrics, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .attachments import AttachmentBar
from .board_write import write
from .dialogs import ORDINARY, PRIMARY, choose, confirm, notify
from .growing_edit import GrowingTextEdit
from .links import LinkBar, remove_links_for_task
from .segmented import SegmentedControl
from .settled_combo import fill_words
from .theme import (
    BLOCK_REASON_CHOICES,
    BLOCK_REASON_HINT,
    EPIC_KIND_CHOICES,
    EPIC_STATUS_CHOICES,
    FLEET_AGENTS,
    LAYOUT,
    SIZE_CHOICES,
    SIZE_HINT,
    STAGE_CHOICES,
    STATUS_CHOICES,
    TIER_CHOICES,
    TIER_HINT,
    _mono_font,
    _utcnow,
    edge_width,
    fill_agents,
    fleet_agents,
    log_lines,
    select_agent,
    space,
    type_size,
)

# ---------------------------------------------------------------------------
# Record-type description templates
# ---------------------------------------------------------------------------
# A ticket is one of two record types. A *Build* is a thing to build; its
# description is a Story, Given/When/Then requirements and test criteria. A *Fix* is a
# broken thing; its description states the Expected behaviour and the Observed
# divergence. These skeletons pre-populate the Description field so both the
# user and the agents fill in the same shape every time. They are mad-libs:
# constant words with short "[bracketed]" fill-in blanks — replace the whole
# bracket (including the brackets) with your own words. Keep these strings in
# sync with the format rules in src/skills/manage-tickets/SKILL.md (§Record types).
BUILD_TEMPLATE = (
    "Story:\n"
    "As [the person served, by their role] I want [what should change] so that [why it matters].\n"
    "\n"
    "Requirements:\n"
    "1. Given [starting state], when [action], then [expected result].\n"
    "\n"
    "Test Criteria:\n"
    "- [what is run or looked at], and [the result that would fail the card].\n"
)

FIX_TEMPLATE = (
    "Expected:\n"
    "Given [precondition], when [action], then [expected result].\n"
    "\n"
    "Observed:\n"
    "[what happened instead]\n"
)

RECORD_TEMPLATES = {"build": BUILD_TEMPLATE, "fix": FIX_TEMPLATE}

# What a record's Log shows: everything, only the comments, or only the changes.
LOG_FILTERS = [("all", "All"), ("comments", "Comments"), ("changes", "Changes")]

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
    rule.setFrameShape(QFrame.Shape.HLine)
    rule.setFixedHeight(edge_width("line"))
    column.addWidget(label)
    column.addWidget(rule)
    return box


# The one value that means standing; every other value, including the prose an
# older board contains, means project. finishing.STANDING_KIND is the same word,
# named there because that is where the rules resting on it live.
STANDING_KIND = finishing.STANDING_KIND
PROJECT_KIND = "project"


def _epic_kind(stored: str | None) -> str:
    """Which of the two kinds a stored `epic.type` reads as."""
    return STANDING_KIND if (stored or "").strip().lower() == STANDING_KIND else PROJECT_KIND


# The date a due-date field sits on when the card has none. A date field has to
# contain some date, so the earliest one it offers is the word "no date" instead.
NO_DUE_DATE = QDate(1970, 1, 1)

# The description box's height, in lines of the monospace face: room for the
# mad-lib skeleton it opens with, and the most it grows before it scrolls.
DESC_MIN_LINES = 8
DESC_MAX_LINES = 11


def _captioned(caption: QLabel, widget: QWidget, stretch: bool = False) -> QWidget:
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
        column.addWidget(widget, 0, Qt.AlignmentFlag.AlignLeft)
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
    def __init__(
        self,
        parent: QWidget | None,
        conn: sqlite3.Connection,
        mode: str = "task",
        record_id: int | None = None,
        initial_status: str | None = None,
        epic_id: int | None = None,
        initial_stage: str | None = None,
    ) -> None:
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
        # The raw text this epic's kind arrived as. An older board contains prose
        # there, which reads as project and is kept until the user chooses
        # something else.
        self._loaded_epic_type = None

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
        self._scroll.setObjectName("recordScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        # No visible bars: the wheel/trackpad still scrolls, and a permanent
        # gutter on a form this narrow is more intrusive than the thing it fixes.
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        self._scroll.setWidget(body)
        outer.addWidget(self._scroll, 1)

        self.main_layout = QVBoxLayout(body)
        # The dialog's pad is SPACE xl all round: the body takes the top and
        # sides, the pinned button row the sides and foot, and SPACE md, the
        # block-to-block gap, lies between them.
        self.main_layout.setContentsMargins(space("xl"), space("xl"), space("xl"), 0)
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
        self.title_edit = GrowingTextEdit(max_lines=3)

        # The description's height comes from the mad-lib skeleton it opens
        # with; its face is monospace only while the text still IS that
        # skeleton, and switches to the body face once prose replaces it.
        self.desc_edit = QTextEdit()
        mono_line = QFontMetrics(_mono_font()).lineSpacing()
        self.desc_edit.setMinimumHeight(mono_line * DESC_MIN_LINES)
        self.desc_edit.setMaximumHeight(mono_line * DESC_MAX_LINES)
        self._desc_is_mono = True
        self.desc_edit.setFont(_mono_font())
        self.desc_edit.textChanged.connect(self._sync_desc_font)
        self.desc_label = QLabel("Description")

        # Stage (backlog | active | archive) — which tab the task lives in;
        # orthogonal to Status.
        self.stage_combo = fill_words(QComboBox(), STAGE_CHOICES)

        self.status_combo = fill_words(QComboBox(), STATUS_CHOICES)
        if initial_status:
            self.status_combo.setCurrentIndex(max(self.status_combo.findData(initial_status), 0))

        # Owner is a picker of the fleet agents + 'user' so ownership
        # is always a real, spellable slug.
        self.owner_edit = QComboBox()
        fill_agents(self.owner_edit, fleet_agents())
        self.originator_edit = QLineEdit()

        if record_id is None:
            # A new task opens on the stage of the tab Create was pressed on
            # (main_window._stage_for_current_tab), appended to the bottom of
            # that list on save. With no tab to key off, it lands on the board,
            # the same default ``ticket_write.py add-task`` carries.
            self.stage_combo.setCurrentIndex(
                max(self.stage_combo.findData(initial_stage or "active"), 0)
            )
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
            "SELECT id, name, status FROM epic ORDER BY id"
        ).fetchall():
            if (estatus or "").lower() in ("completed", "done"):
                continue
            self.epic_combo.addItem(ename, eid)

        # Tier: how much thinking the card needs, whatever its size. Size: how
        # much of a full usage budget it would take. The anchors are each
        # picker's tooltip rather than its option text, so the picker stays a
        # column of names; both scales are the manage-tickets skill.
        self.tier_combo = fill_words(QComboBox(), TIER_CHOICES, hint=TIER_HINT)
        self.estimate_combo = fill_words(QComboBox(), SIZE_CHOICES, hint=SIZE_HINT)

        # Due: an outside deadline the card has to meet — a filing window, a
        # renewal, a date somebody else set. Most cards have none, so the field
        # opens on "no date" and says so in words; it is a date field rather
        # than a checkbox and a date because the empty state is the common one
        # and has to be reachable in one move.
        self.due_edit = QDateEdit()
        self.due_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setMinimumDate(NO_DUE_DATE)
        self.due_edit.setSpecialValueText("no date")
        self.due_edit.setDate(NO_DUE_DATE)
        self.due_edit.setToolTip(
            "An outside deadline this card has to meet. Optional, and it "
            "orders nothing — board order is the queue. Wind the date back "
            "past its start to clear it."
        )

        # Blocked: what kind of thing has stopped the card. It never names which
        # card — a dependency is a 'blocks' link under Links, resolved live — and
        # the prose that goes with it belongs in a comment under the Log.
        self.block_combo = fill_words(QComboBox(), BLOCK_REASON_CHOICES, hint=BLOCK_REASON_HINT)

        # Kind is chosen, never typed: one value means standing and the board
        # has one standing workstream, so a field anyone can type in is a field
        # that can break it.
        self.epic_type_combo = fill_words(QComboBox(), EPIC_KIND_CHOICES)
        self.epic_status_combo = fill_words(QComboBox(), EPIC_STATUS_CHOICES)

        # Every short field sits at the width its contents ask for: a combo
        # sizes to its longest entry, the originator to the longest agent slug. Only the title and description
        # keep an Expanding policy and take the dialog's width.
        metrics = QFontMetrics(self.font())
        for combo in (
            self.type_combo,
            self.recordtype_combo,
            self.stage_combo,
            self.status_combo,
            self.owner_edit,
            self.epic_combo,
            self.tier_combo,
            self.estimate_combo,
            self.block_combo,
            self.epic_type_combo,
            self.epic_status_combo,
        ):
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            combo.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        # A date field sizes itself; only the width policy is shared with the
        # pickers beside it.
        self.due_edit.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.originator_edit.setMaximumWidth(
            max(metrics.horizontalAdvance(slug) for slug in FLEET_AGENTS) + space("2xl") * 2
        )

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
        self._recordtype_cell = _captioned(self.recordtype_label, self.recordtype_combo)
        record_grid.addWidget(self._recordtype_cell, 0, 1)
        record_grid.addWidget(
            _captioned(self.title_label, self.title_edit, stretch=True), 1, 0, 1, 2
        )
        record_grid.addWidget(_captioned(self.desc_label, self.desc_edit, stretch=True), 2, 0, 1, 2)
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
        for position, (caption, widget) in enumerate(
            (
                ("Status", self.status_combo),
                ("Stage", self.stage_combo),
                ("Owner", self.owner_edit),
                ("Originator", self.originator_edit),
                ("Epic Link", self.epic_combo),
                ("Tier", self.tier_combo),
                ("Size", self.estimate_combo),
                ("Blocked", self.block_combo),
                ("Due", self.due_edit),
            )
        ):
            row, column = divmod(position, 2)
            placement_grid.addWidget(_captioned(QLabel(caption), widget), row, column)
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
        epic_grid.addWidget(_captioned(QLabel("Epic Type"), self.epic_type_combo), 0, 0)
        epic_grid.addWidget(_captioned(QLabel("Epic Status"), self.epic_status_combo), 0, 1)
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
        self.links.on_open_issue = self._open_linked_card
        self.main_layout.addWidget(self.links)

        # Log section — comments and mechanical field changes in one list,
        # newest first. Only meaningful when editing an existing task.
        self._log_section = section_widget("Log")
        self.log_filter_row = QHBoxLayout()
        self.log_filter = SegmentedControl(LOG_FILTERS)
        self.log_filter.changed.connect(lambda _value: self._render_log())
        self.log_filter_row.addWidget(self.log_filter)
        self.log_filter_row.addStretch(1)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(QFontMetrics(self.log_view.font()).lineSpacing() * 7)
        self.log_post_row = QHBoxLayout()
        self.log_post_input = GrowingTextEdit(max_lines=6)
        self.log_post_input.setPlaceholderText("Post a brief progress note…")
        self.log_post_input.submitted.connect(self._post_log_entry)
        self.log_post_btn = QPushButton("Post")
        self.log_post_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.log_post_btn.clicked.connect(self._post_log_entry)
        self.log_post_row.addWidget(self.log_post_input)
        self.log_post_row.addWidget(self.log_post_btn, 0, Qt.AlignmentFlag.AlignBottom)
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
        self._log_widgets = [
            self._log_section,
            self.log_filter,
            self.log_view,
            self.log_post_input,
            self.log_post_btn,
            self._attach_section,
            self.attachments,
        ]

        self.button_box = QHBoxLayout()
        if record_id is not None:
            self.delete_btn = QPushButton("Delete")
            self.delete_btn.setObjectName("deleteBtn")
            self.delete_btn.clicked.connect(self._handle_delete)
            self.button_box.addWidget(self.delete_btn)

        self.button_box.addStretch()
        # Delete sits far left as the destructive action (added above when
        # editing); Cancel and the action sit right as secondary and primary,
        # in the same button ranks the rest of the app uses.
        standard_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        standard_buttons.accepted.connect(self.accept)
        standard_buttons.rejected.connect(self.reject)
        self.button_box.addWidget(standard_buttons)
        # The default button names its action. A save tried with a required
        # field empty is refused in accept(), which keeps the window open with
        # the typing in it and only then marks the field.
        self.ok_button = standard_buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Save" if record_id is not None else "Create")
        self.ok_button.setObjectName("globalCreateBtn")
        # Pinned OUTSIDE the scroll area — the save button stays reachable no
        # matter how tall the body grows.
        self.button_box.setContentsMargins(space("xl"), space("md"), space("xl"), space("xl"))
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

    def showEvent(self, event: QShowEvent) -> None:
        """Open tall enough to show the whole ticket, capped at the screen."""
        super().showEvent(event)
        body = self._scroll.widget()
        if body is not None:
            chrome = self.height() - self._scroll.viewport().height()
            wanted = body.sizeHint().height() + chrome
            self.resize(self.width(), min(wanted, self.maximumHeight()))
        self._keep_on_screen()
        event.accept()

    def _keep_on_screen(self) -> None:
        """Move the window up until its frame, title bar and buttons included,
        sits inside the screen's usable area. It is placed at the size it opens
        with and only then grown to the ticket, so the growth is what carries
        its bottom under the Dock."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        frame = self.frameGeometry()
        shift = min(0, area.bottom() - frame.bottom())
        if frame.top() + shift < area.top():
            shift = area.top() - frame.top()
        if shift:
            self.move(self.x(), self.y() + shift)

    # ----- unsaved-changes guard ------------------------------

    def _field_signature(self) -> tuple:
        """A comparable snapshot of every editable field. Two signatures differ
        iff the user changed something, so it drives the unsaved-changes prompt."""
        return (
            self.title_edit.text(),
            self.desc_edit.toPlainText(),
            self.type_combo.currentIndex(),
            self.recordtype_combo.currentIndex(),
            self.stage_combo.currentData(),
            self.status_combo.currentData(),
            self.owner_edit.currentData(),
            self.originator_edit.text(),
            self.epic_combo.currentIndex(),
            self.tier_combo.currentData(),
            self.estimate_combo.currentData(),
            self.block_combo.currentData(),
            self.due_edit.date(),
            self.epic_type_combo.currentData(),
            self.epic_status_combo.currentData(),
            # Links buffered on a not-yet-saved ticket are unsaved work too, so
            # cancelling with one queued should warn like any other edit.
            self.links.pending_signature() if hasattr(self, "links") else (),
        )

    def _is_dirty(self) -> bool:
        return self._field_signature() != getattr(self, "_baseline_signature", None)

    def _epic_closure(self) -> ModuleType | None:
        """The epic-closure module, or None where this bundle does not carry it.
        A board that cannot reach it still edits epics; what it loses is the
        closure, the same way a stripped bundle loses the report."""
        try:
            import epic_closure
        except ImportError:
            return None
        return epic_closure

    def _confirm_discard(self) -> bool:
        """Return True if it's OK to close (no edits, or the user chose to discard
        them). Shows a warning with Close / Cancel, Cancel highlighted as the safe
        default so a stray keypress doesn't throw work away."""
        if not self._is_dirty():
            return True
        return confirm(
            self,
            "Unsaved changes",
            "You have unsaved changes. Closing throws them away.",
            "Close without saving",
            "Keep editing",
            destructive=True,
        )

    def accept(self) -> None:
        """Refuse a save with a required field empty rather than close, since
        closing is what would discard the user's typing, and from here on mark
        every empty required field."""
        self._save_tried = True
        missing = self._missing_required()
        if missing:
            self._refresh_required_state()
            missing[0].setFocus()
            return
        super().accept()

    def reject(self) -> None:
        """Cancel button / Esc: guard unsaved edits before discarding."""
        if self._confirm_discard():
            super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Window-close (the title-bar X): same guard as Cancel."""
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    # ----- following a link -----------------------------------

    def _open_linked_card(self, other_id: int) -> None:
        """Show the card a link points at in this window, in place of the one it
        shows, asking first whether to save edits in flight."""
        if self.mode != "task" or self.record_id is None:
            return
        if self._is_dirty():
            answer = choose(
                self,
                "Unsaved changes",
                f"Save your changes to this card before opening #{other_id}?",
                [
                    ("Don't Save", ORDINARY, "discard"),
                    ("Cancel", ORDINARY, None),
                    ("Save", PRIMARY, "save"),
                ],
                default_index=2,
            )
            if answer is None:
                return
            if answer == "save":
                self._save_tried = True
                missing = self._missing_required()
                if missing:
                    self._refresh_required_state()
                    missing[0].setFocus()
                    return
                self.save_data()
        self._show_record(other_id)

    def _show_record(self, record_id: int) -> None:
        """Point the window at another saved card and read it in afresh."""
        self.record_id = record_id
        self._save_tried = False
        self.log_post_input.setText("")
        self._load_existing_data()
        self._update_visible_fields()
        self._refresh_required_state()
        self.attachments.set_task(record_id)
        self.links.set_task(record_id)
        self._scroll.verticalScrollBar().setValue(0)
        self._baseline_signature = self._field_signature()

    def _select_owner(self, value: str | None) -> None:
        """Point the Owner picker at ``value``. If a legacy record carries an
        owner not in FLEET_AGENTS, add it as an option so editing never silently
        rewrites its owner."""
        select_agent(self.owner_edit, value)

    def _current_record_type(self) -> str:
        return self.recordtype_combo.currentData() or "build"

    def _apply_template_if_boilerplate(self, *args: object) -> None:
        """Fill the Description with the current record type's template, but only
        when the field is still boilerplate. User input supersedes the template
        except when blank. No-op unless the entity is a Task/Issue."""
        if self.type_combo.currentText() != "Task / Issue":
            return
        if _is_boilerplate(self.desc_edit.toPlainText()):
            self.desc_edit.setPlainText(RECORD_TEMPLATES[self._current_record_type()])
        self._sync_desc_font()

    def _sync_desc_font(self, *args: object) -> None:
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
        a default (Stage, Status, Owner) or is legitimately optional
        (Description, Epic Link, links, attachments). Return widgets, not names,
        so the caller can mark exactly what it found."""
        missing = []
        if not self.title_edit.text().strip():
            missing.append(self.title_edit)
        return missing

    @staticmethod
    def _set_missing(widget: QWidget, missing: bool) -> None:
        """Flip the dynamic ``fieldMissing`` property and force a restyle, so
        the field's border follows the property."""
        if widget.property("fieldMissing") == missing:
            return
        widget.setProperty("fieldMissing", missing)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _refresh_required_state(self, *args: object) -> None:
        """Mark every empty required field red once a save has been tried with
        one empty, and never before. Called on construction, on every keystroke
        in a required field and on each refused save."""
        shown = self._missing_required() if getattr(self, "_save_tried", False) else []
        self._set_missing(self.title_edit, self.title_edit in shown)
        self._set_missing(self.title_label, self.title_edit in shown)

    def _update_visible_fields(self) -> None:
        is_task = self.type_combo.currentText() == "Task / Issue"
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
        # "Epic Name *"), so its red state is recomputed whenever the kind
        # does.
        self._refresh_required_state()

    def _load_existing_data(self) -> None:
        try:
            if self.mode == "task":
                row = self.conn.execute(
                    "SELECT title, description, status, tier, epic_id, "
                    "COALESCE(assignee, 'user'), COALESCE(reporter, 'user'), COALESCE(estimate, ''), "
                    "COALESCE(record_type, 'build'), COALESCE(stage, 'backlog'), "
                    "block_reason, due_date "
                    "FROM task WHERE id=?",
                    (self.record_id,),
                ).fetchone()
                if row:
                    self.title_edit.setText(row[0] or "")
                    self.desc_edit.setPlainText(row[1] or "")
                    current_status = row[2] if row[2] in ["todo", "doing", "done"] else "todo"
                    self.status_combo.setCurrentIndex(
                        max(self.status_combo.findData(current_status), 0)
                    )
                    tier_idx = self.tier_combo.findData((row[3] or "").lower() or None)
                    self.tier_combo.setCurrentIndex(max(tier_idx, 0))
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
                    block_idx = self.block_combo.findData(row[10])
                    self.block_combo.setCurrentIndex(max(block_idx, 0))
                    stage = row[9] if row[9] in STAGES else "backlog"
                    self.stage_combo.setCurrentIndex(max(self.stage_combo.findData(stage), 0))
                    self._loaded_stage = stage
                    self._loaded_status = current_status
                    due = QDate.fromString(row[11] or "", "yyyy-MM-dd")
                    self.due_edit.setDate(due if due.isValid() else NO_DUE_DATE)

                self._render_log()

            elif self.mode == "epic":
                row = self.conn.execute(
                    "SELECT name, description, type, status FROM epic WHERE id=?", (self.record_id,)
                ).fetchone()
                if row:
                    self.title_edit.setText(row[0] or "")
                    self.desc_edit.setPlainText(row[1] or "")
                    self._loaded_epic_type = row[2]
                    self.epic_type_combo.setCurrentIndex(
                        max(self.epic_type_combo.findData(_epic_kind(row[2])), 0)
                    )
                    self.epic_status_combo.setCurrentIndex(
                        max(self.epic_status_combo.findData(row[3] or "not started"), 0)
                    )
        except sqlite3.OperationalError:
            pass

    def _render_log(self, _checked: bool | None = None) -> None:
        if self.record_id is None:
            return
        lines = log_lines(
            self.conn,
            self.record_id,
            comments=self.log_filter.value() in ("all", "comments"),
            changes=self.log_filter.value() in ("all", "changes"),
        )
        self.log_view.setPlainText("\n".join(lines) if lines else "(Nothing to show.)")

    def _post_log_entry(self) -> None:
        if self.record_id is None:
            return
        body = self.log_post_input.text().strip()
        if not body:
            return
        record_id = self.record_id
        if not write(
            self.conn,
            self,
            f"The comment on #{record_id}",
            lambda: self.conn.execute(
                "INSERT INTO issue_log (task_id, author, body, created_at) VALUES (?,?,?,?)",
                (record_id, "user", body, _utcnow()),
            ),
        ):
            return
        self.log_post_input.clear()
        self._render_log()

    def _handle_delete(self) -> None:
        if confirm(
            self,
            f"Delete this {self.mode}",
            f"Permanently delete this {self.mode}? This cannot be undone.",
            "Delete",
            destructive=True,
        ):
            record_id = self.record_id

            def delete() -> None:
                if self.mode == "task":
                    self.conn.execute("DELETE FROM issue_log WHERE task_id=?", (record_id,))
                    self.conn.execute("DELETE FROM task_event WHERE task_id=?", (record_id,))
                    self.conn.execute("DELETE FROM attachment WHERE task_id=?", (record_id,))
                    # Both ends of every link, so nothing is left pointing at a
                    # ticket that no longer exists.
                    if record_id is not None:
                        remove_links_for_task(self.conn, record_id)
                    self.conn.execute("DELETE FROM task WHERE id=?", (record_id,))
                elif self.mode == "epic":
                    self.conn.execute("UPDATE task SET epic_id=NULL WHERE epic_id=?", (record_id,))
                    self.conn.execute("DELETE FROM epic WHERE id=?", (record_id,))

            if not write(self.conn, self, f"The deletion of this {self.mode}", delete):
                return
            # (behaviour preserved from the pre-split monolith): callers do
            # `if dlg.exec() == Accepted: dlg.save_data()`, so save_data() runs
            # once more after delete. Harmless — its statements target the now-
            # deleted record_id and affect zero rows — and it lets the caller's
            # refresh path run.
            self.done(QDialog.DialogCode.Accepted)

    def _append_order(self, stage: str, status: str) -> int:
        """sort_order that appends a task to the BOTTOM of its destination list:
        the Backlog is one combined list (keyed on stage), the active Board is a
        list per status column (keyed on stage+status)."""
        if stage == "active":
            row = self.conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage='active' AND status=?",
                (status,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage=?", (stage,)
            ).fetchone()
        return int(row[0]) + 1

    def save_data(self, fallback_epic: int | None = None) -> None:
        title = self.title_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()
        if not title:
            # Unreachable through the UI: OK is disabled and accept() refuses
            # while the title is empty. Kept because a titleless write is worse
            # than no write, and _handle_delete deliberately re-enters here.
            return

        chosen_type = self.type_combo.currentText()
        closing = False

        if chosen_type == "Task / Issue":
            status = self.status_combo.currentData()
            stage = self.stage_combo.currentData()
            tier = self.tier_combo.currentData()
            epic_id = self.epic_combo.currentData() or fallback_epic or self.fallback_epic_id
            owner = (self.owner_edit.currentData() or "user").strip() or "user"
            originator = self.originator_edit.text().strip() or "user"
            estimate = self.estimate_combo.currentData() or None
            record_type = self._current_record_type()
            due_date = (
                None
                if self.due_edit.date() <= NO_DUE_DATE
                else self.due_edit.date().toString("yyyy-MM-dd")
            )
            # closed_at is the moment the card went done, and only the
            # transition writes it: a card that was already done keeps the
            # finish it has, so correcting a typo on it does not move its
            # finish to today and inflate every duration measured from it.
            closed_at = _utcnow() if status == "done" else None
            if self.record_id is not None and status == "done" and self._loaded_status == "done":
                held = self.conn.execute(
                    "SELECT closed_at FROM task WHERE id=?", (self.record_id,)
                ).fetchone()
                if held is not None:
                    closed_at = held[0]
            # A finished card is not blocked, so Done clears the reason whatever
            # the picker says.
            block_reason = None if status == "done" else self.block_combo.currentData()

            if self.record_id is None:
                sort_order = self._append_order(stage, status)
                ts = _utcnow()
                cur = self.conn.execute(
                    "INSERT INTO task (epic_id, title, description, status, stage, sort_order, "
                    "tier, assignee, reporter, estimate, record_type, block_reason, "
                    "due_date, closed_at, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        epic_id,
                        title,
                        desc,
                        status,
                        stage,
                        sort_order,
                        tier,
                        owner,
                        originator,
                        estimate,
                        record_type,
                        block_reason,
                        due_date,
                        closed_at,
                        ts,
                        ts,
                    ),
                )
                # The ticket now has an id, so links entered during creation can
                # finally be written against it. An INSERT always gives its row one.
                new_id = cast(int, cur.lastrowid)
                self.links.flush_pending(new_id)
                if status == "done":
                    finishing.finish(self.conn, new_id)
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
                        "sort_order=?, tier=?, assignee=?, reporter=?, estimate=?, "
                        "record_type=?, block_reason=?, due_date=?, closed_at=? WHERE id=?",
                        (
                            epic_id,
                            title,
                            desc,
                            status,
                            stage,
                            sort_order,
                            tier,
                            owner,
                            originator,
                            estimate,
                            record_type,
                            block_reason,
                            due_date,
                            closed_at,
                            self.record_id,
                        ),
                    )
                else:
                    self.conn.execute(
                        "UPDATE task SET epic_id=?, title=?, description=?, status=?, stage=?, "
                        "tier=?, assignee=?, reporter=?, estimate=?, record_type=?, "
                        "block_reason=?, due_date=?, closed_at=? WHERE id=?",
                        (
                            epic_id,
                            title,
                            desc,
                            status,
                            stage,
                            tier,
                            owner,
                            originator,
                            estimate,
                            record_type,
                            block_reason,
                            due_date,
                            closed_at,
                            self.record_id,
                        ),
                    )
                # What done means for the board, on the one transition that
                # means it: a standing card archives itself, a project card
                # waits in Done for its epic, and a card taken out of done
                # returns to the board.
                if status != self._loaded_status:
                    if status == "done":
                        finishing.finish(self.conn, self.record_id)
                    elif self._loaded_status == "done":
                        finishing.reopen(self.conn, self.record_id)

        elif chosen_type == "Epic":
            # A kind the user did not touch is written back exactly as it
            # arrived, so the prose an older board contains survives until someone
            # chooses one of the two kinds over it.
            chosen_kind = self.epic_type_combo.currentData()
            etype = (
                self._loaded_epic_type
                if (
                    self.record_id is not None and _epic_kind(self._loaded_epic_type) == chosen_kind
                )
                else chosen_kind
            )
            if chosen_kind == STANDING_KIND:
                clash = finishing.standing_conflict(self.conn, self.record_id)
                if clash:
                    notify(self, "This board already has a standing workstream", clash)
                    etype = self._loaded_epic_type
                    self.epic_type_combo.setCurrentIndex(
                        max(self.epic_type_combo.findData(_epic_kind(self._loaded_epic_type)), 0)
                    )
            estatus = self.epic_status_combo.currentData()
            if self.record_id is None:
                self.conn.execute(
                    "INSERT INTO epic (name, description, type, status) VALUES (?,?,?,?)",
                    (title, desc, etype, estatus),
                )
            else:
                # Giving an epic a finished status is what ends the effort: its
                # finished cards leave the board and its report is written, in
                # epic_closure.close_epic. Only the transition does that, so an
                # edit to an epic that was already finished changes what it says
                # and nothing else, and a refused closure keeps the rest of the
                # edit and leaves the status where it was.
                prior = self.conn.execute(
                    "SELECT status FROM epic WHERE id=?", (self.record_id,)
                ).fetchone()
                closure = self._epic_closure()
                finished = closure.FINISHED_STATUSES if closure else frozenset()
                was = (prior[0] if prior else "") or ""
                closing = (estatus or "").lower() in finished and was.lower() not in finished
                if closing and closure is not None:
                    refused = closure.refusal(self.conn, self.record_id)
                    if refused:
                        notify(self, "This epic does not close", refused)
                        estatus, closing = (prior[0] if prior else estatus), False
                self.conn.execute(
                    "UPDATE epic SET name=?, description=?, type=?, status=? WHERE id=?",
                    (title, desc, etype, estatus, self.record_id),
                )
                if closing:
                    self.conn.execute(
                        "UPDATE epic SET closed_at=? WHERE id=? AND closed_at IS NULL",
                        (_utcnow(), self.record_id),
                    )

        self.conn.commit()

        if closing and closure is not None and self.record_id is not None:
            result = closure.close_epic(self.conn, self.record_id)
            if result.report is not None and not (result.report.ok or result.report.skipped):
                notify(
                    self,
                    "Report not written",
                    f"{len(result.archived)} card(s) were archived, but the "
                    f"report for this epic could not be written.\n\n"
                    f"{result.report.error}",
                )
