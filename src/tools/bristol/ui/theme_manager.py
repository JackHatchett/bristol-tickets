"""ui/theme_manager.py — Manage Themes: the collection, edited in one window.

Settings' Manage Themes button opens this. Every theme is listed down the left
and the selected one's name and colours stand on the right, so adding a theme,
renaming one, changing its colours and deleting it are four things in one place
rather than four doors.

The shipped themes are starting points rather than fixtures. What this window
hands back is the difference from what the build ships — a theme added, a name
changed, a palette stored under a shipped theme's name, a shipped name deleted
— and Settings is what stores it, in ``config/config.local.json``. So editing
Pumpkin changes what Pumpkin looks like on this installation and leaves the
repository's own tree untouched, and Restore Shipped Themes puts every shipped
theme back exactly as this build defines it.

A theme's id never changes. The name on screen is free to, because what a
stored choice names is the id, so a rename migrates nothing.

The dark half of a theme is carried through untouched: this window edits the
light palette, which is the one every theme has.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from .dialogs import confirm
from .palette_form import PaletteForm, complete_palette
from .theme import (
    CONTRAST_MIN,
    LAYOUT,
    order_collection,
    readable_on,
    shipped_collection,
    space,
    theme_id_for,
)

# What a new theme is called before it is named, and what stands in for a name
# left empty.
NEW_THEME_NAME = "New Theme"


class ThemeManagerDialog(QDialog):
    """The collection, edited. ``themes()`` is what was built and
    ``theme_in_force()`` the theme the app should be on afterwards.

    ``on_preview`` is called with the theme in hand and the working collection
    every time something changes, so the running app draws in the theme being
    edited while the window is open.
    """

    def __init__(self, collection: dict[str, dict], current: str,
                 parent=None, on_preview=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage Themes")
        self.setModal(True)
        self.setMinimumSize(LAYOUT["theme_dialog_min_w"],
                            LAYOUT["theme_dialog_min_h"])
        self._on_preview = on_preview

        # The working copy. Nothing here reaches the configuration until Save,
        # so a window closed on Cancel has changed nothing at all.
        self._collection = {theme_id: dict(record)
                            for theme_id, record in collection.items()}
        self._current = current if current in self._collection else next(
            iter(self._collection), current)
        self._selected = self._current
        # The themes added in this window, whose ids are still the window's to
        # choose. A theme's id is fixed the moment it is stored, so one added
        # here takes its id from the name it is saved under rather than from
        # the placeholder it was created with.
        self._fresh: set[str] = set()
        self._seating = False

        heading = QLabel("Manage Themes")
        heading.setObjectName("dialogHeading")

        blurb = QLabel(
            "Every theme this installation offers. The shipped ones are "
            "starting points: rename them, change their colours, delete the "
            "ones you do not want, and put them all back with Restore Shipped "
            "Themes."
        )
        blurb.setObjectName("formCaption")
        blurb.setWordWrap(True)

        self.list = QListWidget()
        self.list.setObjectName("themeList")
        self.list.setMinimumWidth(LAYOUT["theme_list_min_w"])
        self.list.currentRowChanged.connect(self._row_chosen)

        self.add_button = QPushButton("Add")
        self.add_button.setToolTip(
            "A new theme, seeded from the one selected.")
        self.add_button.clicked.connect(self._add_clicked)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("deleteBtn")
        self.delete_button.clicked.connect(self._delete_clicked)
        self.restore_button = QPushButton("Restore Shipped Themes")
        self.restore_button.setToolTip(
            "Put every theme this build ships back as it ships it. Themes you "
            "added are untouched.")
        self.restore_button.clicked.connect(self._restore_clicked)

        left_buttons = QHBoxLayout()
        left_buttons.setSpacing(space("md"))
        left_buttons.addWidget(self.add_button)
        left_buttons.addWidget(self.delete_button)
        left_buttons.addStretch(1)

        left = QVBoxLayout()
        left.setSpacing(space("md"))
        left.addWidget(self.list, 1)
        left.addLayout(left_buttons)
        left.addWidget(self.restore_button)

        self.name = QLineEdit()
        self.name.setToolTip(
            "What this theme is called. The name is yours; what the "
            "configuration stores is the theme, so renaming one keeps it.")
        self.name.textChanged.connect(self._name_typed)

        name_row = QHBoxLayout()
        name_row.setSpacing(space("lg"))
        name_label = QLabel("Name")
        name_label.setMinimumWidth(LAYOUT["palette_caption_w"])
        name_row.addWidget(name_label)
        name_row.addWidget(self.name, 1)

        self.form = PaletteForm(on_change=self._palette_typed)

        right = QVBoxLayout()
        right.setSpacing(space("lg"))
        right.addLayout(name_row)
        right.addWidget(self.form, 1)

        columns = QHBoxLayout()
        columns.setSpacing(space("xl"))
        columns.addLayout(left)
        columns.addLayout(right, 1)

        self.notice = QLabel()
        self.notice.setObjectName("formCaption")
        self.notice.setWordWrap(True)
        self.notice.setTextInteractionFlags(Qt.TextSelectableByMouse)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.save_button = buttons.button(QDialogButtonBox.Save)
        self.save_button.setObjectName("globalCreateBtn")
        self.save_button.setText("Save Themes")
        self.save_button.setAutoDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setAutoDefault(False)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("lg"))
        column.addWidget(heading)
        column.addWidget(blurb)
        column.addLayout(columns, 1)
        column.addWidget(self.notice)
        column.addWidget(buttons)

        self._fill_list()

    # ----- what was built --------------------------------------------------

    def themes(self) -> dict[str, dict]:
        """The collection as the window now holds it, the selected theme's
        unsaved edits included."""
        collection = {theme_id: dict(record)
                      for theme_id, record in self._collection.items()}
        if self._selected in collection:
            record = collection[self._selected]
            record["name"] = self.name.text().strip() or record["name"]
            record["light"] = complete_palette(self.form.palette())
        return order_collection(collection)

    def theme_in_force(self) -> str:
        """The theme the app should be drawing when this window closes."""
        return self._current

    def selected(self) -> str | None:
        """The theme whose name and colours are on the right."""
        return self._selected

    # ----- the collection --------------------------------------------------

    def select(self, theme_id: str) -> None:
        """Put the right-hand side on one theme, keeping the edits made to the
        one it is leaving."""
        if theme_id not in self._collection:
            return
        self._keep_edits()
        self._selected = theme_id
        self._seat_selection()
        row = list(self._collection).index(theme_id)
        if self.list.currentRow() != row:
            was, self._seating = self._seating, True
            try:
                self.list.setCurrentRow(row)
            finally:
                self._seating = was
        self._preview()

    def add(self, name: str = NEW_THEME_NAME) -> str:
        """A new theme, seeded from the one selected, and selected itself.

        Seeding from the theme in hand rather than from nothing is what makes
        every shipped theme a starting point: adding one is where a variation
        of Pumpkin that leaves Pumpkin alone comes from.
        """
        self._keep_edits()
        seed = self._collection.get(self._selected) or next(
            iter(self._collection.values()), None)
        theme_id = theme_id_for(name, self._collection)
        self._collection[theme_id] = {
            "name": self._unused_name(name),
            "light": complete_palette(seed["light"] if seed else None),
            "dark": dict(seed["dark"]) if seed and seed.get("dark") else None,
        }
        self._collection = order_collection(self._collection)
        self._fresh.add(theme_id)
        self._selected = theme_id
        self._fill_list()
        self.name.setFocus()
        self.name.selectAll()
        return theme_id

    def rename(self, name: str) -> None:
        """Call the selected theme something else."""
        if self._selected not in self._collection:
            return
        self.name.setText(name)

    def delete(self) -> bool:
        """Remove the selected theme. False where it refuses.

        The last theme stays: an app whose collection is empty has nothing to
        draw. Deleting the theme in force moves the app to the one that takes
        its place in the list.
        """
        if len(self._collection) <= 1 or self._selected not in self._collection:
            self._read_notice()
            return False
        order = list(self._collection)
        index = order.index(self._selected)
        self._collection.pop(self._selected)
        self._fresh.discard(self._selected)
        order.pop(index)
        self._selected = order[min(index, len(order) - 1)]
        if self._current not in self._collection:
            self._current = self._selected
        self._fill_list()
        return True

    def restore_shipped(self) -> None:
        """Put every theme this build ships back as it ships it, leaving the
        themes the user added exactly where they are."""
        self._keep_edits()
        shipped = shipped_collection()
        added = {theme_id: record
                 for theme_id, record in self._collection.items()
                 if theme_id not in shipped}
        restored = dict(shipped)
        restored.update(added)
        self._collection = order_collection(restored)
        if self._selected not in self._collection:
            self._selected = next(iter(self._collection))
        if self._current not in self._collection:
            self._current = self._selected
        self._fill_list()

    # ----- what stands between this and saving -----------------------------

    def name_problem(self) -> str:
        """Why the name on the right cannot be stored, or an empty string."""
        if self._selected not in self._collection:
            return ""
        name = self.name.text().strip()
        if not name:
            return "A theme needs a name."
        taken = {record["name"].casefold()
                 for theme_id, record in self._collection.items()
                 if theme_id != self._selected}
        if name.casefold() in taken:
            return f"Another theme is already called {name}."
        return ""

    def complaints(self) -> list[str]:
        """Everything the window has to say about what it is holding."""
        lines = []
        problem = self.name_problem()
        if problem:
            lines.append(problem)
        if len(self._collection) <= 1:
            lines.append("The last theme cannot be deleted.")
        lines.extend(self.form.complaints())
        return lines

    # ----- editing ---------------------------------------------------------

    def _row_chosen(self, row: int) -> None:
        if self._seating or row < 0:
            return
        order = list(self._collection)
        if row < len(order):
            self.select(order[row])

    def _add_clicked(self) -> None:
        self.add()
        self._preview()

    def _delete_clicked(self) -> None:
        if self._selected not in self._collection:
            return
        name = self._collection[self._selected]["name"]
        if len(self._collection) <= 1:
            self._read_notice()
            return
        if not confirm(self, f"Delete {name}?",
                       f"{name} leaves the list of themes on this "
                       f"installation. A shipped theme comes back with "
                       f"Restore Shipped Themes; one you added does not.",
                       "Delete", destructive=True):
            return
        self.delete()
        self._preview()

    def _restore_clicked(self) -> None:
        if not confirm(self, "Restore shipped themes?",
                       "Every theme this build ships goes back to the colours "
                       "and the name it ships with, and any you deleted come "
                       "back. Themes you added are untouched.",
                       "Restore"):
            return
        self.restore_shipped()
        self._preview()

    def _name_typed(self, _text: str) -> None:
        if self._seating:
            return
        self._mark_name()
        self._read_notice()
        row = self.list.currentRow()
        if 0 <= row < self.list.count():
            self.list.item(row).setText(self.name.text().strip()
                                        or NEW_THEME_NAME)

    def _palette_typed(self) -> None:
        if self._seating:
            return
        self._read_notice()
        self._preview()

    def _keep_edits(self) -> None:
        """Fold the right-hand side back into the theme it belongs to, before
        the selection moves off it."""
        if self._selected not in self._collection:
            return
        record = self._collection[self._selected]
        record["name"] = self.name.text().strip() or record["name"]
        record["light"] = complete_palette(self.form.palette())

    def _fill_list(self) -> None:
        was, self._seating = self._seating, True
        try:
            self.list.clear()
            for record in self._collection.values():
                self.list.addItem(record["name"])
            order = list(self._collection)
            if self._selected in order:
                self.list.setCurrentRow(order.index(self._selected))
        finally:
            self._seating = was
        self._seat_selection()

    def _seat_selection(self) -> None:
        """Show the selected theme's name and colours."""
        record = self._collection.get(self._selected)
        if record is None:
            return
        was, self._seating = self._seating, True
        try:
            self.name.setText(record["name"])
            self.form.set_palette(record["light"])
        finally:
            self._seating = was
        self._mark_name()
        self._read_notice()

    def _mark_name(self) -> None:
        # The border every empty required field in this app carries, for a name
        # that is empty or already taken: same fault, same mark.
        self.name.setProperty("fieldMissing", bool(self.name_problem()))
        self.name.style().unpolish(self.name)
        self.name.style().polish(self.name)

    def _read_notice(self) -> None:
        lines = self.complaints()
        self.notice.setText("\n".join(lines) if lines else
                            f"Every pair of text and surface clears "
                            f"{CONTRAST_MIN}:1.")
        # Drawn against the canvas the selected palette names, so the line that
        # says what is unreadable never becomes the unreadable thing.
        self.notice.setStyleSheet(f"color: {readable_on(self.form.ground())};")

    def _preview(self) -> None:
        """Draw the running app in the theme being edited."""
        if self._on_preview is None:
            return
        collection = self.themes()
        theme = self._selected if self._selected in collection else self._current
        self._on_preview(theme, collection)

    def accept(self) -> None:
        """Save, having said what fails rather than refusing quietly.

        A name that is empty or already taken is nothing to store and sends the
        window back. A palette under the readable ratio is still the user's to
        choose, so this names every pair that falls short and asks once.
        """
        if self.name_problem() or self.form.broken():
            self._read_notice()
            return
        failures = self.form.unreadable()
        if failures and not confirm(
            self, "Some text will be hard to read",
            f"This palette puts these under {CONTRAST_MIN}:1:\n\n"
            + "\n".join(f"• {line}" for line in failures)
            + "\n\nSave it anyway?",
            "Save Anyway",
        ):
            return
        self._keep_edits()
        self._name_fresh_themes()
        self._collection = order_collection(self._collection)
        super().accept()

    def _name_fresh_themes(self) -> None:
        """Give each theme added in this window an id taken from the name it is
        being saved under.

        A theme created before it is named would otherwise be stored under the
        placeholder, and a configuration full of `new_theme_2` says nothing
        about what is in it. Only a theme this window created is re-keyed: one
        that already exists is named by an id something may already have
        stored.
        """
        for theme_id in sorted(self._fresh):
            record = self._collection.get(theme_id)
            if record is None:
                continue
            taken = set(self._collection) - {theme_id}
            wanted = theme_id_for(record["name"], taken)
            if wanted == theme_id:
                continue
            self._collection[wanted] = self._collection.pop(theme_id)
            if self._selected == theme_id:
                self._selected = wanted
            if self._current == theme_id:
                self._current = wanted
        self._fresh.clear()

    def _unused_name(self, name: str) -> str:
        """``name``, or the first numbered version of it nothing else uses."""
        taken = {record["name"].casefold()
                 for record in self._collection.values()}
        if name.casefold() not in taken:
            return name
        suffix = 2
        while f"{name} {suffix}".casefold() in taken:
            suffix += 1
        return f"{name} {suffix}"
