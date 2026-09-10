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

Theme and Light & Dark are two rows because they are two choices: the first
names a theme, the second which half of it is drawn. A theme with no dark half
leaves Dark and Follow System unclickable and says why on hover, rather than
hiding them — an option nobody can find is not an invitation to build one.

The theme applies the moment it is picked, so it can be compared against the
board it themes, and each control writes its own key as it is moved.

Which themes the picker offers is a third thing, and it sits behind the Manage
Themes button: the choice is made every session and the collection is touched
rarely, so the collection is what goes behind a door. What that window hands
back is the difference from what this build ships, stored under one key.
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

from .settled_combo import SettledComboBox, fill_words
from .theme import (
    LIGHT_MODE,
    MODE_CHOICES,
    NO_DARK_HALF,
    appearance_choice,
    collection_differences,
    install_collection,
    register_collection,
    space,
    theme_choices,
    theme_has_dark,
)
from .theme_manager import ThemeManagerDialog

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


class SettingsTab(QWidget):
    def __init__(self, parent=None, on_appearance_changed=None) -> None:
        super().__init__(parent)

        # Called when the theme picker moves, so the window it lives in can
        # re-theme itself. Absent in a bare construction (the smoke check), where
        # there is no window to re-theme.
        self._on_appearance_changed = on_appearance_changed

        self.new_ticket = fill_words(QComboBox(), NEW_TICKET_CHOICES)
        self.new_ticket.currentIndexChanged.connect(
            lambda _i: self._write(config_file.NEW_TICKET_STAGE,
                                   self.new_ticket.currentData(),
                                   "Ticket Destination"))
        self.new_ticket.setToolTip(
            "Where a new card lands when the agent filing it names no tab.")

        # The collection this installation offers, as it currently stands. The
        # picker is filled from it rather than from what the build ships, so a
        # theme added, renamed or deleted is in the list the moment it is.
        self._collection = register_collection(
            config_file.get(config_file.APPEARANCE_THEMES),
            config_file.get(config_file.APPEARANCE_CUSTOM))

        self.theme = fill_words(QComboBox(), theme_choices(self._collection))
        self.theme.currentIndexChanged.connect(self._theme_chosen)
        self.theme.setToolTip("The pair of palettes the board is drawn from.")

        self.manage = QPushButton("Manage Themes…")
        self.manage.setToolTip(
            "Add a theme, rename one, change any theme's colours, or delete "
            "the ones you do not want.")
        self.manage.clicked.connect(self._manage_themes)

        self.mode = fill_words(QComboBox(), MODE_CHOICES)
        self.mode.currentIndexChanged.connect(self._mode_chosen)
        self.mode.setToolTip(
            "Which half of the theme is drawn, or the one the OS is set to.")

        # Which agent the next session runs as: the one field here that decides
        # what a session is rather than how it behaves. It is a settled combo
        # because a wheel gesture aimed past the page must not move it.
        self.next_agent = SettledComboBox()
        self.next_agent.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        # `picked` fires only on a deliberate choice from an open list, so the
        # one control that decides what the next session IS cannot be written by
        # a gesture aimed past the page.
        self.next_agent.picked.connect(
            lambda slug: self._write("active_agent", slug, "Agent"))
        self.next_agent.setToolTip(
            "The agent the next session starts as. Choosing one writes "
            "active_agent into the configuration and nothing else.")

        self.work_scope = fill_words(QComboBox(), WORK_SCOPE_CHOICES)
        self.work_scope.currentIndexChanged.connect(
            lambda _i: self._write(config_file.WORK_WHOLE_QUEUE,
                                   self.work_scope.currentData(), "Work Scope"))
        self.work_scope.setToolTip(
            "How far a session goes when you say continue.")

        # No text of its own: the row label carries the words, so the box sits
        # in the control column with every picker.
        self.suggested_commit = QCheckBox()
        self.suggested_commit.toggled.connect(
            lambda on: self._write(config_file.SUGGESTED_COMMIT, on,
                                   "Git Commit on Session Close"))
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
        form.addRow("Theme", self.theme)
        form.addRow("Light && Dark", self.mode)
        form.addRow("Themes", self.manage)
        form.addRow(_heading("Agent Sessions"))
        form.addRow("Agent", self.next_agent)
        form.addRow("Work Scope", self.work_scope)
        form.addRow("Git Commit on Session Close", self.suggested_commit)

        self.status = QLabel()
        self.status.setObjectName("formCaption")
        self.status.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.setSpacing(space("lg"))
        buttons.addWidget(self.status, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("xl"))
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addStretch(1)

        # Raised while reload() seats every control, so seating a stored value
        # is never mistaken for someone choosing it.
        self._loading = False
        self.reload()

    def _theme_chosen(self) -> None:
        """Offer the modes the new theme can draw, re-theme, and keep the
        choice."""
        self._seat_modes()
        self._redraw()
        self._write(config_file.APPEARANCE_THEME,
                    self.theme.currentData(), "Theme")

    def _mode_chosen(self) -> None:
        """Re-theme the running app, then keep the mode."""
        self._redraw()
        self._write(config_file.APPEARANCE_MODE,
                    self.mode.currentData(), "Light & Dark")

    def _redraw(self) -> None:
        """Draw the running app in the theme and mode the page is showing."""
        if self._on_appearance_changed is not None:
            self._on_appearance_changed(self.theme.currentData(),
                                        self.mode.currentData())

    def _seat_modes(self) -> None:
        """Offer only the modes the theme in force can draw.

        A theme with no dark half leaves Dark and Follow System unclickable
        carrying the reason, and the row sits on Light, which is what the app
        draws for such a theme whatever is stored. The stored mode is left
        alone, so returning to a theme that has both halves returns to it.
        """
        has_dark = theme_has_dark(self.theme.currentData())
        model = self.mode.model()
        for index in range(self.mode.count()):
            allowed = has_dark or self.mode.itemData(index) == LIGHT_MODE
            model.item(index).setEnabled(allowed)
            self.mode.setItemData(index, "" if allowed else NO_DARK_HALF,
                                  Qt.ToolTipRole)
        if not has_dark:
            self._seat(self.mode, LIGHT_MODE)
        else:
            self._seat(self.mode, self._stored_appearance()[1])

    def _manage_themes(self) -> None:
        """Edit the collection, keep the difference, and re-offer what it comes
        to.

        A window closed on Cancel puts the installed collection and the theme
        in force back, so a preview the user then declined leaves nothing
        behind.
        """
        was_theme, _was_mode = self._stored_appearance()
        dialog = ThemeManagerDialog(self._collection, was_theme, parent=self,
                                    on_preview=self._preview_themes)
        if not dialog.exec():
            install_collection(self._collection)
            self._seat(self.theme, was_theme)
            self._seat_modes()
            self._redraw()
            return
        self._collection = install_collection(dialog.themes())
        self._write(
            config_file.APPEARANCE_THEMES,
            collection_differences(self._collection,
                                   config_file.get(config_file.APPEARANCE_CUSTOM)),
            "Themes")
        self._offer_themes()
        theme = dialog.theme_in_force()
        if theme != was_theme:
            self._write(config_file.APPEARANCE_THEME, theme, "Theme")
        self._seat(self.theme, theme)
        self._seat_modes()
        self._redraw()

    def _offer_themes(self) -> None:
        """Re-fill the Theme picker from the collection, keeping the theme it
        is sitting on where that theme is still in it."""
        was = self.theme.currentData()
        seating, self._loading = self._loading, True
        try:
            self.theme.clear()
            fill_words(self.theme, theme_choices(self._collection))
        finally:
            self._loading = seating
        self._seat(self.theme, was)

    def _preview_themes(self, theme: str, collection: dict,
                        half: str | None = None) -> None:
        """Draw the running app in a theme the manage-themes window is still
        holding, in the half it is showing.

        The half wins over the stored mode while that window is open, so the
        colours being edited are the colours on the board. Closing it draws the
        stored mode again, whichever way it closed.
        """
        install_collection(collection)
        if self._on_appearance_changed is not None:
            self._on_appearance_changed(theme, half or self.mode.currentData())

    def _stored_appearance(self) -> tuple[str, str]:
        """The theme and mode the configuration currently says, migrating the
        one key a build before these two wrote."""
        return appearance_choice(
            config_file.get(config_file.APPEARANCE_THEME),
            config_file.get(config_file.APPEARANCE_MODE),
            config_file.get(config_file.APPEARANCE_SCHEME))

    def _seat(self, combo: QComboBox, value) -> None:
        """Put a picker on a value without it reading as a choice made."""
        was = self._loading
        self._loading = True
        try:
            index = combo.findData(value)
            combo.setCurrentIndex(index if index >= 0 else 0)
        finally:
            self._loading = was

    def _write(self, key: str, value, caption: str) -> None:
        """Persist one choice at the moment it is made.

        A page of pickers behind a Save button asks the user to remember a second
        step, and a choice that looks made but was never written is the failure
        that follows. Each control writes its own key and nothing else, so a
        failure names the row it belongs to.
        """
        if self._loading or not self.isEnabled():
            return
        try:
            config_file.update({key: value})
        except OSError as exc:
            self.status.setText(f"{caption} not saved: {exc}")
            return
        self.status.setText(f"{caption} saved.")

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
        self._loading = True
        try:
            self._reload()
        finally:
            self._loading = False

    def _reload(self) -> None:
        target = config_file.path()
        placed = target is not None and target.exists()
        self._collection = register_collection(
            config_file.get(config_file.APPEARANCE_THEMES),
            config_file.get(config_file.APPEARANCE_CUSTOM))
        self._offer_themes()
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
        theme, mode = self._stored_appearance()
        self._seat(self.theme, theme)
        self._seat(self.mode, mode)
        self._seat_modes()
        self.setEnabled(placed)
        # An unplaced clone has nothing to write to, and says so where a save
        # result would otherwise appear.
        self.status.setText(
            "" if placed else "No configuration file yet — run File → Setup…"
        )
