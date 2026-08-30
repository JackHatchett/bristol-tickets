"""ui/skills_tab.py — the Skills tab: what a session can load, and how a new
skill gets here.

Every fact on this page comes from one call to
``src/tools/skill_tools/skills.py list --json``, the same loader a session
reads, so the app and a session cannot disagree about a name, a description or
an origin. Attaching and removing are that tool's own commands, run the same
way.

The page performs the mechanical half of an import and stops there. Judging a
skill is a read of its body and of every script it carries, and the app cannot
read; the fetch therefore lands the skill in quarantine and files a card for
``chief_of_staff``, whose procedure is ``src/skills/importing-a-skill``. What is
quarantined stays invisible to every session until that judgment is made.

A skill opens into a view of its own — its text, its files, its source and a
tick box per agent — and attaching happens there, beside what is being
attached. The page's bottom row therefore narrows the list rather than
attaching: by text, by whether a skill came with Bristol or was downloaded, and
by which agent holds it.

The page offers no trust control. The user has no basis on which to press one,
which is why the judgment was taken off him in the first place, and a button
asking him to overrule it is that gate wearing another label. Wanting a
quarantined skill sooner is said on its card, where every other decision about
it already lives.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox,
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
from .theme import LAYOUT, space

SKILLS_CLI = Path("src") / "tools" / "skill_tools" / "skills.py"

# The three things the page has to say in its own words, kept together because
# they are one vocabulary: importing, quarantine, and what ends it.
IMPORT_NOTE = (
    "Import downloads the skill and stops there. It lands in quarantine, where "
    "no session can use it, and a card asks chief_of_staff to read it and "
    "decide. Nothing else changes and nothing is asked of you.")
QUARANTINE_NOTE = (
    "Downloaded, and nobody has read it yet, so no agent can use it. Each one "
    "waits on the card beside it — say so on that card if you want it used.")

# A quarantined skill's card. The body is the record-type skeleton every build
# card takes, so a card filed here reads like one filed anywhere else.
CARD_TITLE = "Judge and attach the skill {name}"
CARD_BODY = """Story:
As the user I want a skill fetched from the app judged and attached so that what I found in a browser becomes a capability an agent holds.

Acceptance Criteria:
1. Given {name}, quarantined from {origin}, when it is read, then it is judged against src/skills/importing-a-skill/SKILL.md and the case it falls to is named.
2. Given it clears, when it is trusted, then it is attached to the agent whose work it serves and that agent is named here.
3. Given it does not clear, when it is refused, then it stays in quarantine and this card returns to the user with what was read, what was not, and what would change the answer.

