"""ui/skills_tab.py — the Skills tab: what a session can load, and how a new
skill gets here.

Every fact on this page comes from one call to
``src/tools/skill_tools/skills.py list --json``, the same loader a session
reads, so the app and a session cannot disagree about a name, a description or
an origin. Attaching and removing are that tool's own commands, run the same
way.

The page reads like the Backlog: the row that narrows the list at the top, with
New Skill at its right, and each skill as a card under it — its name in Title
Case, its subtitle, where it came from and which agents hold it. A card opens
the skill's own window, and everything that changes a skill happens there:
ticking the agents that hold it, and removing a downloaded one.

New Skill opens a window offering the two ways a skill arrives: asking
chief_of_staff for one, which files a card on the board, and importing one from
GitHub, whose example is a real skill folder, so following it shows what a skill
folder looks like and gives an address that works. The page carries no sentence of explanation
and no line reporting what the last action did: a failure is a dialog the user
dismisses, and a success is the skill's window opening.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QRadioButton,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local; see module docstring

from . import dialogs
from .links import open_uri
from .growing_edit import GrowingTextEdit
from .row_card import card_list
from .theme import CARD_ROLE, LAYOUT, agent_caption, fill_agents, space

TICKETS_CLI = Path("src") / "tools" / "ticket_tools" / "ticket_write.py"
STANDING_KIND = "standing"  # create_tickets.EPIC_KIND_STANDING

SKILLS_CLI = Path("src") / "tools" / "skill_tools" / "skills.py"

# A skill folder that exists, in the sample-skills repository career_coach's
# skills ship from.
# It is the New Skill window's example: well formed, and live, so following it
# lands on a page whose address can be pasted straight back.
EXAMPLE_SKILL = ("https://github.com/JackHatchett/bristol-career-coach/"
                 "tree/main/jd-evaluation")

# The three ways the list narrows. Each is one control on the top row, and the
# picker's own name is the option that turns it off.
ANY_SOURCE = "Source"
CAME_WITH = "Came with Bristol"
DOWNLOADED = "Downloaded"
ANY_AGENT = "Agent"
NO_AGENT = "No Agent"
NO_AGENT_DATA = "\x00none"  # item data no agent slug can be


def _title(record: dict) -> str:
    """A skill's name as a person reads it, from the loader where it says."""
    return record.get("title") or record["name"]


def _leave_for(parent, url: str) -> None:
    """Open a web address, once the user has agreed to leave the app for it."""
    if dialogs.confirm(parent, "Open in Your Browser?", url, "Open"):
        open_uri(url)


