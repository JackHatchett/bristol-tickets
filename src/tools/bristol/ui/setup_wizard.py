"""ui/setup_wizard.py — first-run setup, so a fresh clone opens into a board.

Bristol Tickets imports nothing from the rest of ``src/tools``: this module
uses PySide6, the standard library, and the sibling ``instance`` module. The
database it provisions comes from ``bristol/schema.sql`` — the same generated
snapshot ``app.py`` applies on every launch — and the configuration it writes is
``config/config.example.json`` with this installation's answers substituted in.

Nothing reaches the disk until Finish, and Finish asks before replacing an
existing ``config/config.local.json``. Cancel leaves the machine untouched.
"""

from __future__ import annotations

import getpass
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

import config_file  # bristol-local; see module docstring
import instance

SLUG_PATTERN = r"[a-z0-9][a-z0-9_-]*"
REQUIRED_AGENT = "chief_of_staff"
INSTANCE_TOKEN = "<your-instance>"
PROJECT_TOKEN = "/path/to/project"
NOTEBOOK_TOKEN = "/path/to/notebook"
ZOTERO_TOKEN = "/path/to/Zotero"
HOME_TOKEN = "/path/to/your/home"


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

project_root = config_file.project_root


def config_local_path(root: Path) -> Path:
    return root / "config" / "config.local.json"


def needs_setup(discovered_db: Path | None) -> bool:
    """True when this machine holds no installation to open.

    A discoverable database or a written ``config.local.json`` each mean setup
    has already happened, whatever else is missing.
    """
    if discovered_db is not None and discovered_db.exists():
        return False
    root = project_root()
    if root is not None and config_local_path(root).exists():
        return False
    return True


