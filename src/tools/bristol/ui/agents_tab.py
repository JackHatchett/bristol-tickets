"""ui/agents_tab.py — the Agents tab: the fleet, and one agent as a form.

Every fact on this page comes from ``src/tools/agent_tools/agents.py list
--json`` and ``skill_tools/skills.py list --json``, the same readers a session
uses, so the app and a session cannot disagree. Writing goes through
``create_agent.py``, ``import_agent.py``, ``agents.py edit`` and
``skills.py attach``/``detach`` —
the tools that own each part — so an agent made here and one made at the command
line are the same object.

The form contains every property an agent has and nothing else, and all of it is
editable but the name of an agent that already exists, which is what its charter
file and its config key are named after.

Each kind of property gets the control its kind deserves. A path is picked, not
typed, and the picked path is turned back into the spelling config stores by
``config_tools/data_paths.py --declare``, which owns that rule in both
directions. A folder carries the access it is granted beside it, so adding a
folder and deciding what may be done in it are one gesture. A notebook zone is a tick box per zone. An environment variable is a
name beside a value. A key this build has no control for keeps its own field,
named after the key and containing the JSON it contains, so nothing is lost and
nothing is guessed at.

The charter is one Markdown editor containing the whole document. It is not
parsed: a charter is prose somebody wrote, and shredding it into fields would
mean only the ones this app generated could be edited.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import config_file  # bristol-local; see module docstring
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
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
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .dialogs import (
    ORDINARY,
    PRIMARY,
    Modal,
    RowList,
    add_button,
    as_sheet,
    confirm,
    notify,
    removable_item,
)
from .growing_edit import GrowingTextEdit
from .row_card import card_list
from .segmented import SegmentedControl
from .settled_combo import SettledComboBox, fill_words
from .theme import CARD_ROLE, LAYOUT, agent_caption, control_height, space
from .toggle_list import ToggleList

AGENTS_CLI = Path("src") / "tools" / "agent_tools" / "agents.py"
CREATE_CLI = Path("src") / "tools" / "agent_tools" / "create_agent.py"
IMPORT_CLI = Path("src") / "tools" / "agent_tools" / "import_agent.py"
SKILLS_CLI = Path("src") / "tools" / "skill_tools" / "skills.py"
PATHS_CLI = Path("src") / "tools" / "config_tools" / "data_paths.py"
NOTEBOOK_CLI = Path("src") / "tools" / "config_tools" / "notebook.py"
DASHBOARDS_CLI = Path("src") / "tools" / "config_tools" / "dashboards.py"
# The one agent that writes to every dashboard whatever its toggle says —
# src/tools/config_tools/dashboards.py.
ALWAYS_ALL_DASHBOARDS = "chief_of_staff"

# What an agent cannot be without. The form marks each one and refuses a save
# while one is empty.
REQUIRED = ["slug", "description", "charter"]
FIELD_NAMES = {"slug": "Name", "description": "Description", "charter": "Charter"}

# What an agent may do in the notebook — src/tools/config_tools/notebook.py.
NOTEBOOK_MODES = [
    ("per_folder", "Per Folder"),
    ("read_all", "Read All"),
    ("write_all", "Write All"),
]
FOLDER_ACCESS = [("read", "Read"), ("write", "Write"), ("hide", "Hide")]
DASHBOARD_MODES = [("all", "All Dashboards"), ("chosen", "Chosen Dashboards")]


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
        mode = entry.get("mode") if entry.get("mode") in dict(NOTEBOOK_MODES) else "per_folder"
        self._kept = dict(entry.get("folders") or {}) if "mode" in entry else {}
        self._legacy = "mode" not in entry and bool(entry)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))

        self.mode_control = SegmentedControl(NOTEBOOK_MODES, mode)
        column.addWidget(self.mode_control, 0, Qt.AlignmentFlag.AlignLeft)

        self.rows = QWidget()
        grid = QGridLayout(self.rows)
        grid.setContentsMargins(0, space("sm"), 0, 0)
        grid.setHorizontalSpacing(space("lg"))
        grid.setVerticalSpacing(space("sm"))
        self.choices: dict[str, SegmentedControl] = {}
        for row, folder in enumerate(folders):
            name = QLabel(folder)
            name.setObjectName("metaText")
            grid.addWidget(name, row, 0)
            control = SegmentedControl(FOLDER_ACCESS, self._kept.get(folder, "hide"))
            control.setAccessibleName(f"{folder}: Read, Write or Hide")
            grid.addWidget(control, row, 1)
            self.choices[folder] = control
        grid.setColumnStretch(2, 1)
        column.addWidget(self.rows)
        self.mode_control.changed.connect(lambda _value: self._sync())
        self._sync()

    def _sync(self) -> None:
        self.rows.setVisible(self.mode() == "per_folder" and bool(self.choices))

    def mode(self) -> str:
        return self.mode_control.value() or "per_folder"

    def values(self) -> dict:
        chosen = dict(self._kept)
        for folder, control in self.choices.items():
            chosen[folder] = control.value()
        return {"mode": self.mode(), "folders": chosen}

    def changed_from(self, entry: dict) -> bool:
        """Whether saving would change what the entry says."""
        if self._legacy:
            return True
        entry = entry if isinstance(entry, dict) else {}
        before = {
            "mode": entry.get("mode", "per_folder"),
            "folders": dict(entry.get("folders") or {}),
        }
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


class DashboardAccess(QWidget):
    """All Dashboards or Chosen Dashboards, as the Notebook row offers its modes,
    and under Chosen a checkable list of the dashboards known in Settings, as
    the Skills list is, each off until ticked. There is no read-only level: a
    dashboard is published, and anyone may read it.

    Choices are kept while All is chosen, so going back to Chosen brings them
    back. chief_of_staff writes to every dashboard, so its All is shown chosen
    and cannot be moved.
    """

    def __init__(self, entry: dict, dashboards: list[str], slug: str = "") -> None:
        super().__init__()
        entry = entry if isinstance(entry, dict) else {}
        self._kept = [n for n in entry.get("dashboards") or [] if isinstance(n, str)]
        locked = slug == ALWAYS_ALL_DASHBOARDS
        write_all = locked or entry.get("write_all") is not False

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))

        self.mode_control = SegmentedControl(DASHBOARD_MODES, "all" if write_all else "chosen")
        self.mode_control.setEnabled(not locked)
        if locked:
            self.mode_control.setToolTip(
                "chief_of_staff keeps every dashboard, whatever this says."
            )
        column.addWidget(self.mode_control, 0, Qt.AlignmentFlag.AlignLeft)

        self.list = ToggleList()
        for name in dashboards:
            self.list.add(name, name in self._kept)
        if not dashboards:
            self.list.add_note("No dashboard is known yet. Add one in Settings.")
        rows = max(1, self.list.count())
        self.list.setFixedHeight(
            min(rows, 6) * self.list.sizeHintForRow(0)
            + 2 * self.list.frameWidth()
            + 2 * space("sm")
        )
        self._names = list(dashboards)
        column.addWidget(self.list)
        self.mode_control.changed.connect(lambda _value: self._sync())
        self._sync()

    def _sync(self) -> None:
        self.list.setVisible(self.mode_control.value() == "chosen")

    def _ticked(self) -> list[str]:
        return [n for n in self.list.chosen() if n in self._names]

    def values(self) -> dict:
        chosen = [n for n in self._kept if n not in self._names] + self._ticked()
        return {"write_all": self.mode_control.value() == "all", "dashboards": chosen}

    def changed_from(self, entry: dict) -> bool:
        """Whether saving would change what the entry says."""
        entry = entry if isinstance(entry, dict) else {}
        before = {
            "write_all": entry.get("write_all") is not False,
            "dashboards": [n for n in entry.get("dashboards") or []],
        }
        now = self.values()
        return now["write_all"] != before["write_all"] or sorted(now["dashboards"]) != sorted(
            before["dashboards"]
        )

    def args(self) -> list[str]:
        values = self.values()
        out = ["--dashboards-all" if values["write_all"] else "--dashboards-chosen"]
        known = [n for n in values["dashboards"] if n in self._names]
        for name in known:
            out += ["--dashboard", name]
        if not known:
            out += ["--no-dashboards"]
        return out


def _required(label: str) -> str:
    return f"{label} *"


def align_form_labels(form: QFormLayout) -> None:
    """Sit every label of ``form`` on the first line of its field: each label is
    one control tall and centred in that height, at the top of its row, so it
    reads level with a field, a picker, a row of radios or a list's first row
    alike."""
    for row in range(form.rowCount()):
        item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
        label = item.widget() if item is not None else None
        if isinstance(label, QLabel):
            label.setFixedHeight(control_height())
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


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
    return {"path": declared, "access": access if access in known else known[0]}


class PathList(QWidget):
    """The folders or files an agent reaches: one row each, added with a picker.

    A path is machine-specific when it is picked and portable when it is
    stored, and `data_paths.py --declare` is what turns one into the other.

    A folder row carries the access it is granted beside it, because a grant is
    a folder and what may be done in it rather than a folder alone. A file row
    carries none: a context file is read.

    A repository row, kind ``repo``, is a folder or a file inside the cloned
    project, stored relative to its root: a path whose git-tracked files the
    agent may change.
    """

    def __init__(
        self, run, kind: str, add_label: str, parent=None, *, access: bool = False
    ) -> None:
        super().__init__(parent)
        self._run = run
        self._kind = kind
        self._access = access
        self._rows: list[tuple[QListWidgetItem, str, QComboBox | None]] = []

        self.list = QListWidget()
        # Its own name rather than the search list's: that one pads every
        # item for text a delegate draws, and a row here is a widget, which
        # such padding shrinks out of the item containing it.
        self.list.setObjectName("pathRows")
        self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list.setMinimumHeight(LAYOUT["path_list_min_h"])

        self.add_btn = add_button(add_label.rstrip("…"), self._add)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))
        column.addWidget(self.list)
        column.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignLeft)

    def set_values(self, entries: list) -> None:
        self.list.clear()
        self._rows = []
        for entry in entries:
            grant = folder_grant(entry)
            self._row(grant["path"], grant["access"])

    def values(self) -> list:
        out = []
        for _, declared, combo in self._rows:
            if self._access and combo is not None:
                out.append({"path": declared, "access": combo.currentData()})
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
            combo.setCurrentIndex(max(0, combo.findData(access)))
        line = QHBoxLayout(holder)
        line.setContentsMargins(0, space("xs"), 0, space("xs"))
        line.setSpacing(space("sm"))
        line.addWidget(label, 1)
        if combo is not None:
            line.addWidget(combo)

        # A row is as tall as its own contents once the stylesheet is on them,
        # and never shorter than one line of them: an unpolished widget reports
        # a height its padding has not reached yet, and a list item takes the
        # height it is given rather than growing to what it contains.
        holder.ensurePolished()
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, LAYOUT["path_row_min_h"]))
        self.list.addItem(item)
        subject = {"dir": "folder", "repo": "path"}.get(self._kind, "file")
        removable_item(
            self.list, item, f"Remove this {subject}", lambda i=item: self._drop(i), content=holder
        )
        self._rows.append((item, declared, combo))

    def _drop(self, item: QListWidgetItem) -> None:
        declared = next((d for i, d, _ in self._rows if i is item), "")
        subject = {"dir": "folder", "repo": "path"}.get(self._kind, "file")
        if not confirm(
            self,
            f"Remove this {subject}?",
            f"{declared} goes off this agent's list. Nothing on disk is touched.",
            "Remove",
            destructive=True,
        ):
            return
        self._rows = [r for r in self._rows if r[0] is not item]
        self.list.takeItem(self.list.row(item))

    def _start_in(self) -> str:
        root = config_file.project_root()
        return str(root) if root else ""

    def _declared(self) -> list[str]:
        return [declared for _, declared, _ in self._rows]

    def _add_repo_path(self) -> None:
        """A folder or a file inside the project, kept relative to its root."""
        root = config_file.project_root()
        if root is None:
            return
        question = Modal(
            self,
            "Add a Path",
            "Grant a folder, which covers everything under it, or a single file.",
            [("Cancel", ORDINARY, None), ("Folder", ORDINARY, "dir"), ("File", PRIMARY, "file")],
            default_index=2,
            escape_index=0,
        )
        question.exec()
        kind = question.choice()
        if kind == "dir":
            picked = QFileDialog.getExistingDirectory(self, "Choose a folder", str(root))
        elif kind == "file":
            picked, _ = QFileDialog.getOpenFileName(self, "Choose a file", str(root))
        else:
            return
        if not picked:
            return
        try:
            declared = Path(picked).resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            notify(self, "Not Added", f"{picked} is outside the project folder, {root}.")
            return
        if declared not in self._declared():
            self._row(declared, ACCESS_CHOICES[0][0])

    def _add(self) -> None:
        if self._kind == "repo":
            self._add_repo_path()
            return
        if self._kind == "dir":
            picked = QFileDialog.getExistingDirectory(self, "Choose a folder", self._start_in())
        else:
            picked, _ = QFileDialog.getOpenFileName(self, "Choose a file", self._start_in())
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

        self.rows = RowList()

        self.add_btn = add_button("Add Variable", lambda: self._add("", ""))

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("sm"))
        column.addWidget(self.rows)
        column.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignLeft)

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
        name_edit.setCursorPosition(0)
        name_edit.textChanged.connect(lambda _text: self._fit_names())
        value_edit = QLineEdit(value)
        value_edit.setPlaceholderText("Value")
        choose = QPushButton()
        choose.setObjectName("quietIcon")
        icons.tint(choose, "folder")
        choose.setToolTip("Choose a folder for this variable")
        choose.setAccessibleName("Choose a folder for this variable")
        choose.setAutoDefault(False)
        choose.setFixedSize(LAYOUT["env_choose_w"], control_height())
        choose.clicked.connect(lambda: self._pick_into(value_edit))
        line = QHBoxLayout(holder)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(space("sm"))
        line.addWidget(name_edit)
        line.addWidget(value_edit, 1)
        line.addWidget(choose)
        cell: list[QWidget] = []
        row = self.rows.add_row(holder, "Remove this variable", lambda: self._drop(cell[0]))
        cell.append(row)
        holder = row
        self._rows.append((holder, name_edit, value_edit))
        self._fit_names()

    def _fit_names(self) -> None:
        """Give every name box one width, wide enough for the longest name, so
        each name shows whole and the value boxes start in one column."""
        if not self._rows:
            return
        sample = self._rows[0][1]
        metrics = sample.fontMetrics()
        longest = max(
            metrics.horizontalAdvance(name.text() or name.placeholderText())
            for _holder, name, _value in self._rows
        )
        margins = sample.textMargins()
        width = max(
            LAYOUT["env_name_w"], longest + margins.left() + margins.right() + 4 * space("md")
        )
        for _holder, name, _value in self._rows:
            name.setFixedWidth(width)

    def _pick_into(self, field: QLineEdit) -> None:
        """A value that names a folder is picked; one that does not is typed."""
        root = config_file.project_root()
        picked = QFileDialog.getExistingDirectory(
            self, "Choose a folder", field.text() or (str(root) if root else "")
        )
        if picked:
            field.setText(picked)

    def _drop(self, holder: QWidget, ask: bool = True) -> None:
        named = next((n.text().strip() for h, n, _ in self._rows if h is holder), "")
        if (
            ask
            and named
            and not confirm(
                self,
                "Remove this variable?",
                f"{named} goes off this agent's list. The tools that read it "
                f"run without it afterwards.",
                "Remove",
                destructive=True,
            )
        ):
            return
        self._rows = [r for r in self._rows if r[0] is not holder]
        self.rows.remove_row(holder)


class KeyFields(QWidget):
    """One field per config key this build has no control of its own for.

    Each is labelled with the key it contains and contains that key's value as the
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
        self.form.setSpacing(space("lg"))
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

    def set_values(self, extra: dict) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._fields = {}
        for key, value in extra.items():
            field = QPlainTextEdit(json.dumps(value, indent=2))
            field.setMinimumHeight(LAYOUT["extra_min_h"])
            self._fields[key] = field
            self.form.addRow(key, field)
        align_form_labels(self.form)
        self.setVisible(bool(extra))

    def values(self) -> dict:
        """What the fields contain. Raises ValueError naming the key that is not
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

        self.setWindowTitle(agent_caption(record["slug"]) if record else "New Agent")
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["agent_dialog_min_w"])
        self.setMinimumHeight(LAYOUT["agent_dialog_min_h"])
        self._open_at_a_readable_size()

        self.slug = QLineEdit(record["slug"] if record else "")
        self.slug.setEnabled(self.creating)
        self.description = GrowingTextEdit(min_lines=2, max_lines=4, newline_on_return=True)
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
        self.charter.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.data_paths = PathList(run, "dir", "Add Folder…", access=True)
        self.data_paths.set_values(record["key_data_paths"] if record else [])
        self.context_files = PathList(run, "file", "Add File…")
        self.context_files.set_values(record["key_context_files"] if record else [])
        self.repo_write = PathList(run, "repo", "Add Path…")
        self.repo_write.setToolTip(
            "The folders and files of this project the agent may change, beside chief_of_staff."
        )
        self.repo_write.set_values(record.get("repo_write", []) if record else [])

        self.notebook = NotebookAccess(
            record["notebook_access"] if record else {}, self._attached(run)
        )

        self.dashboards = DashboardAccess(
            record.get("dashboard_access", {}) if record else {},
            self._known_dashboards(run),
            record["slug"] if record else "",
        )

        self.env = EnvList(run)
        self.env.set_values(record["env"] if record else {})

        self.skills = ToggleList()
        self.skills.setMinimumHeight(LAYOUT["skill_list_min_h"])
        held = set(record["skills"]) if record else set()
        for name in list(every_skill) + sorted(held - set(every_skill)):
            self.skills.add(name, name in held)

        self.extra = KeyFields()
        self.extra.set_values(record["extra"] if record else {})

        form = QFormLayout()
        form.setSpacing(space("lg"))
        form.setHorizontalSpacing(space("lg"))
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow(_required("Name"), self.slug)
        form.addRow(_required("Description"), self.description)
        form.addRow("Charter File", identity_row)
        form.addRow("Folders", self.data_paths)
        form.addRow("Context Files", self.context_files)
        form.addRow("Repository Write", self.repo_write)
        form.addRow("Notebook", self.notebook)
        form.addRow("Dashboards", self.dashboards)
        form.addRow("Environment Variables", self.env)
        form.addRow("Skills", self.skills)
        if record and record["extra"]:
            form.addRow("Other Keys", self.extra)
        align_form_labels(form)

        page = QWidget()
        page.setLayout(form)
        self.fields_scroll = QScrollArea()
        self.fields_scroll.setWidgetResizable(True)
        self.fields_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.fields_scroll.setWidget(page)
        self.fields_scroll.setMinimumWidth(LAYOUT["agent_fields_min_w"])

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

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(space("lg"))
        split.addWidget(self.fields_scroll)
        split.addWidget(charter_pane)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 4)

        heading = QLabel(self.windowTitle())
        heading.setObjectName("dialogHeading")
        heading.setVisible(as_sheet(self))

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
        column.setContentsMargins(space("xl"), space("xl"), space("xl"), space("xl"))
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
            return [f["folder"] for f in json.loads(out)["folders"]] if code == 0 else []
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    @staticmethod
    def _known_dashboards(run) -> list[str]:
        """The dashboards known in Settings, read fresh."""
        code, out, _ = run(DASHBOARDS_CLI, "show", "--json")
        try:
            return [d["name"] for d in json.loads(out)] if code == 0 else []
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def _pick_charter(self) -> None:
        root = config_file.project_root()
        start = str(root / "src" / "agent_identities") if root else ""
        picked, _ = QFileDialog.getSaveFileName(
            self, "Where the charter lives", start, "Markdown (*.md)"
        )
        if not picked:
            return
        code, out, _ = self._run(PATHS_CLI, "--declare", picked)
        self.identity.setText(out.strip() if code == 0 and out.strip() else picked)

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
            max(LAYOUT["agent_dialog_min_w"], min(int(room.width() * 0.78), room.width() - 80)),
            max(LAYOUT["agent_dialog_min_h"], min(int(room.height() * 0.88), room.height() - 80)),
        )

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

    # ----- what the form contains, and what it refuses -------------------------

    def values(self) -> dict:
        checked = []
        for i in range(self.skills.count()):
            item = self.skills.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(item.text())
        return {
            "slug": self.slug.text().strip(),
            "description": self.description.text().strip(),
            "identity": self.identity.text().strip(),
            "charter": self.charter.toPlainText(),
            "key_data_paths": self.data_paths.values(),
            "key_context_files": self.context_files.values(),
            "repo_write": self.repo_write.values(),
            "notebook_access": self.notebook.values(),
            "dashboard_access": self.dashboards.values(),
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
                code, out, err = self._run(CREATE_CLI, *self._create_args(values, charter_file))
                if code == 0 and self.dashboards.changed_from({}):
                    code, more, err = self._run(
                        AGENTS_CLI, "edit", values["slug"], *self.dashboards.args()
                    )
                    out += more
            else:
                args = self._edit_args(values, extra, charter_file, extra_file)
                code, out, err = (
                    (0, "", "") if len(args) == 1 else self._run(AGENTS_CLI, "edit", *args)
                )
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
        args = [
            values["slug"],
            "--description",
            values["description"],
            "--charter-file",
            str(charter_file),
            "--notebook-mode",
            notebook["mode"],
        ]
        for folder, access in notebook["folders"].items():
            args += ["--notebook-folder", f"{folder}={access}"]
        for grant in values["key_data_paths"]:
            args += [_grant_option(grant), grant["path"]]
        for declared in values["key_context_files"]:
            args += ["--context-file", declared]
        for declared in values["repo_write"]:
            args += ["--repo-write", declared]
        for name, value in values["env"].items():
            args += ["--env", f"{name}={value}"]
        return args

    def _edit_args(
        self, values: dict, extra: dict, charter_file: Path, extra_file: Path
    ) -> list[str]:
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
        if values["repo_write"] != was.get("repo_write", []):
            for declared in values["repo_write"]:
                args += ["--repo-write", declared]
            if not values["repo_write"]:
                args += ["--no-repo-write"]
        if self.notebook.changed_from(was["notebook_access"]):
            args += self.notebook.args()
        if self.dashboards.changed_from(was.get("dashboard_access", {})):
            args += self.dashboards.args()
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
        cancel.clicked.connect(self.reject)
        self.accept_btn = QPushButton("Import Agent")
        self.accept_btn.setObjectName("globalCreateBtn")
        self.accept_btn.setAutoDefault(False)
        self.accept_btn.setDefault(True)
        self.accept_btn.clicked.connect(self.accept)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(self.accept_btn)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"), space("xl"))
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
            capture_output=True,
            text=True,
            cwd=str(found.parents[3]),
        )
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
            self._skills = (
                [s["name"] for s in json.loads(out).get("skills", [])] if code == 0 else []
            )
        except (json.JSONDecodeError, TypeError, KeyError):
            self._skills = []
        self._fill_list()

    def _fill_list(self) -> None:
        self.list.clear()
        active = config_file.get("active_agent", "")
        for agent in self._agents:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, agent["slug"])
            item.setData(
                CARD_ROLE,
                {
                    "title": agent_caption(agent["slug"]),
                    "description": agent["description"],
                    "meta": "",
                    "pills": ["Active"] if agent["slug"] == active else [],
                },
            )
            self.list.addItem(item)

    def _selected(self):
        item = self.list.currentItem()
        if item is None:
            return None
        slug = item.data(Qt.ItemDataRole.UserRole)
        return next((a for a in self._agents if a["slug"] == slug), None)

    # ----- the two ways in --------------------------------------------------

    def _create(self) -> None:
        self._show(None)

    def _addons_folder(self) -> str:
        """Where the agent files Bristol ships sit, which is where a picker for
        one opens; the home folder where this build ships none."""
        root = config_file.project_root()
        addons = root / "src" / "addons" if root else None
        return str(addons if addons and addons.is_dir() else Path.home())

    def _import(self) -> None:
        """Adopt an agent from its file: read it, show what it asks for, and
        write it only on Accept."""
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Import Agent", self._addons_folder(), "Agent files (*.agent.json);;All files (*)"
        )
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
            notify(
                self,
                "Not Imported",
                err.strip() or out.strip() or "The agent file could not be read.",
            )
            return
        # The skills it fetched are installed whatever is decided next, so the
        # Skills tab shows them either way.
        # The command-line run closes on what to type next; here the next step
        # is the Accept button, so the report stops before it.
        report = out.split("\nEach fetched skill is loadable now")[0]
        dialog = ImportAgentDialog(self, slug, report.strip())
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
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
        dialog = AgentDialog(
            self, record, self._run, {a["slug"] for a in self._agents}, self._skills
        )
        dialog.exec()
        self.list.clearSelection()
        if dialog.status:
            self.reload()
            if self._on_agents_changed is not None:
                self._on_agents_changed()