class NewSkillDialog(QDialog):
    """The two ways a skill arrives, one above the other: a request to
    chief_of_staff, and an import from GitHub. Choosing one opens its fields and
    closes the other's; the one button at the foot does what the open choice
    says.

    ``imported`` is set when an import landed and ``filed`` when a request
    became a card. A refused import keeps the window open with the reason in a
    dialog over it.
    """

    def __init__(self, parent, run, file_request) -> None:
        super().__init__(parent)
        self._run = run
        self._file_request = file_request
        self.imported = False
        self.filed = False
        self.setWindowTitle("New Skill")
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["dialog_min_w"])

        heading = QLabel("New Skill")
        heading.setObjectName("dialogHeading")

        self.request_choice = QRadioButton("Request From Chief of Staff")
        self.import_choice = QRadioButton("Import From GitHub")
        for choice in (self.request_choice, self.import_choice):
            choice.setObjectName("choiceHeading")
            choice.setCursor(Qt.PointingHandCursor)
        group = QButtonGroup(self)
        group.addButton(self.request_choice)
        group.addButton(self.import_choice)
        group.buttonToggled.connect(lambda *_: self._sync())

        # The request: a short title and the request itself.
        self.request_fields = QWidget()
        rf = QVBoxLayout(self.request_fields)
        rf.setContentsMargins(space("2xl"), 0, 0, 0)
        rf.setSpacing(space("sm"))
        self.title = QLineEdit()
        self.title.textChanged.connect(self._sync)
        self.request = GrowingTextEdit(min_lines=4, max_lines=10,
                                       newline_on_return=True)
        self.request.textChanged.connect(self._sync)
        rf.addWidget(self._caption("Title"))
        rf.addWidget(self.title)
        rf.addSpacing(space("sm"))
        rf.addWidget(self._caption("Request"))
        rf.addWidget(self.request)

        # The import: one address, and a live example under it.
        self.import_fields = QWidget()
        imf = QVBoxLayout(self.import_fields)
        imf.setContentsMargins(space("2xl"), 0, 0, 0)
        imf.setSpacing(space("sm"))
        self.address = QLineEdit()
        self.address.textChanged.connect(self._sync)
        self.address.returnPressed.connect(self._go)
        self.example = QPushButton(f"Example: {EXAMPLE_SKILL}")
        self.example.setObjectName("exampleLink")
        self.example.setCursor(Qt.PointingHandCursor)
        self.example.setToolTip(EXAMPLE_SKILL)
        self.example.clicked.connect(lambda: _leave_for(self, EXAMPLE_SKILL))
        imf.addWidget(self._caption("Skill Folder on GitHub"))
        imf.addWidget(self.address)
        imf.addWidget(self.example, 0, Qt.AlignLeft)

        rule = QFrame()
        rule.setObjectName("sectionRule")
        rule.setFixedHeight(1)

        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        self.go_btn = QPushButton("Submit")
        self.go_btn.setObjectName("globalCreateBtn")
        self.go_btn.setDefault(True)
        self.go_btn.clicked.connect(self._go)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(self.go_btn)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("md"))
        column.addWidget(heading)
        column.addSpacing(space("sm"))
        column.addWidget(self.request_choice)
        column.addWidget(self.request_fields)
        column.addSpacing(space("sm"))
        column.addWidget(rule)
        column.addSpacing(space("sm"))
        column.addWidget(self.import_choice)
        column.addWidget(self.import_fields)
        column.addSpacing(space("lg"))
        column.addLayout(row)
        self._sync()

    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("formCaption")
        return label

    def _sync(self) -> None:
        """Open the chosen section, close the other, and say on the button
        what it will do."""
        requesting = self.request_choice.isChecked()
        importing = self.import_choice.isChecked()
        self.request_fields.setVisible(requesting)
        self.import_fields.setVisible(importing)
        self.go_btn.setText("Import" if importing else "Submit")
        if requesting:
            ready = bool(self.title.text().strip()
                         and self.request.toPlainText().strip())
        elif importing:
            ready = bool(self.address.text().strip())
        else:
            ready = False
        self.go_btn.setEnabled(ready)
        self.adjustSize()

    def _go(self) -> None:
        if not self.go_btn.isEnabled():
            return
        if self.request_choice.isChecked():
            self._request()
        else:
            self._import()

    def _request(self) -> None:
        """File the request as a card for chief_of_staff."""
        problem = self._file_request(self.title.text().strip(),
                                     self.request.toPlainText().strip())
        if problem:
            dialogs.notify(self, "Not Sent", problem)
            return
        self.filed = True
        self.accept()

    def _import(self) -> None:
        address = self.address.text().strip()
        self.go_btn.setEnabled(False)
        self.go_btn.setText("Importing…")
        # Repainted before the fetch blocks, so the window shows it is working
        # rather than freezing.
        self.go_btn.repaint()
        try:
            code, _out, err = self._run("install", address)
        finally:
            self._sync()
        if code != 0:
            dialogs.notify(self, "Not Imported",
                           err.strip() or "The fetch failed.")
            return
        self.imported = True
        self.accept()


