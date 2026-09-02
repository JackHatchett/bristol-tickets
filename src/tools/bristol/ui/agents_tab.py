"""ui/agents_tab.py — the Agents tab: the fleet, and one agent as a form.

Every fact on this page comes from ``src/tools/agent_tools/agents.py list
--json`` and ``skill_tools/skills.py list --json``, the same readers a session
uses, so the app and a session cannot disagree. Writing goes through
``create_agent.py``, ``agents.py edit`` and ``skills.py attach``/``detach`` —
the tools that own each part — so an agent made here and one made at the command
line are the same object.

The form holds every property an agent has and nothing else, and all of it is
editable but the name of an agent that already exists, which is what its charter
file and its config key are named after.

Each kind of property gets the control its kind deserves. A path is picked, not
typed, and the picked path is turned back into the spelling config stores by
``config_tools/data_paths.py --declare``, which owns that rule in both
directions. A notebook zone is a tick box per zone. An environment variable is a
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

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local; see module docstring

from .growing_edit import GrowingTextEdit
from .theme import LAYOUT, space

AGENTS_CLI = Path("src") / "tools" / "agent_tools" / "agents.py"
CREATE_CLI = Path("src") / "tools" / "agent_tools" / "create_agent.py"
SKILLS_CLI = Path("src") / "tools" / "skill_tools" / "skills.py"
PATHS_CLI = Path("src") / "tools" / "config_tools" / "data_paths.py"

# What an agent cannot be without. The form marks each one and refuses a save
# while one is empty.
REQUIRED = ["slug", "description", "charter"]
FIELD_NAMES = {"slug": "Name", "description": "Description",
               "charter": "Charter"}

# The notebook zones, as `config`'s markdown_notebook §ZONES defines them: the
# notebook is read whole or not at all, and writing is granted one zone at a
# time. Archive is a write too — a file may be moved into it — and is stored on
# its own key because moving in is the only write it takes.
WRITE_ZONES = [("workspace", "AI Workspace"), ("inbox", "Inbox")]
ARCHIVE_LABEL = "Archive (move files in)"
READ_LABEL = "Full Notebook"


def _required(label: str) -> str:
    return f"{label} *"


class PathList(QWidget):
    """A list of declared paths, added with a picker and removed with a button.

    A path is machine-specific when it is picked and portable when it is
    stored, and `data_paths.py --declare` is what turns one into the other.
    """

    def __init__(self, run, kind: str, add_label: str, parent=None) -> None:
        super().__init__(parent)
        self._run = run
        self._kind = kind

        self.list = QListWidget()
        self.list.setObjectName("searchResults")
        self.list.setMinimumHeight(LAYOUT["path_list_min_h"])
        self.list.currentItemChanged.connect(lambda *_: self._sync())

        self.add_btn = QPushButton(add_label)
        self.add_btn.setAutoDefault(False)
        self.add_btn.clicked.connect(self._add)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setAutoDefault(False)
        self.remove_btn.clicked.connect(self._remove)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addWidget(self.add_btn)
        row.addWidget(self.remove_btn)
        row.addStretch(1)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))
        column.addWidget(self.list)
        column.addLayout(row)
        self._sync()

    def set_values(self, declared: list[str]) -> None:
        self.list.clear()
        self.list.addItems(declared)
        self._sync()

    def values(self) -> list[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]

    def _sync(self) -> None:
        self.remove_btn.setEnabled(self.list.currentItem() is not None)

    def _start_in(self) -> str:
        root = config_file.project_root()
        return str(root) if root else ""

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
        if declared not in self.values():
            self.list.addItem(declared)
        self._sync()

    def _remove(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
        self._sync()


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
            self._drop(self._rows[0][0])
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
        drop.clicked.connect(lambda: self._drop(holder))
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

    def _drop(self, holder: QWidget) -> None:
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

        self.data_paths = PathList(run, "dir", "Add Folder…")
        self.data_paths.set_values(record["key_data_paths"] if record else [])
        self.context_files = PathList(run, "file", "Add File…")
        self.context_files.set_values(
            record["key_context_files"] if record else [])

        notebook = record["notebook_access"] if record else {}
        self.notebook_read = QCheckBox(READ_LABEL)
        self.notebook_read.setChecked(bool(notebook.get("read")))
        self.zone_boxes: dict[str, QCheckBox] = {}
        held_zones = list(notebook.get("write_zones") or [])
        known = [z for z, _ in WRITE_ZONES]
        for zone, label in WRITE_ZONES + [(z, z) for z in held_zones
                                          if z not in known]:
            box = QCheckBox(label)
            box.setChecked(zone in held_zones)
            self.zone_boxes[zone] = box
        self.archive_moves = QCheckBox("Archive")
        self.archive_moves.setChecked(bool(notebook.get("archive_moves")))

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
        form.addRow("Data Folders", self.data_paths)
        form.addRow("Context Files", self.context_files)
        form.addRow("Notebook", self._zone_group())
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

        heading = QLabel(slug)
        heading.setObjectName("dialogHeading")

        self.problem = QLabel()
        self.problem.setObjectName("formCaption")
        self.problem.setWordWrap(True)

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
        column.addWidget(self.problem)
        column.addLayout(row)

        if self.creating:
            self._start_from_skeleton()

    def _zone_group(self) -> QWidget:
        """Read and Write, each with the zones it grants.

        The notebook is read whole or not at all — `config`'s markdown_notebook
        §ZONES — so Read holds one zone, and Write holds the ones granted a zone
        at a time.
        """
        holder = QWidget()
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))
        # The row's label sits on the first line of its field, so the first
        # line is left empty and Read begins under Notebook rather than beside
        # it.
        column.addSpacing(QFontMetrics(self.font()).lineSpacing())
        for title, boxes in (("Read", [self.notebook_read]),
                             ("Write", list(self.zone_boxes.values())
                              + [self.archive_moves])):
            label = QLabel(title)
            label.setObjectName("sectionHeader")
            column.addWidget(label)
            for box in boxes:
                indent = QHBoxLayout()
                indent.setContentsMargins(space("lg"), 0, 0, 0)
                indent.addWidget(box)
                column.addLayout(indent)
        return holder

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
            "notebook_access": {
                "read": self.notebook_read.isChecked(),
                "write_zones": [z for z, box in self.zone_boxes.items()
                                if box.isChecked()],
                "archive_moves": self.archive_moves.isChecked(),
            },
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
        self.problem.setText(message)

    def _save(self) -> None:
        values = self.values()
        empty = self.missing()
        if empty:
            named = ", ".join(FIELD_NAMES[name] for name in empty)
            self._refuse(f"Nothing was saved. Fill in {named}.")
            return
        try:
            extra = self.extra.values()
        except ValueError as exc:
            self._refuse(f"Nothing was saved. {exc}")
            return
        if self.creating and values["slug"] in self._taken:
            self._refuse(f"Nothing was saved. '{values['slug']}' is already an "
                         f"agent; open it to change what it says.")
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
                "--notebook-read", "yes" if notebook["read"] else "no",
                "--archive-moves",
                "yes" if notebook["archive_moves"] else "no"]
        for zone in notebook["write_zones"]:
            args += ["--write-zone", zone]
        for declared in values["key_data_paths"]:
            args += ["--data-path", declared]
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
            for declared in values["key_data_paths"]:
                args += ["--data-path", declared]
            if not values["key_data_paths"]:
                args += ["--no-data-paths"]
        if values["key_context_files"] != was["key_context_files"]:
            for declared in values["key_context_files"]:
                args += ["--context-file", declared]
            if not values["key_context_files"]:
                args += ["--no-context-files"]
        notebook, before = values["notebook_access"], was["notebook_access"]
        if notebook["read"] != bool(before.get("read")):
            args += ["--notebook-read", "yes" if notebook["read"] else "no"]
        if notebook["write_zones"] != list(before.get("write_zones") or []):
            for zone in notebook["write_zones"]:
                args += ["--write-zone", zone]
            if not notebook["write_zones"]:
                args += ["--no-write-zones"]
        if notebook["archive_moves"] != bool(before.get("archive_moves")):
            args += ["--archive-moves",
                     "yes" if notebook["archive_moves"] else "no"]
        if values["env"] != was["env"]:
            for name, value in values["env"].items():
                args += ["--env", f"{name}={value}"]
            if not values["env"]:
                args += ["--no-env"]
        if extra != was["extra"]:
            args += ["--extra-file", str(extra_file)]
        return args


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

        self.status = QLabel()
        self.status.setObjectName("formCaption")
        self.status.setWordWrap(True)

        self.list = QListWidget()
        self.list.setObjectName("searchResults")
        self.list.itemActivated.connect(lambda *_: self._open())
        self.list.currentItemChanged.connect(lambda *_: self._sync_actions())

        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self._open)

        top = QHBoxLayout()
        top.setSpacing(space("md"))
        top.addStretch(1)
        top.addWidget(self.new_btn)

        actions = QHBoxLayout()
        actions.setSpacing(space("md"))
        actions.addStretch(1)
        actions.addWidget(self.open_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("lg"))
        layout.addLayout(top)
        layout.addWidget(self.status)
        layout.addWidget(self.list, 1)
        layout.addLayout(actions)

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
            self.setEnabled(False)
            self.status.setText(err.strip() or "The agent reader failed.")
            return
        self.setEnabled(True)
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
        self._sync_actions()

    def _fill_list(self) -> None:
        self.list.clear()
        active = config_file.get("active_agent", "")
        for agent in self._agents:
            name = agent["slug"] + ("   ·   active" if agent["slug"] == active
                                    else "")
            item = QListWidgetItem(f"{name}\n{agent['description']}")
            item.setData(Qt.UserRole, agent["slug"])
            self.list.addItem(item)

    def _sync_actions(self) -> None:
        self.open_btn.setEnabled(self.list.currentItem() is not None)

    def _selected(self):
        item = self.list.currentItem()
        if item is None:
            return None
        slug = item.data(Qt.UserRole)
        return next((a for a in self._agents if a["slug"] == slug), None)

    # ----- the two ways in --------------------------------------------------

    def _create(self) -> None:
        self._show(None)

    def _open(self) -> None:
        record = self._selected()
        if record is not None:
            self._show(record)

    def _show(self, record) -> None:
        dialog = AgentDialog(self, record, self._run,
                             {a["slug"] for a in self._agents}, self._skills)
        dialog.exec()
        if dialog.status:
            self.status.setText(dialog.status)
            self.reload()
            if self._on_agents_changed is not None:
                self._on_agents_changed()
