"""ui/agents_tab.py — the Agents tab: the fleet, and one agent as a form.

Every fact on this page comes from ``src/tools/agent_tools/agents.py list
--json`` and ``skill_tools/skills.py list --json``, the same readers a session
uses, so the app and a session cannot disagree. Writing goes through
``create_agent.py``, ``import_agent.py``, ``agents.py edit`` and
``skills.py attach``/``detach`` —
the tools that own each part — so an agent made here and one made at the command
line are the same object.

The form holds every property an agent has and nothing else, and all of it is
editable but the name of an agent that already exists, which is what its charter
file and its config key are named after.

Each kind of property gets the control its kind deserves. A path is picked, not
typed, and the picked path is turned back into the spelling config stores by
``config_tools/data_paths.py --declare``, which owns that rule in both
directions. A folder carries the access it is granted beside it, so adding a
folder and deciding what may be done in it are one gesture. A notebook zone is a tick box per zone. An environment variable is a
name beside a value. A key this build has no control for keeps its own field,
named after the key and holding the JSON it holds, so nothing is lost and
nothing is guessed at.

The charter is one Markdown editor holding the whole document. It is not
parsed: a charter is prose somebody wrote, and shredding it into fields would
mean only the ones this app generated could be edited.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local; see module docstring

from .dialogs import confirm, notify
from .growing_edit import GrowingTextEdit
from .settled_combo import SettledComboBox, fill_words
from .row_card import card_list
from .theme import CARD_ROLE, LAYOUT, agent_caption, space

AGENTS_CLI = Path("src") / "tools" / "agent_tools" / "agents.py"
CREATE_CLI = Path("src") / "tools" / "agent_tools" / "create_agent.py"
IMPORT_CLI = Path("src") / "tools" / "agent_tools" / "import_agent.py"
SKILLS_CLI = Path("src") / "tools" / "skill_tools" / "skills.py"
PATHS_CLI = Path("src") / "tools" / "config_tools" / "data_paths.py"
NOTEBOOK_CLI = Path("src") / "tools" / "config_tools" / "notebook.py"

# What an agent cannot be without. The form marks each one and refuses a save
# while one is empty.
REQUIRED = ["slug", "description", "charter"]
FIELD_NAMES = {"slug": "Name", "description": "Description",
               "charter": "Charter"}

# What an agent may do in the notebook — src/tools/config_tools/notebook.py.
NOTEBOOK_MODES = [("per_folder", "Per Folder"), ("read_all", "Read All"),
                  ("write_all", "Write All")]
FOLDER_ACCESS = [("read", "Read"), ("write", "Write"), ("hide", "Hide")]


class NotebookAccess(QWidget):
    """Per Folder, Read All or Write All, and under Per Folder one row per
    folder attached in Settings with Read, Write and Hide.

    The rows are read from Settings each time the window opens, so a folder
    attached or detached there is here or gone. Choices are kept while Read All
    or Write All is chosen, so going back to Per Folder brings them back.
    """

    def __init__(self, entry: dict, folders: list[str]) -> None:
        super().__init__()
        entry = entry if isinstance(entry, dict) else {}
        mode = entry.get("mode") if entry.get("mode") in dict(NOTEBOOK_MODES) \
            else "per_folder"
        self._kept = dict(entry.get("folders") or {}) if "mode" in entry else {}
        self._legacy = "mode" not in entry and bool(entry)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))

        modes = QHBoxLayout()
        modes.setSpacing(space("lg"))
        self.mode_group = QButtonGroup(self)
        self.mode_buttons: dict[str, QRadioButton] = {}
        for value, label in NOTEBOOK_MODES:
            button = QRadioButton(label)
            button.setChecked(value == mode)
            self.mode_group.addButton(button)
            self.mode_buttons[value] = button
            modes.addWidget(button)
        modes.addStretch(1)
        column.addLayout(modes)

        self.rows = QWidget()
        grid = QGridLayout(self.rows)
        grid.setContentsMargins(space("lg"), space("sm"), 0, 0)
        grid.setHorizontalSpacing(space("lg"))
        grid.setVerticalSpacing(space("xs"))
        self.choices: dict[str, dict[str, QRadioButton]] = {}
        for row, folder in enumerate(folders):
            name = QLabel(folder)
            name.setObjectName("metaText")
            grid.addWidget(name, row, 0)
            group = QButtonGroup(self.rows)
            buttons = {}
            for col, (value, label) in enumerate(FOLDER_ACCESS, start=1):
                button = QRadioButton(label)
                button.setChecked(self._kept.get(folder, "hide") == value)
                group.addButton(button)
                buttons[value] = button
                grid.addWidget(button, row, col)
            self.choices[folder] = buttons
        grid.setColumnStretch(len(FOLDER_ACCESS) + 1, 1)
        column.addWidget(self.rows)
        self.mode_group.buttonToggled.connect(lambda *_: self._sync())
        self._sync()

    def _sync(self) -> None:
        self.rows.setVisible(self.mode() == "per_folder" and bool(self.choices))

    def mode(self) -> str:
        return next((v for v, b in self.mode_buttons.items() if b.isChecked()),
                    "per_folder")

    def values(self) -> dict:
        chosen = dict(self._kept)
        for folder, buttons in self.choices.items():
            chosen[folder] = next(v for v, b in buttons.items() if b.isChecked())
        return {"mode": self.mode(), "folders": chosen}

    def changed_from(self, entry: dict) -> bool:
        """Whether saving would change what the entry says."""
        if self._legacy:
            return True
        entry = entry if isinstance(entry, dict) else {}
        before = {"mode": entry.get("mode", "per_folder"),
                  "folders": dict(entry.get("folders") or {})}
        now = self.values()
        for folder in self.choices:
            before["folders"].setdefault(folder, "hide")
        return now != before

    def args(self) -> list[str]:
        out = ["--notebook-mode", self.mode()]
        for folder, access in self.values()["folders"].items():
            if folder in self.choices:
                out += ["--notebook-folder", f"{folder}={access}"]
        return out


def _required(label: str) -> str:
    return f"{label} *"


def _grant_option(grant: dict) -> str:
    """The option `agents.py` and `create_agent.py` take for this access."""
    return "--read-path" if grant["access"] == "read" else "--data-path"


ACCESS_CHOICES = [("write", "Read & write"), ("read", "Read only")]


def folder_grant(entry) -> dict:
    """One `key_data_paths` entry as a declared folder and the access it carries.

    An entry written before access was recorded is a bare string, and it reads
    as `write` — `src/tools/config_tools/data_paths.py`, which owns the rule and
    is what every session reads through.
    """
    if isinstance(entry, dict):
        declared = str(entry.get("path", ""))
        access = entry.get("access")
    else:
        declared, access = str(entry), None
    known = [value for value, _ in ACCESS_CHOICES]
    return {"path": declared,
            "access": access if access in known else known[0]}


class PathList(QWidget):
    """The folders or files an agent reaches: one row each, added with a picker.

    A path is machine-specific when it is picked and portable when it is
    stored, and `data_paths.py --declare` is what turns one into the other.

    A folder row carries the access it is granted beside it, because a grant is
    a folder and what may be done in it rather than a folder alone. A file row
    carries none: a context file is read.
    """

    def __init__(self, run, kind: str, add_label: str, parent=None, *,
                 access: bool = False) -> None:
        super().__init__(parent)
        self._run = run
        self._kind = kind
        self._access = access
        self._rows: list[tuple[QListWidgetItem, str, QComboBox | None]] = []

        self.list = QListWidget()
        # Its own name rather than the search list's: that one pads every
        # item for text a delegate draws, and a row here is a widget, which
        # such padding shrinks out of the item holding it.
        self.list.setObjectName("pathRows")
        self.list.setSelectionMode(QListWidget.NoSelection)
        self.list.setMinimumHeight(LAYOUT["path_list_min_h"])

        self.add_btn = QPushButton(add_label)
        self.add_btn.setAutoDefault(False)
        self.add_btn.clicked.connect(self._add)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addWidget(self.add_btn)
        row.addStretch(1)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))
        column.addWidget(self.list)
        column.addLayout(row)

    def set_values(self, entries: list) -> None:
        self.list.clear()
        self._rows = []
        for entry in entries:
            grant = folder_grant(entry)
            self._row(grant["path"], grant["access"])

    def values(self) -> list:
        out = []
        for _, declared, combo in self._rows:
            if self._access:
                out.append({"path": declared,
                            "access": combo.currentData()})
            else:
                out.append(declared)
        return out

    def _row(self, declared: str, access: str) -> None:
        holder = QWidget()
        label = QLabel(declared)
        label.setObjectName("pathRow")
        label.setWordWrap(False)
        label.setToolTip(declared)
        combo = None
        if self._access:
            combo = fill_words(SettledComboBox(), ACCESS_CHOICES)
            combo.setCurrentIndex(
                max(0, combo.findData(access)))
        drop = QPushButton("✕")
        drop.setAutoDefault(False)
        drop.setMaximumWidth(LAYOUT["env_choose_w"])

        line = QHBoxLayout(holder)
        line.setContentsMargins(space("sm"), space("xs"), space("sm"),
                                space("xs"))
        line.setSpacing(space("sm"))
        line.addWidget(label, 1)
        if combo is not None:
            line.addWidget(combo)
        line.addWidget(drop)

        # A row is as tall as its own contents once the stylesheet is on them,
        # and never shorter than one line of them: an unpolished widget reports
        # a height its padding has not reached yet, and a list item takes the
        # height it is given rather than growing to what it holds.
        holder.ensurePolished()
        item = QListWidgetItem()
        item.setSizeHint(holder.sizeHint().expandedTo(
            QSize(0, LAYOUT["path_row_min_h"])))
        self.list.addItem(item)
        self.list.setItemWidget(item, holder)
        self._rows.append((item, declared, combo))
        drop.clicked.connect(lambda: self._drop(item))

    def _drop(self, item: QListWidgetItem) -> None:
        declared = next((d for i, d, _ in self._rows if i is item), "")
        subject = "folder" if self._kind == "dir" else "file"
        if not confirm(self, f"Remove this {subject}?",
                       f"{declared} goes off this agent's list. "
                       f"Nothing on disk is touched.",
                       "Remove", destructive=True):
            return
        self._rows = [r for r in self._rows if r[0] is not item]
        self.list.takeItem(self.list.row(item))

    def _start_in(self) -> str:
        root = config_file.project_root()
        return str(root) if root else ""

    def _declared(self) -> list[str]:
        return [declared for _, declared, _ in self._rows]

    def _add(self) -> None:
        if self._kind == "dir":
            picked = QFileDialog.getExistingDirectory(
                self, "Choose a folder", self._start_in())
        else:
            picked, _ = QFileDialog.getOpenFileName(
                self, "Choose a file", self._start_in())
        if not picked:
            return
        code, out, _ = self._run(PATHS_CLI, "--declare", picked)
        declared = out.strip() if code == 0 and out.strip() else picked
        if declared not in self._declared():
            self._row(declared, ACCESS_CHOICES[0][0])


class EnvList(QWidget):
    """The environment variables an agent runs with: a name beside a value.

    These are Unix environment variables, read by the tools a session runs —
    where that agent's Zotero library is, which database file it keeps its
    records in. They are the agent's, not the machine's, which is why they are
    stored on its config entry rather than set in a shell profile.
    """

    def __init__(self, run, parent=None) -> None:
        super().__init__(parent)
        self._run = run
        self._rows: list[tuple[QWidget, QLineEdit, QLineEdit]] = []

        self.rows = QVBoxLayout()
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(space("sm"))

        self.add_btn = QPushButton("Add Variable")
        self.add_btn.setAutoDefault(False)
        self.add_btn.clicked.connect(lambda: self._add("", ""))

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))
        column.addLayout(self.rows)
        bottom = QHBoxLayout()
        bottom.setSpacing(space("md"))
        bottom.addWidget(self.add_btn)
        bottom.addStretch(1)
        column.addLayout(bottom)

    def set_values(self, env: dict) -> None:
        while self._rows:
            self._drop(self._rows[0][0], ask=False)
        for name, value in env.items():
            self._add(name, str(value))

    def values(self) -> dict:
        out = {}
        for _, name, value in self._rows:
            if name.text().strip():
                out[name.text().strip()] = value.text()
        return out

    def _add(self, name: str, value: str) -> None:
        holder = QWidget()
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Name")
        name_edit.setMaximumWidth(LAYOUT["env_name_w"])
        value_edit = QLineEdit(value)
        value_edit.setPlaceholderText("Value")
        choose = QPushButton("…")
        choose.setAutoDefault(False)
        choose.setMaximumWidth(LAYOUT["env_choose_w"])
        choose.clicked.connect(lambda: self._pick_into(value_edit))
        drop = QPushButton("✕")
        drop.setAutoDefault(False)
        drop.setMaximumWidth(LAYOUT["env_choose_w"])
        drop.clicked.connect(lambda _=False: self._drop(holder))
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(space("sm"))
        row.addWidget(name_edit)
        row.addWidget(value_edit, 1)
        row.addWidget(choose)
        row.addWidget(drop)
        self.rows.addWidget(holder)
        self._rows.append((holder, name_edit, value_edit))

    def _pick_into(self, field: QLineEdit) -> None:
        """A value that names a folder is picked; one that does not is typed."""
        root = config_file.project_root()
        picked = QFileDialog.getExistingDirectory(
            self, "Choose a folder", field.text() or (str(root) if root else ""))
        if picked:
            field.setText(picked)

    def _drop(self, holder: QWidget, ask: bool = True) -> None:
        named = next((n.text().strip() for h, n, _ in self._rows
                      if h is holder), "")
        if ask and named and not confirm(
                self, "Remove this variable?",
                f"{named} goes off this agent's list. The tools that read it "
                f"run without it afterwards.",
                "Remove", destructive=True):
            return
        self._rows = [r for r in self._rows if r[0] is not holder]
        self.rows.removeWidget(holder)
        holder.deleteLater()


class KeyFields(QWidget):
    """One field per config key this build has no control of its own for.

    Each is labelled with the key it holds and holds that key's value as the
    JSON it is. A flat list of strings would be the friendlier control, and it
    would be the wrong one: these values are objects, so a control that could
    only add a line would either refuse what is there or quietly flatten it.
    An agent with no such keys gets no section at all.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._fields: dict[str, QPlainTextEdit] = {}
        self.form = QFormLayout(self)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setSpacing(space("md"))
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)
        self.form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

    def set_values(self, extra: dict) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._fields = {}
        for key, value in extra.items():
            field = QPlainTextEdit(json.dumps(value, indent=2))
            field.setMinimumHeight(LAYOUT["extra_min_h"])
            self._fields[key] = field
            self.form.addRow(key, field)
        self.setVisible(bool(extra))

    def values(self) -> dict:
        """What the fields hold. Raises ValueError naming the key that is not
        JSON, so a refusal can say which one."""
        out = {}
        for key, field in self._fields.items():
            text = field.toPlainText().strip()
            if not text:
                continue
            try:
                out[key] = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{key} is not JSON: {exc}") from exc
        return out