class SkillDialog(QDialog):
    """One skill, whole: what it is, where it came from, what is in it, which
    agents hold it, and its own text.

    The tick boxes are the only thing here that changes anything, and they write
    through the same loader commands the command line calls. Everything else is
    a read: a skill's files are published source, and this view never offers to
    edit them.
    """

    def __init__(self, parent, record: dict, agents: list[str], body: str,
                 run) -> None:
        super().__init__(parent)
        self._record = record
        self._run = run
        # Set when Remove deleted the skill, so the page behind reads again.
        self.removed = False

        self.setWindowTitle(_title(record))
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["dialog_min_w"])
        self.setMinimumHeight(LAYOUT["wizard_min_h"])

        heading = QLabel(_title(record))
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)

        subtitle = QLabel(record.get("subtitle", ""))
        subtitle.setWordWrap(True)

        description = QLabel(record.get("description", ""))
        description.setObjectName("metaText")
        description.setWordWrap(True)

        facts = QLabel("   ·   ".join(part for part in (
            record["name"], record["said_origin"], record["said_contents"],
            record.get("said_scan", "")) if part))
        facts.setObjectName("metaText")
        facts.setWordWrap(True)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("md"))
        column.addWidget(heading)
        column.addWidget(subtitle)
        column.addWidget(facts)
        column.addWidget(description)

        # The source, as the address it actually came from rather than a name to
        # go and look up.
        self.source_btn = None
        if record.get("source_url"):
            self.source_btn = QPushButton("Source on GitHub")
            self.source_btn.setObjectName("linkRow")
            self.source_btn.setToolTip(record["source_url"])
            self.source_btn.clicked.connect(
                lambda: _leave_for(self, record["source_url"]))
            column.addWidget(self.source_btn, 0, Qt.AlignLeft)

        column.addSpacing(space("md"))
        column.addWidget(self._section("Held By"))
        self.boxes: dict[str, QCheckBox] = {}
        held = set(record.get("holders", []))
        for slug in agents:
            box = QCheckBox(agent_caption(slug))
            box.setChecked(slug in held)
            box.toggled.connect(
                lambda on, name=slug: self._attachment(name, on))
            self.boxes[slug] = box
            column.addWidget(box)

        column.addSpacing(space("md"))
        column.addWidget(self._section("Files"))
        self.files = QListWidget()
        self.files.setObjectName("searchResults")
        self.files.addItems(record.get("file_list", []))
        self.files.itemActivated.connect(self._open_file)
        self.files.setToolTip("Open a file in whatever application owns it.")
        column.addWidget(self.files, 1)

        column.addSpacing(space("md"))
        column.addWidget(self._section("SKILL.md"))
        self.body = QPlainTextEdit(body)
        self.body.setReadOnly(True)
        column.addWidget(self.body, 2)

        close = QPushButton("Close")
        close.setObjectName("globalCreateBtn")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.setSpacing(space("md"))
        # Removing is offered only where it can happen: a skill that came with
        # Bristol is source under version control, and the loader refuses it.
        if record.get("root") != "native":
            remove = QPushButton("Remove")
            remove.setObjectName("deleteBtn")
            remove.setAutoDefault(False)
            remove.clicked.connect(self._remove)
            row.addWidget(remove)
        row.addStretch(1)
        row.addWidget(close)
        column.addLayout(row)

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionHeader")
        return label

    def _remove(self) -> None:
        """Delete a downloaded skill, after a confirmation that says what goes
        with it."""
        record = self._record
        held = (f" It is held by {', '.join(record['holders'])}, and removing "
                f"it detaches it." if record.get("holders") else "")
        if not dialogs.confirm(
            self, "Remove This Skill?",
            f"{_title(record)} will be deleted from disk and no session will "
            f"be able to load it.{held} This cannot be undone.",
            "Remove", destructive=True,
        ):
            return
        code, out, err = self._run("remove", record["name"])
        if code != 0:
            dialogs.notify(self, "Not Removed",
                           (err or out).strip() or "The loader refused.")
            return
        self.removed = True
        self.accept()

    def _attachment(self, slug: str, attached: bool) -> None:
        """A tick is an attachment, written where the command line writes it."""
        command = "attach" if attached else "detach"
        code, out, err = self._run(command, self._record["name"],
                                   "--agent", slug)
        if code != 0:
            dialogs.notify(self, "Not Changed",
                           (err or out).strip() or "The loader refused.")
            # The write did not land, so the box goes back to what is true.
            box = self.boxes[slug]
            box.blockSignals(True)
            box.setChecked(not attached)
            box.blockSignals(False)

    def _open_file(self, item) -> None:
        open_uri(str(Path(self._record["path"]) / item.text()))