It carries {code}."""


# The three ways the list narrows. Each is one control on the bottom row, and
# "any" is the option that turns that control off.
ANY_SOURCE = "Any source"
CAME_WITH = "Came with Bristol"
DOWNLOADED = "Downloaded"
ANY_AGENT = "Any agent"
NO_AGENT = "No agent"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        # What the page behind should say once this closes, where a tick wrote
        # something. Empty while nothing has been written.
        self.status = ""

        self.setWindowTitle(record["name"])
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["dialog_min_w"])
        self.setMinimumHeight(LAYOUT["wizard_min_h"])

        heading = QLabel(record["name"])
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)

        description = QLabel(record.get("description", ""))
        description.setWordWrap(True)

        facts = QLabel(f"{record['said_origin']}   ·   {record['said_contents']}")
        facts.setObjectName("metaText")
        facts.setWordWrap(True)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("md"))
        column.addWidget(heading)
        column.addWidget(description)
        column.addWidget(facts)

        # The source, as the address it actually came from rather than a name to
        # go and look up.
        self.source_btn = None
        if record.get("source_url"):
            self.source_btn = QPushButton("Open the source at this commit")
            self.source_btn.setObjectName("linkRow")
            self.source_btn.setToolTip(record["source_url"])
            self.source_btn.clicked.connect(
                lambda: open_uri(record["source_url"]))
            column.addWidget(self.source_btn, 0, Qt.AlignLeft)

        column.addSpacing(space("md"))
        column.addWidget(self._section("Agents"))
        column.addWidget(QLabel(
            "Tick an agent to attach this skill to it. A session carries the "
            "skills its agent holds."), 0)
        self.boxes: dict[str, QCheckBox] = {}
        held = set(record.get("holders", []))
        for slug in agents:
            box = QCheckBox(slug)
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
        row.addStretch(1)
        row.addWidget(close)
        column.addLayout(row)

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionHeader")
        return label

    def _attachment(self, slug: str, attached: bool) -> None:
        """A tick is an attachment, written where the command line writes it."""
        command = "attach" if attached else "detach"
        code, out, err = self._run(command, self._record["name"],
                                   "--agent", slug)
        self.status = (out or err).strip()
        if code != 0:
            # The write did not land, so the box goes back to what is true.
            box = self.boxes[slug]
            box.blockSignals(True)
            box.setChecked(not attached)
            box.blockSignals(False)

    def _open_file(self, item) -> None:
        open_uri(str(Path(self._record["path"]) / item.text()))


class SkillsTab(QWidget):
    def __init__(self, conn, parent=None, on_card_filed=None) -> None:
        super().__init__(parent)
        self.conn = conn
        # Called when this page files a card, so the board behind it can catch
        # up. Absent in a bare construction (the smoke check), where there is no
        # board to refresh.
        self._on_card_filed = on_card_filed
        self._listing: dict = {"skills": [], "agents": {}}

        self.address = QLineEdit()
        self.address.setPlaceholderText(
            "Paste the web address of a skill's folder on GitHub")
        self.address.returnPressed.connect(self._import)
        self.import_btn = QPushButton("Import")
        self.import_btn.setObjectName("globalCreateBtn")
        self.import_btn.clicked.connect(self._import)

        address_row = QHBoxLayout()
        address_row.setSpacing(space("md"))
        address_row.addWidget(self.address, 1)
        address_row.addWidget(self.import_btn)

        # What the button does, beside the button, because a page that only
        # reveals itself once pressed is a page nobody presses.
        self.import_note = QLabel(IMPORT_NOTE)
        self.import_note.setObjectName("formCaption")
        self.import_note.setWordWrap(True)

        self.status = QLabel()
        self.status.setObjectName("formCaption")
        self.status.setWordWrap(True)

        self.list = QListWidget()
        self.list.setObjectName("searchResults")
        self.list.currentItemChanged.connect(lambda *_: self._sync_actions())
        self.list.itemActivated.connect(lambda *_: self._open())

        # The bottom row narrows the list. Attaching moved into the skill's own
        # view, where the agents are chosen beside what is being attached.
        self.search = QLineEdit()
        self.search.setPlaceholderText("Narrow by name or description")
        self.search.textChanged.connect(self._fill_list)
        self.source = QComboBox()
        self.source.addItems([ANY_SOURCE, CAME_WITH, DOWNLOADED])
        self.source.currentIndexChanged.connect(self._fill_list)
        self.holder = QComboBox()
        self.holder.currentIndexChanged.connect(self._fill_list)

        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self._open)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setObjectName("deleteBtn")
        self.remove_btn.clicked.connect(self._remove)

        actions = QHBoxLayout()
        actions.setSpacing(space("md"))
        actions.addWidget(self.search, 1)
        actions.addWidget(self.source)
        actions.addWidget(self.holder)
        actions.addStretch(1)
        actions.addWidget(self.open_btn)
        actions.addWidget(self.remove_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("lg"))
        layout.addLayout(address_row)
        layout.addWidget(self.import_note)
        layout.addWidget(self.status)
        layout.addWidget(self.list, 1)
        layout.addLayout(actions)

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
        """Show what the loader currently reports."""
        code, out, err = self._run("list", "--json")
        if code != 0:
            self._listing = {"skills": [], "agents": {}}
            self.list.clear()
            self.setEnabled(False)
            self.status.setText(err.strip() or "The skill loader failed.")
            return
        self.setEnabled(True)
        try:
            self._listing = json.loads(out)
        except json.JSONDecodeError:
            self._listing = {"skills": [], "agents": {}}
        self._fill_agents()
        self._fill_list()
        self._sync_actions()

    def _fill_agents(self) -> None:
        """The holder filter's options: any agent, no agent, then each agent by
        name. Rebuilt on every read, and the chosen one is kept where it
        survives the rebuild."""
        current = self.holder.currentText()
        self.holder.blockSignals(True)
        self.holder.clear()
        self.holder.addItems([ANY_AGENT, NO_AGENT]
                             + sorted(self._listing.get("agents", {})))
        index = self.holder.findText(current) if current else -1
        self.holder.setCurrentIndex(max(index, 0))
        self.holder.blockSignals(False)

    def _fill_list(self) -> None:
        """Quarantined skills first, because they are the ones with something
        outstanding; then everything a session can load."""
        selected = self._selected_name()
        self.list.clear()
        skills = [s for s in self._listing.get("skills", []) if self._shown(s)]
        quarantined = [s for s in skills if s["root"] == "quarantined"]
        loadable = [s for s in skills if s["root"] != "quarantined"]
        for heading, note, group in (("Quarantined", QUARANTINE_NOTE, quarantined),
                                     ("Loadable", "", loadable)):
            if not group:
                continue
            self._add_heading(heading)
            if note:
                self._add_note(note)
            for record in group:
                self._add_skill(record)
        if selected:
            self._select(selected)

    def _shown(self, record: dict) -> bool:
        """Whether the bottom row's three controls leave this skill on the list.
        They narrow together: a skill has to pass all three."""
        text = self.search.text().strip().lower()
        if text and text not in (record["name"] + " "
                                 + record.get("description", "")).lower():
            return False
        source = self.source.currentText()
        if source == CAME_WITH and record["root"] != "native":
            return False
        if source == DOWNLOADED and record["root"] == "native":
            return False
        holder = self.holder.currentText()
        holders = record.get("holders", [])
        if holder == NO_AGENT and holders:
            return False
        if holder not in (ANY_AGENT, NO_AGENT, "") and holder not in holders:
            return False
        return True

    def _add_heading(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.NoItemFlags)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.list.addItem(item)

    def _add_note(self, text: str) -> None:
        """A sentence under a heading saying what the reader is looking at. It
        sits in the list rather than above it so it appears only when the
        section it explains does."""
        item = QListWidgetItem(text)
        item.setFlags(Qt.NoItemFlags)
        self.list.addItem(item)

    def _add_skill(self, record: dict) -> None:
        """Three lines: the name by itself, the three labelled facts, then the
        description. Nothing on the row has to be recognised to be understood.
        """
        last = (self._said_deciding_card(record["name"])
                if record["root"] == "quarantined" else record["said_holders"])
        facts = "   ·   ".join((record["said_origin"],
                                record["said_contents"], last))
        item = QListWidgetItem(
            f"{record['name']}\n{facts}\n{self._one_line_description(record)}")
        item.setData(Qt.UserRole, record)
        self.list.addItem(item)

    def _said_deciding_card(self, name: str) -> str:
        """The card that will decide a quarantined skill, found on the board by
        the title an import gives it. The board is where the decision lives, so
        it is where the number is read from rather than stored here."""
        row = self.conn.execute(
            "SELECT id FROM task WHERE title = ? ORDER BY id DESC LIMIT 1",
            (CARD_TITLE.format(name=name),)).fetchone()
        return f"Card #{row[0]} decides it" if row else "No card asks for it yet"

    def _one_line_description(self, record: dict) -> str:
        """The description cut to the width the list actually has, so a long one
        ends in an ellipsis at the edge instead of running underneath it."""
        text = record.get("description", "")
        room = self.list.viewport().width() - 2 * space("lg")
        if room <= 0:
            return text
        return QFontMetrics(self.list.font()).elidedText(
            text, Qt.ElideRight, int(room))

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Re-cut every description to the new width. The rows carry no state of
        their own, so redrawing the list is the whole of it."""
        super().resizeEvent(event)
        if hasattr(self, "list"):
            self._fill_list()

    # ----- selection --------------------------------------------------------

    def _selected(self) -> dict | None:
        item = self.list.currentItem()
        if item is None:
            return None
        record = item.data(Qt.UserRole)
        return record if isinstance(record, dict) else None

    def _selected_name(self) -> str:
        record = self._selected()
        return record["name"] if record else ""

    def _select(self, name: str) -> None:
        for row in range(self.list.count()):
            item = self.list.item(row)
            record = item.data(Qt.UserRole)
            if isinstance(record, dict) and record["name"] == name:
                self.list.setCurrentItem(item)
                return

    def _sync_actions(self) -> None:
        record = self._selected()
        chosen = bool(record)
        native = chosen and record["root"] == "native"
        self.open_btn.setEnabled(chosen)
        # A native skill is source under version control, and the loader refuses
        # to delete one; the button says so by being unavailable rather than by
        # failing when pressed.
        self.remove_btn.setEnabled(chosen and not native)

    # ----- actions ----------------------------------------------------------

    def _import(self) -> None:
        address = self.address.text().strip()
        if not address:
            return
        self.import_btn.setEnabled(False)
        self.status.setText("Fetching…")
        # Repainted before the fetch blocks, so the page says what it is doing
        # rather than freezing silently.
        self.status.repaint()
        try:
            code, out, err = self._run("install", address)
        finally:
            self.import_btn.setEnabled(True)
        if code != 0:
            self.status.setText(err.strip() or "The fetch failed.")
            return
        self.address.clear()
        self.reload()
        record = self._quarantined_from(out)
        if record is None:
            self.status.setText(out.strip().splitlines()[-1] if out.strip()
                                else "Fetched.")
            return
        task_id = self._file_card(record)
        # Read again, so the new row names the card that will decide it.
        self.reload()
        self._select(record["name"])
        # Name, where from, what is in it, and who decides — the order the
        # reader needs them in, and the same words the rows use.
        self.status.setText(
            f"{record['name']} is here. {record['said_origin']}. It carries "
            f"{record['said_contents']}. No session can use it yet: card "
            f"#{task_id} asks chief_of_staff to read it and decide.")

    def _quarantined_from(self, output: str) -> dict | None:
        """The skill the install just made, found by asking the loader again
        rather than by parsing what install printed."""
        names = {s["name"] for s in self._listing.get("skills", [])
                 if s["root"] == "quarantined"}
        for line in reversed(output.splitlines()):
            for name in names:
                if name in line:
                    return self._record(name)
        records = [s for s in self._listing.get("skills", [])
                   if s["root"] == "quarantined"]
        return records[0] if len(records) == 1 else None

    def _record(self, name: str) -> dict | None:
        for record in self._listing.get("skills", []):
            if record["name"] == name:
                return record
        return None

    def _file_card(self, record: dict) -> int:
        """File the judgment as a card, which is where the decision lives."""
        scripts = record.get("scripts", [])
        code = record["said_contents"] + (
            f" — {', '.join(scripts)}" if scripts else "")
        row = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM task "
            "WHERE stage='active' AND status='todo'").fetchone()
        stamp = _utcnow()
        cur = self.conn.execute(
            "INSERT INTO task (epic_id, title, description, status, stage, "
            "sort_order, pressure, assignee, reporter, estimate, record_type, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (None,
             CARD_TITLE.format(name=record["name"]),
             CARD_BODY.format(name=record["name"], origin=record["origin"],
                              code=code),
             "todo", "active", row[0], 50, "chief_of_staff", "user", "S",
             "build", stamp, stamp),
        )
        self.conn.commit()
        if self._on_card_filed is not None:
            self._on_card_filed()
        return int(cur.lastrowid)

    def _open(self) -> None:
        """Open the selected skill's own view. Attaching happens in there, so
        this page reads again on the way out."""
        record = self._selected()
        if record is None:
            return
        # A quarantined skill is not loadable, so `view` refuses it; `audit` is
        # the read that exists for something nothing has judged, and it carries
        # the same SKILL.md inside it.
        command = "audit" if record["root"] == "quarantined" else "view"
        code, out, err = self._run(command, record["name"])
        dialog = SkillDialog(self, record, sorted(self._listing.get("agents", {})),
                             out if code == 0 else (err.strip() or "Unreadable."),
                             self._run)
        dialog.exec()
        if dialog.status:
            self.status.setText(dialog.status)
        self.reload()

    def _remove(self) -> None:
        record = self._selected()
        if record is None:
            return
        held = (f" {record['said_holders']}, and removing it detaches it."
                if record.get("holders") else f" {record['said_holders']}.")
        if not dialogs.confirm(
            self, "Remove This Skill",
            f"{record['name']} will be deleted from disk and no session will "
            f"be able to load it.{held} This cannot be undone.",
            "Remove It", destructive=True,
        ):
            return
        code, out, err = self._run("remove", record["name"])
        self.status.setText((out or err).strip())
        self.reload()
