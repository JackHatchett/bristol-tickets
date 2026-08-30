"""ui/skills_tab.py — the Skills tab: what a session can load, and how a new
skill gets here.

Every fact on this page comes from one call to
``src/tools/skill_tools/skills.py list --json``, the same loader a session
reads, so the app and a session cannot disagree about a name, a description or
an origin. Attaching, trusting and removing are that tool's own commands, run
the same way.

The page performs the mechanical half of an import and stops there. Judging a
skill is a read of its body and of every script it carries, and the app cannot
read; the fetch therefore lands the skill in quarantine and files a card for
``chief_of_staff``, whose procedure is ``src/skills/importing-a-skill``. What is
quarantined stays invisible to every session until that judgment is made.

Trusting a quarantined skill from here is the user overruling that judgment, and
is the one trust decision this app puts to him.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local; see module docstring

from . import dialogs
from .theme import space

SKILLS_CLI = Path("src") / "tools" / "skill_tools" / "skills.py"

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


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            "Paste the address of a skill's folder on GitHub")
        self.address.returnPressed.connect(self._import)
        self.import_btn = QPushButton("Import")
        self.import_btn.setObjectName("globalCreateBtn")
        self.import_btn.setToolTip(
            "Fetch the skill, record where it came from, and file a card for "
            "chief_of_staff to judge it. Nothing is asked of you.")
        self.import_btn.clicked.connect(self._import)

        address_row = QHBoxLayout()
        address_row.setSpacing(space("md"))
        address_row.addWidget(self.address, 1)
        address_row.addWidget(self.import_btn)

        self.status = QLabel()
        self.status.setObjectName("formCaption")
        self.status.setWordWrap(True)

        self.list = QListWidget()
        self.list.setObjectName("searchResults")
        self.list.currentItemChanged.connect(lambda *_: self._sync_actions())

        self.agent = QComboBox()
        self.agent.setToolTip("Which agent an attachment belongs to.")
        self.attach_btn = QPushButton("Attach")
        self.attach_btn.clicked.connect(lambda: self._attachment("attach"))
        self.detach_btn = QPushButton("Detach")
        self.detach_btn.clicked.connect(lambda: self._attachment("detach"))
        self.trust_btn = QPushButton("Trust Anyway")
        self.trust_btn.clicked.connect(self._trust)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setObjectName("deleteBtn")
        self.remove_btn.clicked.connect(self._remove)

        actions = QHBoxLayout()
        actions.setSpacing(space("md"))
        actions.addWidget(self.agent)
        actions.addWidget(self.attach_btn)
        actions.addWidget(self.detach_btn)
        actions.addStretch(1)
        actions.addWidget(self.trust_btn)
        actions.addWidget(self.remove_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("lg"))
        layout.addLayout(address_row)
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
        current = self.agent.currentText()
        self.agent.clear()
        self.agent.addItems(sorted(self._listing.get("agents", {})))
        if current:
            index = self.agent.findText(current)
            if index >= 0:
                self.agent.setCurrentIndex(index)

    def _holders(self, name: str) -> list[str]:
        return sorted(slug for slug, names
                      in self._listing.get("agents", {}).items()
                      if name in names)

    def _fill_list(self) -> None:
        """Quarantined skills first, because they are the ones with something
        outstanding; then everything a session can load."""
        selected = self._selected_name()
        self.list.clear()
        skills = self._listing.get("skills", [])
        quarantined = [s for s in skills if s["root"] == "quarantined"]
        loadable = [s for s in skills if s["root"] != "quarantined"]
        for heading, group in (("Quarantined", quarantined),
                               ("Loadable", loadable)):
            if not group:
                continue
            self._add_heading(heading)
            for record in group:
                self._add_skill(record)
        if selected:
            self._select(selected)

    def _add_heading(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.NoItemFlags)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.list.addItem(item)

    def _add_skill(self, record: dict) -> None:
        name = record["name"]
        holders = self._holders(name)
        line = f"{name} — {record['origin']}"
        if holders:
            line += f" — {', '.join(holders)}"
        detail = record.get("description", "")
        item = QListWidgetItem(f"{line}\n{self._code_line(record)}  {detail}")
        item.setData(Qt.UserRole, record)
        self.list.addItem(item)

    @staticmethod
    def _code_line(record: dict) -> str:
        """What a skill carries, said differently for one with code and one
        without, because the two are not the same risk."""
        scripts = record.get("scripts", [])
        if not scripts:
            return f"{record.get('files', 0)} files, no executable code."
        return (f"{record.get('files', 0)} files, "
                f"{len(scripts)} carrying executable code.")

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
        quarantined = chosen and record["root"] == "quarantined"
        native = chosen and record["root"] == "native"
        self.attach_btn.setEnabled(chosen and not quarantined
                                   and bool(self.agent.count()))
        self.detach_btn.setEnabled(chosen and not quarantined
                                   and bool(self.agent.count()))
        # Trust is the override, so it exists only where there is a judgment to
        # override.
        self.trust_btn.setVisible(quarantined)
        self.trust_btn.setEnabled(quarantined)
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
        self._select(record["name"])
        task_id = self._file_card(record)
        self.status.setText(
            f"{record['name']} is quarantined and no session can load it. "
            f"Card #{task_id} asks chief_of_staff to judge it.")

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
        code = (f"{len(scripts)} files of executable code: "
                f"{', '.join(scripts)}" if scripts else "no executable code")
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

    def _attachment(self, command: str) -> None:
        record = self._selected()
        slug = self.agent.currentText()
        if record is None or not slug:
            return
        code, out, err = self._run(command, record["name"], "--agent", slug)
        self.status.setText((out or err).strip())
        self.reload()

    def _trust(self) -> None:
        record = self._selected()
        if record is None:
            return
        if not dialogs.confirm(
            self, "Trust This Skill",
            f"{record['name']} is quarantined because nothing has read it yet. "
            f"It carries {self._code_line(record).lower()} Trusting it now "
            f"makes it loadable by every agent without that read, which is "
            f"chief_of_staff's judgment to make and yours to overrule.",
            "Trust It",
        ):
            return
        code, out, err = self._run("trust", record["name"])
        self.status.setText((out or err).strip())
        self.reload()

    def _remove(self) -> None:
        record = self._selected()
        if record is None:
            return
        holders = self._holders(record["name"])
        held = (f" It is attached to {', '.join(holders)}, and removing it "
                f"detaches it from {'them' if len(holders) > 1 else 'it'}."
                if holders else " No agent attaches it.")
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