def _shipped_agents(root: Path) -> list[tuple[str, str]]:
    """Every agent in the example config, as (slug, one-line description)."""
    try:
        example = json.loads(
            (root / "config" / "config.example.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []
    agents = example.get("agents", {})
    if not isinstance(agents, dict):
        return []
    return [
        (slug, str(body.get("notes", "")).strip())
        for slug, body in agents.items()
        if slug != "_notes" and isinstance(body, dict)
    ]


# ---------------------------------------------------------------------------
# A labelled folder picker, used on three pages
# ---------------------------------------------------------------------------

class FolderRow(QWidget):
    def __init__(self, caption: str, clearable: bool = False) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.field = QLineEdit()
        self.field.setReadOnly(True)
        self.field.setPlaceholderText("(none)")
        self.caption = caption
        self.chosen_by_user = False
        choose = QPushButton("Choose…")
        choose.clicked.connect(self._choose)
        row.addWidget(self.field, 1)
        row.addWidget(choose)
        if clearable:
            clear = QPushButton("Clear")
            clear.clicked.connect(lambda: self.field.setText(""))
            row.addWidget(clear)

    def _choose(self) -> None:
        start = self.field.text().strip() or str(Path.home())
        picked = QFileDialog.getExistingDirectory(self, self.caption, start)
        if picked:
            self.chosen_by_user = True
            self.field.setText(picked)

    def value(self) -> str:
        return self.field.text().strip()

    def set_value(self, text: str) -> None:
        self.field.setText(text)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def default_slug() -> str:
    """The operating system's short user name, reduced to the allowed shape."""
    try:
        raw = getpass.getuser()
    except Exception:
        raw = ""
    cleaned = re.sub(r"[^a-z0-9_-]", "-", raw.lower()).strip("-")
    return cleaned or "default"


class InstancePage(QWizardPage):
    """The installation's name, and the folder its data lives in."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.setTitle("Name this installation")
        self.setSubTitle(
            "This name labels the folder holding your board and everything you "
            "save. Lower case, no spaces."
        )

        self.slug_edit = QLineEdit(default_slug())
        self.slug_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(SLUG_PATTERN))
        )
        self.slug_edit.textChanged.connect(self._on_slug_changed)
        self.slug_edit.inputRejected.connect(self._on_input_rejected)

        self.rejected_hint = QLabel(
            "That key is not allowed in the name. Use lower-case letters, "
            "digits, hyphens and underscores."
        )
        self.rejected_hint.setWordWrap(True)
        self.rejected_hint.setVisible(False)

        self.folder = FolderRow("Choose where this installation's data lives")
        self.folder.set_value(str(root / "data" / default_slug()))
        self.folder.field.textChanged.connect(self.completeChanged)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Installation name"))
        layout.addWidget(self.slug_edit)
        layout.addWidget(self.rejected_hint)
        layout.addSpacing(10)
        layout.addWidget(QLabel("Data folder"))
        layout.addWidget(self.folder)
        layout.addStretch(1)

    def _on_input_rejected(self) -> None:
        """Show what the field will accept, once a key has been refused.

        // A validator drops a disallowed keystroke with no signal to the
        // typist, so the field looks unresponsive rather than strict.
        """
        self.rejected_hint.setVisible(True)

    def _on_slug_changed(self) -> None:
        """The default folder tracks the name until the user picks one."""
        if not self.folder.chosen_by_user:
            slug = self.slug_edit.text().strip() or default_slug()
            self.folder.set_value(str(self.root / "data" / slug))
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return bool(self.slug_edit.text().strip()) and bool(self.folder.value())

    def instance_dir(self) -> Path:
        """The folder holding this installation's data.

        A folder already named for the installation is taken as it stands; any
        other choice is read as the place to put that folder in.
        """
        chosen = Path(self.folder.value()).expanduser()
        slug = self.slug_edit.text().strip()
        return chosen if chosen.name == slug else chosen / slug


class AgentsPage(QWizardPage):
    """Which of the shipped agents this installation runs."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.setTitle("Choose your agents")
        self.setSubTitle(
            "Each agent is a role with its own instructions and its own "
            "folder. You can add or remove agents later by editing your "
            "configuration."
        )

        installed_only = QLabel(
            "Checking a box installs that agent. It does not choose which one "
            "you talk to: that is the “Start next session as” selector above "
            "the board, and you can change it whenever you like."
        )
        installed_only.setWordWrap(True)

        self.boxes: dict[str, QCheckBox] = {}
        holder = QWidget()
        inner = QVBoxLayout(holder)
        for slug, notes in _shipped_agents(root):
            box = QCheckBox(slug)
            box.setChecked(True)
            box.stateChanged.connect(self.completeChanged)
            self.boxes[slug] = box
            inner.addWidget(box)
            if notes:
                caption = QLabel(notes)
                caption.setWordWrap(True)
                caption.setIndent(22)
                inner.addWidget(caption)
            if slug == REQUIRED_AGENT:
                box.setEnabled(False)
                required = QLabel(
                    "Always installed: it is the only agent allowed to change "
                    "how any of them work."
                )
                required.setWordWrap(True)
                required.setIndent(22)
                inner.addWidget(required)
            inner.addSpacing(6)
        inner.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        layout = QVBoxLayout(self)
        layout.addWidget(installed_only)
        layout.addSpacing(8)
        layout.addWidget(scroll)

    def isComplete(self) -> bool:
        return any(box.isChecked() for box in self.boxes.values())

    def enabled(self) -> list[str]:
        return [slug for slug, box in self.boxes.items()
                if box.isChecked() or slug == REQUIRED_AGENT]


class IntegrationsPage(QWizardPage):
    """Optional folders outside the clone that agents read and write."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Link your notes and library")
        self.setSubTitle("Both are optional. Leave either empty to skip it.")

        self.notebook = FolderRow("Choose your Markdown notebook folder", clearable=True)
        self.zotero = FolderRow("Choose your Zotero data folder", clearable=True)

        zotero_label = QLabel(
            "Zotero data folder — your reference library. Skip this if you do "
            "not use Zotero."
        )
        zotero_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Markdown notebook — a folder of notes you edit yourself"))
        layout.addWidget(self.notebook)
        layout.addSpacing(10)
        layout.addWidget(zotero_label)
        layout.addWidget(self.zotero)
        layout.addStretch(1)


class SummaryPage(QWizardPage):
    """What Finish will write."""

    def __init__(self, wizard: "SetupWizard") -> None:
        super().__init__()
        self._wizard = wizard
        self.setTitle("Ready to set up")
        self.setSubTitle("Nothing has been written yet. Finish creates the following.")
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout = QVBoxLayout(self)
        layout.addWidget(self.body)
        layout.addStretch(1)

    def initializePage(self) -> None:
        w = self._wizard
        instance_dir = w.instance_page.instance_dir()
        notebook = w.integrations_page.notebook.value()
        zotero = w.integrations_page.zotero.value()
        lines = [
            f"Data folder: {instance_dir}",
            f"Board: {instance_dir / 'tickets' / 'tickets.db'}",
            f"Configuration: {config_local_path(w.root)}",
            f"Pointer, so the app still finds your data after you move it: "
            f"{instance.pointer_path()}",
            f"Agents: {', '.join(w.agents_page.enabled())}",
            f"Markdown notebook: {notebook or 'skipped'}",
            f"Zotero: {zotero or 'skipped'}",
            "",
            "Finish creates those folders, provisions the board, writes the "
            "configuration and the pointer, and opens the board. Cancel writes "
            "nothing.",
        ]
        self.body.setText("\n".join(lines))


# ---------------------------------------------------------------------------
# The wizard
# ---------------------------------------------------------------------------

class SetupWizard(QWizard):
    def __init__(self, root: Path, parent=None) -> None:
        super().__init__(parent)
        self.root = root
        self.db_path: Path | None = None
        self.setWindowTitle("Bristol Tickets — Setup")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setMinimumSize(720, 480)

        self.instance_page = InstancePage(root)
        self.agents_page = AgentsPage(root)
        self.integrations_page = IntegrationsPage()
        self.summary_page = SummaryPage(self)
        for page in (self.instance_page, self.agents_page,
                     self.integrations_page, self.summary_page):
            self.addPage(page)

    def accept(self) -> None:
        """Write everything, or nothing."""
        config_path = config_local_path(self.root)
        if config_path.exists():
            answer = QMessageBox.question(
                self,
                "Replace your configuration?",
                f"{config_path} already exists.\n\n"
                "Finishing setup replaces it with your answers.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        try:
            self.db_path = apply_setup(
                root=self.root,
                instance_dir=self.instance_page.instance_dir(),
                slug=self.instance_page.slug_edit.text().strip(),
                agents=self.agents_page.enabled(),
                notebook=self.integrations_page.notebook.value(),
                zotero=self.integrations_page.zotero.value(),
            )
        except SetupStepError as exc:
            QMessageBox.critical(
                self, "Setup failed",
                f"Setup could not {exc.step}.\n\n{exc.remedy}\n\n"
                f"Nothing was written after that point.\n\n"
                f"Details: {exc.cause}",
            )
            return
        super().accept()


# ---------------------------------------------------------------------------
# Writing the installation
# ---------------------------------------------------------------------------

def _substitute(value, mapping: list[tuple[str, str]]):
    """Every placeholder in the example config, replaced throughout."""
    if isinstance(value, str):
        for token, replacement in mapping:
            value = value.replace(token, replacement)
        return value
    if isinstance(value, dict):
        return {k: _substitute(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, mapping) for v in value]
    return value


def _drop_env_values_containing(config: dict, token: str) -> None:
    """Remove every env entry still pointing at an unanswered placeholder."""
    for holder in [config] + list(config.get("agents", {}).values()):
        if not isinstance(holder, dict):
            continue
        env = holder.get("env")
        if isinstance(env, dict):
            for key in [k for k, v in env.items() if isinstance(v, str) and token in v]:
                del env[key]


def build_config(root: Path, instance_dir: Path, slug: str, agents: list[str],
                 notebook: str, zotero: str) -> dict:
    """The example config with this installation's answers filled in."""
    example = json.loads(
        (root / "config" / "config.example.json").read_text(encoding="utf-8")
    )

    inside_repo = instance_dir == root / "data" / slug
    data_token = f"data/{slug}" if inside_repo else str(instance_dir)
    mapping = [
        (f"{PROJECT_TOKEN}/data/{INSTANCE_TOKEN}", str(instance_dir)),
        (f"data/{INSTANCE_TOKEN}", data_token),
        (PROJECT_TOKEN, str(root)),
        (INSTANCE_TOKEN, slug),
        (HOME_TOKEN, str(Path.home())),
    ]
    if notebook:
        mapping.append((NOTEBOOK_TOKEN, notebook))
    if zotero:
        mapping.append((ZOTERO_TOKEN, zotero))

    config = _substitute(example, mapping)

    config["active_agent"] = "chief_of_staff" if "chief_of_staff" in agents else agents[0]
    config["agents"] = {
        key: body for key, body in config.get("agents", {}).items()
        if key == "_notes" or key in agents
    }

    if not notebook:
        config.pop("markdown_notebook", None)
        _drop_env_values_containing(config, NOTEBOOK_TOKEN)
    if not zotero:
        config.pop("zotero", None)
        _drop_env_values_containing(config, ZOTERO_TOKEN)

    # An absent drives entry makes the photo tools exit with a clear message; a
    # placeholder path makes them act on a folder that is not there.
    drives = config.get("drives")
    if isinstance(drives, dict):
        drives.pop("external1", None)

    scan = config.get("keyword_scan")
    if isinstance(scan, dict):
        scan["keywords"] = [slug]

    return config


def _declared_dirs(root: Path, config: dict, instance_dir: Path) -> list[Path]:
    """Every folder the configuration says this installation owns."""
    dirs = [instance_dir, instance_dir / "tickets"]
    for body in config.get("agents", {}).values():
        if not isinstance(body, dict):
            continue
        for declared in body.get("key_data_paths", []):
            if not isinstance(declared, str) or not declared.strip():
                continue
            path = Path(declared).expanduser()
            dirs.append(path if path.is_absolute() else root / declared)
    return dirs


class SetupStepError(Exception):
    """A setup step that failed, with what the reader can do about it."""

    def __init__(self, step: str, remedy: str, cause: Exception) -> None:
        super().__init__(str(cause))
        self.step = step
        self.remedy = remedy
        self.cause = cause


@contextmanager
def _step(step: str, remedy: str):
    """Run one setup step, naming it if it fails."""
    try:
        yield
    except (OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        raise SetupStepError(step, remedy, exc) from exc


def apply_setup(root: Path, instance_dir: Path, slug: str, agents: list[str],
                notebook: str, zotero: str) -> Path:
    """Create the folders, the database, the configuration and the pointer.

    Returns the path of the provisioned board.
    """
    with _step("read the shipped configuration template",
               "Check that config/config.example.json is present in your clone "
               "and is valid JSON."):
        config = build_config(root, instance_dir, slug, agents, notebook,
                              zotero)

    with _step("create your data folders",
               "Choose a data folder you can write to, then run setup again."):
        for path in _declared_dirs(root, config, instance_dir):
            path.mkdir(parents=True, exist_ok=True)

    db_path = instance_dir / "tickets" / "tickets.db"
    with _step("provision the board",
               "A file at that path may already be open or may not be a "
               "database. Close the app holding it, or choose another data "
               "folder."):
        schema_file = Path(__file__).resolve().parent.parent / "schema.sql"
        schema = schema_file.read_text(encoding="utf-8")
        conn = sqlite3.connect(str(db_path), timeout=10)
        try:
            conn.execute("PRAGMA busy_timeout=5000")
            # // A mounted-folder bridge has wedged a database whose rollback
            # // journal was written to disk; MEMORY keeps it off the mount.
            conn.execute("PRAGMA journal_mode=MEMORY")
            conn.executescript(schema)
            conn.commit()
        finally:
            conn.close()

    with _step("write your configuration",
               "Check that you can write to the config/ folder in your clone."):
        config_path = config_file.write(config, config_local_path(root))

    with _step("write the instance pointer",
               "Check that you can write to your user Application Support "
               "folder."):
        instance.write(root, instance_dir.parent, slug, config_path)
    return db_path


def run_setup(parent=None) -> Path | None:
    """Show the wizard. Returns the provisioned board, or None if cancelled."""
    root = project_root()
    if root is None:
        QMessageBox.critical(
            parent,
            "Bristol Tickets — Setup",
            "Setup needs the repository folder you cloned, and cannot find it "
            "from here. Launch Bristol Tickets from inside that folder.",
        )
        return None
    wizard = SetupWizard(root, parent)
    if wizard.exec() != QWizard.Accepted:
        return None
    return wizard.db_path
