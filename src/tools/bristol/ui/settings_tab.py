"""ui/settings_tab.py — the Settings tab: what Bristol Tickets does, and what an
agent session does.

Every field here reads and writes ``config/config.local.json`` through
``config_file``, the same helper the setup wizard uses, so a choice has one
home. A key this build does not offer is left exactly as it was on save.

The page is two sections, split by which program reads the key. Bristol Tickets
reads the board and appearance keys and acts on them itself. An agent session
reads the session keys; this app only writes them.

Both sections share one form, so every label starts at the same left edge and
every control at the same one — a section heading is a row that spans both
columns rather than a form of its own.

The theme applies the moment it is picked, so it can be compared against the
board it themes. Save is what commits every field on the page, the theme
included.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local; see module docstring

from .settled_combo import SettledComboBox
from .theme import CHOICES as THEME_CHOICES
from .theme import space

# What each stored value is called on screen. A caption names the column a card
# lands in, which is what the user sees happen.
NEW_TICKET_CHOICES = [
    ("active", "To Do"),
    ("backlog", "Backlog"),
]

# How far a session runs when it is told to continue. The stored value is the
# boolean the agent reads; these are its two positions named for a reader.
WORK_SCOPE_CHOICES = [
    (False, "One Ticket"),
    (True, "Whole Queue"),
]


def _heading(text: str) -> QLabel:
    """A section heading, added as a row that spans the form's two columns."""
    label = QLabel(text)
    label.setObjectName("sectionHeader")
    label.setContentsMargins(0, space("lg"), 0, 0)
    return label


def _fill(combo: QComboBox, choices) -> QComboBox:
    """Load a picker's options and size it to the widest of them.

    A combo left at its default policy sizes to whichever option happens to be
    current, so a longer one is drawn truncated the moment it is picked.
    """
    for value, caption in choices:
        combo.addItem(caption, value)
    combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
    return combo


class SettingsTab(QWidget):
    def __init__(self, parent=None, on_appearance_changed=None) -> None:
        super().__init__(parent)

        # Called when the theme picker moves, so the window it lives in can
        # re-theme itself. Absent in a bare construction (the smoke check), where
        # there is no window to re-theme.
        self._on_appearance_changed = on_appearance_changed

        self.new_ticket = _fill(QComboBox(), NEW_TICKET_CHOICES)
        self.new_ticket.setToolTip(
            "Where a new card lands when the agent filing it names no tab.")

        self.appearance = _fill(QComboBox(), THEME_CHOICES)
        self.appearance.currentIndexChanged.connect(self._preview_appearance)

        # Which agent the next session runs as: the one field here that decides
        # what a session is rather than how it behaves. It is a settled combo
        # because a wheel gesture aimed past the page must not move it.
        self.next_agent = SettledComboBox()
        self.next_agent.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.next_agent.setToolTip(
            "The agent the next session starts as. Saving writes active_agent "
            "into the configuration and nothing else.")

        self.work_scope = _fill(QComboBox(), WORK_SCOPE_CHOICES)
        self.work_scope.setToolTip(
            "How far a session goes when you say continue.")

        # No text of its own: the row label carries the words, so the box sits
        # in the control column with every picker.
        self.suggested_commit = QCheckBox()
        self.suggested_commit.setToolTip(
            "When a session ends having written files inside a git working "
            "tree, it offers a commit block to paste. It never runs it.")

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        form.setHorizontalSpacing(space("xl"))
        form.setVerticalSpacing(space("lg"))

        form.addRow(_heading("Bristol Tickets"))
        form.addRow("Ticket Destination", self.new_ticket)
        form.addRow("Theme", self.appearance)
        form.addRow(_heading("Agent Sessions"))
        form.addRow("Agent", self.next_agent)
        form.addRow("Work Scope", self.work_scope)
        form.addRow("Git Commit on Session Close", self.suggested_commit)

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("globalCreateBtn")
        self.save_btn.clicked.connect(self._save)
        self.status = QLabel()
        self.status.setObjectName("formCaption")
        self.status.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.setSpacing(space("lg"))
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.status, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("xl"))
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addStretch(1)

        self.reload()

    def _preview_appearance(self) -> None:
        """Apply the picked theme to the running app without writing anything."""
        if self._on_appearance_changed is not None:
            self._on_appearance_changed(self.appearance.currentData())

    def _load_agents(self) -> None:
        """Offer the configured agents, opened on the active one.

        Where the configuration names an agent this installation does not
        configure, that name is offered too, so the page shows what a session
        would actually start as. Where there is no list at all the picker is
        empty and unclickable rather than offering a name no session would run
        as.
        """
        slugs = config_file.agent_slugs()
        active = config_file.get("active_agent")
        if isinstance(active, str) and active and active not in slugs:
            slugs = [active, *slugs]
        self.next_agent.clear()
        self.next_agent.addItems(slugs)
        if active in slugs:
            self.next_agent.setCurrentText(active)
        self.next_agent.setEnabled(bool(slugs))

    def reload(self) -> None:
        """Show what the configuration currently says."""
        target = config_file.path()
        placed = target is not None and target.exists()
        self._load_agents()
        stored = config_file.get(
            config_file.NEW_TICKET_STAGE, config_file.NEW_TICKET_STAGE_DEFAULT
        )
        index = self.new_ticket.findData(stored)
        self.new_ticket.setCurrentIndex(index if index >= 0 else 0)
        scope = self.work_scope.findData(bool(config_file.get(
            config_file.WORK_WHOLE_QUEUE, config_file.WORK_WHOLE_QUEUE_DEFAULT
        )))
        self.work_scope.setCurrentIndex(scope if scope >= 0 else 0)
        self.suggested_commit.setChecked(bool(config_file.get(
            config_file.SUGGESTED_COMMIT, config_file.SUGGESTED_COMMIT_DEFAULT
        )))
        scheme = config_file.get(
            config_file.APPEARANCE_SCHEME, config_file.APPEARANCE_SCHEME_DEFAULT
        )
        scheme_index = self.appearance.findData(scheme)
        self.appearance.blockSignals(True)
        self.appearance.setCurrentIndex(scheme_index if scheme_index >= 0 else 0)
        self.appearance.blockSignals(False)
        self.setEnabled(placed)
        # An unplaced clone has nothing to write to, and says so where a save
        # result would otherwise appear.
        self.status.setText(
            "" if placed else "No configuration file yet — run File → Setup…"
        )

    def _save(self) -> None:
        changes = {
            config_file.NEW_TICKET_STAGE: self.new_ticket.currentData(),
            config_file.WORK_WHOLE_QUEUE: self.work_scope.currentData(),
            config_file.SUGGESTED_COMMIT: self.suggested_commit.isChecked(),
            config_file.APPEARANCE_SCHEME: self.appearance.currentData(),
        }
        # An empty picker means this installation configures no agents. Writing
        # its blank would name an agent no session could run as.
        if self.next_agent.currentText():
            changes["active_agent"] = self.next_agent.currentText()
        try:
            written = config_file.update(changes)
        except OSError as exc:
            self.status.setText(f"Not saved: {exc}")
            return
        self.status.setText(f"Saved to {written.name}")