class AgentDialog(QDialog):
    """One agent, whole. A blank one creates; a filled one edits."""

    def __init__(self, parent, record, run, taken, every_skill) -> None:
        super().__init__(parent)
        self._record = record
        self._run = run
        self._taken = taken
        self.creating = record is None
        # What the page behind says once this closes. Empty while nothing has
        # been written.
        self.status = ""

        slug = record["slug"] if record else "New Agent"
        self.setWindowTitle(slug)
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["agent_dialog_min_w"])
        self.setMinimumHeight(LAYOUT["agent_dialog_min_h"])
        self._open_at_a_readable_size()

        self.slug = QLineEdit(record["slug"] if record else "")
        self.slug.setEnabled(self.creating)
        self.description = GrowingTextEdit(min_lines=2, max_lines=4,
                                           newline_on_return=True)
        self.description.setText(record["description"] if record else "")

        self.identity = QLineEdit(record["identity"] if record else "")
        self.identity.setEnabled(not self.creating)
        self.identity_btn = QPushButton("Choose…")
        self.identity_btn.setAutoDefault(False)
        self.identity_btn.setEnabled(not self.creating)
        self.identity_btn.clicked.connect(self._pick_charter)
        identity_row = QWidget()
        identity_layout = QHBoxLayout(identity_row)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(space("sm"))
        identity_layout.addWidget(self.identity, 1)
        identity_layout.addWidget(self.identity_btn)

        self.charter = QPlainTextEdit(record["charter"] if record else "")
        self.charter.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.data_paths = PathList(run, "dir", "Add Folder…", access=True)
        self.data_paths.set_values(record["key_data_paths"] if record else [])
        self.context_files = PathList(run, "file", "Add File…")
        self.context_files.set_values(
            record["key_context_files"] if record else [])

        self.notebook = NotebookAccess(
            record["notebook_access"] if record else {}, self._attached(run))

        self.env = EnvList(run)
        self.env.set_values(record["env"] if record else {})

        self.skills = QListWidget()
        self.skills.setObjectName("searchResults")
        self.skills.setMinimumHeight(LAYOUT["skill_list_min_h"])
        held = set(record["skills"]) if record else set()
        for name in list(every_skill) + sorted(held - set(every_skill)):
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name in held else Qt.Unchecked)
            self.skills.addItem(item)

        self.extra = KeyFields()
        self.extra.set_values(record["extra"] if record else {})

        form = QFormLayout()
        form.setSpacing(space("lg"))
        form.setHorizontalSpacing(space("lg"))
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow(_required("Name"), self.slug)
        form.addRow(_required("Description"), self.description)
        form.addRow("Charter File", identity_row)
        form.addRow("Folders", self.data_paths)
        form.addRow("Context Files", self.context_files)
        form.addRow("Notebook", self.notebook)
        form.addRow("Environment Variables", self.env)
        form.addRow("Skills", self.skills)
        if record and record["extra"]:
            form.addRow("Other Keys", self.extra)

        page = QWidget()
        page.setLayout(form)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setWidget(page)
        self.scroll.setMinimumWidth(LAYOUT["agent_fields_min_w"])

        charter_label = QLabel(_required("Charter"))
        charter_label.setObjectName("sectionHeader")
        charter_side = QVBoxLayout()
        charter_side.setContentsMargins(0, 0, 0, 0)
        charter_side.setSpacing(space("sm"))
        charter_side.addWidget(charter_label)
        charter_side.addWidget(self.charter, 1)
        charter_pane = QWidget()
        charter_pane.setLayout(charter_side)
        charter_pane.setMinimumWidth(LAYOUT["charter_min_w"])

        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(space("lg"))
        split.addWidget(self.scroll)
        split.addWidget(charter_pane)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 4)

        heading = QLabel(agent_caption(slug) if self._record else slug)
        heading.setObjectName("dialogHeading")

        self.save_btn = QPushButton("Create" if self.creating else "Save")
        self.save_btn.setObjectName("globalCreateBtn")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save)
        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(self.save_btn)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("lg"))
        column.addWidget(heading)
        column.addWidget(split, 1)
        column.addLayout(row)

        if self.creating:
            self._start_from_skeleton()

    @staticmethod
    def _attached(run) -> list[str]:
        """The folders attached in Settings, read fresh."""
        code, out, _ = run(NOTEBOOK_CLI, "show", "--json")
        try:
            return [f["folder"] for f in json.loads(out)["folders"]] \
                if code == 0 else []
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def _pick_charter(self) -> None:
        root = config_file.project_root()
        start = str(root / "src" / "agent_identities") if root else ""
        picked, _ = QFileDialog.getSaveFileName(
            self, "Where the charter lives", start, "Markdown (*.md)")
        if not picked:
            return
        code, out, _ = self._run(PATHS_CLI, "--declare", picked)
        self.identity.setText(out.strip() if code == 0 and out.strip()
                              else picked)

    def _open_at_a_readable_size(self) -> None:
        """Open on most of the screen, not on the minimum.

        The minimum is what the form still works at; opening there leaves the
        last field just below the fold, where nobody looks for it.
        """
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        room = screen.availableGeometry()
        self.resize(
            max(LAYOUT["agent_dialog_min_w"],
                min(int(room.width() * 0.78), room.width() - 80)),
            max(LAYOUT["agent_dialog_min_h"],
                min(int(room.height() * 0.88), room.height() - 80)))

    def _start_from_skeleton(self) -> None:
        """A new charter opens on the shape the template gives, not on nothing."""
        self.slug.textChanged.connect(self._reskeleton)
        self._reskeleton(self.slug.text())

    def _reskeleton(self, slug: str) -> None:
        if not self.creating or self._charter_touched():
            return
        name = slug.strip() or "agent"
        code, out, _ = self._run(AGENTS_CLI, "skeleton", name)
        if code == 0:
            self._skeleton = out
            self.charter.setPlainText(out)
        self.identity.setText(f"src/agent_identities/{name}.md")

    def _charter_touched(self) -> bool:
        return self.charter.toPlainText() != getattr(self, "_skeleton", "")

    # ----- what the form holds, and what it refuses -------------------------

    def values(self) -> dict:
        checked = []
        for i in range(self.skills.count()):
            item = self.skills.item(i)
            if item.checkState() == Qt.Checked:
                checked.append(item.text())
        return {
            "slug": self.slug.text().strip(),
            "description": self.description.text().strip(),
            "identity": self.identity.text().strip(),
            "charter": self.charter.toPlainText(),
            "key_data_paths": self.data_paths.values(),
            "key_context_files": self.context_files.values(),
            "notebook_access": self.notebook.values(),
            "env": self.env.values(),
            "skills": checked,
        }

    def missing(self) -> list[str]:
        """The required fields left empty, in the order the form shows them."""
        values = self.values()
        empty = [name for name in REQUIRED if not str(values[name]).strip()]
        if not self.creating:
            empty = [n for n in empty if n != "slug"]
        return empty

    def _refuse(self, message: str) -> None:
        """A save that did not land is the one thing this window says in
        words, and it says it in a box the user has to dismiss."""
        notify(self, "Not Saved", message)

    def _save(self) -> None:
        values = self.values()
        empty = self.missing()
        if empty:
            named = ", ".join(FIELD_NAMES[name] for name in empty)
            self._refuse(f"Fill in {named}.")
            return
        try:
            extra = self.extra.values()
        except ValueError as exc:
            self._refuse(str(exc))
            return
        if self.creating and values["slug"] in self._taken:
            self._refuse(f"'{values['slug']}' is already an agent.")
            return

        with tempfile.TemporaryDirectory() as tmp:
            charter_file = Path(tmp) / "charter.md"
            charter_file.write_text(values["charter"], encoding="utf-8")
            extra_file = Path(tmp) / "extra.json"
            extra_file.write_text(json.dumps(extra), encoding="utf-8")
            if self.creating:
                code, out, err = self._run(
                    CREATE_CLI, *self._create_args(values, charter_file))
            else:
                args = self._edit_args(values, extra, charter_file, extra_file)
                code, out, err = ((0, "", "") if len(args) == 1
                                  else self._run(AGENTS_CLI, "edit", *args))
            if code != 0:
                self._refuse((err or out).strip() or "The write did not land.")
                return
            wrote = bool(out.strip())

        wrote = self._reconcile_skills(values) or wrote
        self.status = "Saved." if wrote else "Nothing changed."
        self.accept()

    def _reconcile_skills(self, values: dict) -> bool:
        """Attach and detach through the loader's own commands."""
        was = set(self._record["skills"]) if self._record else set()
        now = set(values["skills"])
        changed = False
        for name in sorted(now - was):
            self._run(SKILLS_CLI, "attach", name, "--agent", values["slug"])
            changed = True
        for name in sorted(was - now):
            self._run(SKILLS_CLI, "detach", name, "--agent", values["slug"])
            changed = True
        return changed

    @staticmethod
    def _create_args(values: dict, charter_file: Path) -> list[str]:
        notebook = values["notebook_access"]
        args = [values["slug"],
                "--description", values["description"],
                "--charter-file", str(charter_file),
                "--notebook-mode", notebook["mode"]]
        for folder, access in notebook["folders"].items():
            args += ["--notebook-folder", f"{folder}={access}"]
        for grant in values["key_data_paths"]:
            args += [_grant_option(grant), grant["path"]]
        for declared in values["key_context_files"]:
            args += ["--context-file", declared]
        for name, value in values["env"].items():
            args += ["--env", f"{name}={value}"]
        return args

    def _edit_args(self, values: dict, extra: dict, charter_file: Path,
                   extra_file: Path) -> list[str]:
        """Only what actually changed, so an untouched field is never written."""
        was = self._record
        args = [values["slug"]]
        if values["description"] != was["description"]:
            args += ["--description", values["description"]]
        if values["identity"] != was["identity"]:
            args += ["--identity", values["identity"]]
        if values["charter"] != was["charter"]:
            args += ["--charter-file", str(charter_file)]
        if values["key_data_paths"] != was["key_data_paths"]:
            for grant in values["key_data_paths"]:
                args += [_grant_option(grant), grant["path"]]
            if not values["key_data_paths"]:
                args += ["--no-data-paths"]
        if values["key_context_files"] != was["key_context_files"]:
            for declared in values["key_context_files"]:
                args += ["--context-file", declared]
            if not values["key_context_files"]:
                args += ["--no-context-files"]
        if self.notebook.changed_from(was["notebook_access"]):
            args += self.notebook.args()
        if values["env"] != was["env"]:
            for name, value in values["env"].items():
                args += ["--env", f"{name}={value}"]
            if not values["env"]:
                args += ["--no-env"]
        if extra != was["extra"]:
            args += ["--extra-file", str(extra_file)]
        return args