class SkillsTab(QWidget):
    def __init__(self, conn, parent=None, on_ticket_filed=None) -> None:
        super().__init__(parent)
        self.conn = conn
        # Called once a request has become a card, so the board shows it.
        self._on_ticket_filed = on_ticket_filed
        self._listing: dict = {"skills": [], "agents": {}}

        # The top row narrows the list, and New Skill sits at its right edge.
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter")
        self.search.textChanged.connect(self._fill_list)
        self.source = QComboBox()
        self.source.addItems([ANY_SOURCE, CAME_WITH, DOWNLOADED])
        self.source.currentIndexChanged.connect(self._fill_list)
        self.holder = QComboBox()
        self.holder.currentIndexChanged.connect(self._fill_list)
        for picker in (self.source, self.holder):
            picker.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.new_btn = QPushButton("New Skill")
        self.new_btn.setObjectName("globalCreateBtn")
        self.new_btn.clicked.connect(self._new_skill)

        # The field and its two pickers sit close together as one control,
        # apart from New Skill at the far edge.
        self.search.setMaximumWidth(LAYOUT["filter_field_max_w"])
        top = QHBoxLayout()
        top.setSpacing(space("sm"))
        top.addWidget(self.search, 1)
        top.addWidget(self.source)
        top.addWidget(self.holder)
        top.addStretch(1)
        top.addSpacing(space("xl"))
        top.addWidget(self.new_btn)

        self.list = card_list()
        self.list.itemClicked.connect(lambda *_: self._open())
        self.list.itemActivated.connect(lambda *_: self._open())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("lg"))
        layout.addLayout(top)
        layout.addWidget(self.list, 1)

        self.reload()

    # ----- the loader -------------------------------------------------------

    def _cli(self) -> Path | None:
        root = config_file.project_root()
        if root is None:
            return None
        script = root / SKILLS_CLI
        return script if script.is_file() else None

    def _run(self, *args: str) -> tuple[int, str, str]:
        """One skills.py command. Returns (code, stdout, stderr).

        A missing loader is reported in the same shape as a failing one, so
        every caller has one thing to check.
        """
        script = self._cli()
        if script is None:
            return 1, "", ("No skill loader here — this build cannot find "
                           "src/tools/skill_tools/skills.py.")
        done = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True, text=True, cwd=str(script.parents[3]))
        return done.returncode, done.stdout, done.stderr

    def reload(self) -> None:
        """Show what the loader currently reports. A loader that fails stands
        where the skills would, as the list's one row."""
        code, out, err = self._run("list", "--json")
        if code != 0:
            self._listing = {"skills": [], "agents": {}}
            self.list.clear()
            self.list.addItem(err.strip() or "The skill loader failed.")
            self.list.setEnabled(False)
            return
        self.list.setEnabled(True)
        try:
            self._listing = json.loads(out)
        except json.JSONDecodeError:
            self._listing = {"skills": [], "agents": {}}
        self._fill_agents()
        self._fill_list()

    def _fill_agents(self) -> None:
        """The holder filter's options: any agent, no agent, then each agent by
        name. Rebuilt on every read, and the chosen one is kept where it
        survives the rebuild."""
        current = self.holder.currentData()
        self.holder.blockSignals(True)
        self.holder.clear()
        self.holder.addItem(ANY_AGENT, None)
        self.holder.addItem(NO_AGENT, NO_AGENT_DATA)
        fill_agents(self.holder, sorted(self._listing.get("agents", {})))
        index = self.holder.findData(current) if current else -1
        self.holder.setCurrentIndex(max(index, 0))
        self.holder.blockSignals(False)

    def _fill_list(self) -> None:
        """Every skill a session can load, narrowed by the top row and ordered
        by the name a person reads."""
        self.list.clear()
        records = [r for r in self._listing.get("skills", []) if self._shown(r)]
        for record in sorted(records, key=lambda r: _title(r).lower()):
            self._add_skill(record)

    def _shown(self, record: dict) -> bool:
        """Whether the top row's three controls leave this skill on the list.
        They narrow together: a skill has to pass all three."""
        text = self.search.text().strip().lower()
        haystack = " ".join((record["name"], _title(record),
                             record.get("subtitle", ""),
                             record.get("description", ""))).lower()
        if text and text not in haystack:
            return False
        source = self.source.currentText()
        if source == CAME_WITH and record["root"] != "native":
            return False
        if source == DOWNLOADED and record["root"] == "native":
            return False
        holder = self.holder.currentData()
        holders = record.get("holders", [])
        if holder == NO_AGENT_DATA and holders:
            return False
        if holder not in (None, NO_AGENT_DATA) and holder not in holders:
            return False
        return True

    def _add_skill(self, record: dict) -> None:
        """One card: the name, the subtitle, where it came from, and a pill per
        agent holding it."""
        meta = "   ·   ".join(part for part in (
            record["said_origin"], record.get("said_scan", "")) if part)
        item = QListWidgetItem()
        item.setData(Qt.UserRole, record)
        item.setData(CARD_ROLE, {
            "title": _title(record),
            "description": record.get("subtitle", ""),
            "meta": meta,
            "pills": [agent_caption(h) for h in record.get("holders", [])],
        })
        item.setToolTip(record.get("description", ""))
        self.list.addItem(item)

    # ----- actions ----------------------------------------------------------

    def _record(self, name: str) -> dict | None:
        for record in self._listing.get("skills", []):
            if record["name"] == name:
                return record
        return None

    def _new_skill(self) -> None:
        """Ask for a skill or import one. A skill that lands opens in its own
        window, where the agents that should hold it are ticked; a request that
        became a card shows on the board."""
        before = {s["name"] for s in self._listing.get("skills", [])}
        dialog = NewSkillDialog(self, self._run, self._file_request)
        if not dialog.exec():
            return
        if dialog.filed and self._on_ticket_filed is not None:
            self._on_ticket_filed()
        if not dialog.imported:
            return
        self.reload()
        new = [s for s in self._listing.get("skills", [])
               if s["name"] not in before]
        if len(new) == 1:
            self._show(new[0])

    def _file_request(self, title: str, body: str) -> str:
        """File a request for a skill as a card: To Do, assigned to
        chief_of_staff, under the standing workstream, at the bottom of the
        column. Returns what went wrong, or an empty string."""
        root = config_file.project_root()
        script = root / TICKETS_CLI if root is not None else None
        if script is None or not script.is_file():
            return "This build cannot find the ticket writer."
        args = [sys.executable, str(script), "add-task",
                "--title", f"New Skill: {title}", "--description", body,
                "--stage", "active", "--status", "todo",
                "--assignee", "chief_of_staff", "--reporter", "user",
                "--actor", "user", "--record-type", "build"]
        epic = self._standing_epic()
        if epic is not None:
            args += ["--epic-id", str(epic)]
        done = subprocess.run(args, capture_output=True, text=True,
                              cwd=str(root))
        if done.returncode != 0:
            return (done.stderr or done.stdout).strip() or "The card was not filed."
        return ""

    def _standing_epic(self) -> int | None:
        """The standing workstream's epic, where the board has one."""
        if self.conn is None:
            return None
        try:
            row = self.conn.execute(
                "SELECT id FROM epic WHERE type=? ORDER BY id LIMIT 1",
                (STANDING_KIND,)).fetchone()
        except Exception:  # noqa: BLE001 - a board without the column files unfiled
            return None
        return row[0] if row else None

    def _open(self) -> None:
        """Open the clicked skill's own window."""
        item = self.list.currentItem()
        record = item.data(Qt.UserRole) if item is not None else None
        if isinstance(record, dict):
            self._show(record)

    def _show(self, record: dict) -> None:
        code, out, err = self._run("view", record["name"])
        dialog = SkillDialog(self, record, sorted(self._listing.get("agents", {})),
                             out if code == 0 else (err.strip() or "Unreadable."),
                             self._run)
        dialog.exec()
        self.list.clearSelection()
        self.reload()