class ImportAgentDialog(QDialog):
    """An agent file's mandate and guardrails, and what came of fetching its
    skills, read before the agent is adopted. Accept is the grant; nothing of
    the agent is written until it is pressed —
    ``src/skills/importing-an-agent/SKILL.md``."""

    def __init__(self, parent, slug: str, report: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Agent")
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["dialog_min_w"])
        self.setMinimumHeight(LAYOUT["agent_dialog_min_h"] // 2)

        heading = QLabel(f"Import {agent_caption(slug)}?")
        heading.setObjectName("dialogHeading")

        self.report = QPlainTextEdit(report)
        self.report.setReadOnly(True)

        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        cancel.setDefault(True)
        cancel.clicked.connect(self.reject)
        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setObjectName("globalCreateBtn")
        self.accept_btn.setAutoDefault(False)
        self.accept_btn.clicked.connect(self.accept)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(self.accept_btn)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("lg"))
        column.addWidget(heading)
        column.addWidget(self.report, 1)
        column.addLayout(row)


class AgentsTab(QWidget):
    def __init__(self, parent=None, on_agents_changed=None) -> None:
        super().__init__(parent)
        # Called when this page writes, so anything reading the agent list can
        # catch up. Absent in a bare construction (the smoke check).
        self._on_agents_changed = on_agents_changed
        self._agents: list[dict] = []
        self._skills: list[str] = []

        self.new_btn = QPushButton("New Agent")
        self.new_btn.setObjectName("globalCreateBtn")
        self.new_btn.clicked.connect(self._create)
        self.import_btn = QPushButton("Import Agent")
        self.import_btn.clicked.connect(self._import)

        # Each agent is a card, and a card opens on a click.
        self.list = card_list()
        self.list.itemClicked.connect(lambda *_: self._open())
        self.list.itemActivated.connect(lambda *_: self._open())

        top = QHBoxLayout()
        top.setSpacing(space("md"))
        top.addStretch(1)
        top.addWidget(self.import_btn)
        top.addWidget(self.new_btn)


        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("lg"))
        layout.addLayout(top)
        layout.addWidget(self.list, 1)

        self.reload()

    # ----- the readers ------------------------------------------------------

    def _cli(self, script: Path):
        root = config_file.project_root()
        if root is None:
            return None
        found = root / script
        return found if found.is_file() else None

    def _run(self, script: Path, *args: str):
        """One tool command. Returns (code, stdout, stderr).

        A missing tool is reported in the same shape as a failing one, so every
        caller has one thing to check.
        """
        found = self._cli(script)
        if found is None:
            return 1, "", f"This build cannot find {script.as_posix()}."
        done = subprocess.run(
            [sys.executable, str(found), *args],
            capture_output=True, text=True, cwd=str(found.parents[3]))
        return done.returncode, done.stdout, done.stderr

    def reload(self) -> None:
        code, out, err = self._run(AGENTS_CLI, "list", "--json")
        if code != 0:
            self._agents = []
            self.list.clear()
            # The failure stands where the agents would, as the list's one row.
            self.list.addItem(err.strip() or "The agent reader failed.")
            self.list.setEnabled(False)
            return
        self.list.setEnabled(True)
        try:
            self._agents = json.loads(out)
        except json.JSONDecodeError:
            self._agents = []
        code, out, _ = self._run(SKILLS_CLI, "list", "--json")
        try:
            self._skills = ([s["name"] for s in json.loads(out).get("skills", [])]
                            if code == 0 else [])
        except (json.JSONDecodeError, TypeError, KeyError):
            self._skills = []
        self._fill_list()

    def _fill_list(self) -> None:
        self.list.clear()
        active = config_file.get("active_agent", "")
        for agent in self._agents:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, agent["slug"])
            item.setData(CARD_ROLE, {
                "title": agent_caption(agent["slug"]),
                "description": agent["description"],
                "meta": "",
                "pills": ["Active"] if agent["slug"] == active else [],
            })
            self.list.addItem(item)

    def _selected(self):
        item = self.list.currentItem()
        if item is None:
            return None
        slug = item.data(Qt.UserRole)
        return next((a for a in self._agents if a["slug"] == slug), None)

    # ----- the two ways in --------------------------------------------------

    def _create(self) -> None:
        self._show(None)

    def _import(self) -> None:
        """Adopt an agent from its file: read it, show what it asks for, and
        write it only on Accept."""
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Import Agent", str(Path.home()),
            "Agent files (*.agent.json);;All files (*)")
        if not chosen:
            return
        try:
            slug = json.loads(Path(chosen).read_text(encoding="utf-8"))["slug"]
        except (OSError, ValueError, KeyError, TypeError):
            notify(self, "Not Imported", f"{chosen} is not an agent file.")
            return
        self.import_btn.setEnabled(False)
        self.import_btn.setText("Reading…")
        # Repainted before the skills are fetched, so the page shows it is
        # working rather than freezing.
        self.import_btn.repaint()
        try:
            code, out, err = self._run(IMPORT_CLI, chosen)
        finally:
            self.import_btn.setText("Import Agent")
            self.import_btn.setEnabled(True)
        if code != 0:
            notify(self, "Not Imported", err.strip() or out.strip()
                   or "The agent file could not be read.")
            return
        # The skills it fetched are installed whatever is decided next, so the
        # Skills tab shows them either way.
        # The command-line run closes on what to type next; here the next step
        # is the Accept button, so the report stops before it.
        report = out.split("\nEach fetched skill is loadable now")[0]
        dialog = ImportAgentDialog(self, slug, report.strip())
        accepted = dialog.exec() == QDialog.Accepted
        if accepted:
            code, out, err = self._run(IMPORT_CLI, chosen, "--accept")
            if code != 0:
                notify(self, "Not Imported", err.strip() or out.strip())
                accepted = False
        self.reload()
        if not accepted:
            return
        if self._on_agents_changed is not None:
            self._on_agents_changed()
        # The new agent opens as a form, where any value the file left for this
        # installation to supply reads <supply> and is filled in place.
        record = next((a for a in self._agents if a["slug"] == slug), None)
        if record is not None:
            self._show(record)

    def _open(self) -> None:
        record = self._selected()
        if record is not None:
            self._show(record)

    def _show(self, record) -> None:
        dialog = AgentDialog(self, record, self._run,
                             {a["slug"] for a in self._agents}, self._skills)
        dialog.exec()
        self.list.clearSelection()
        if dialog.status:
            self.reload()
            if self._on_agents_changed is not None:
                self._on_agents_changed()
