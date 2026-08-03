"""ui/setup_wizard.py — first-run setup, so a fresh clone opens into a board.

Bristol imports nothing from the rest of ``src/tools``: this module uses
PySide6, the standard library, and the sibling ``instance`` module. The database
it provisions comes from ``bristol/schema.sql`` — the same generated snapshot
``app.py`` applies on every launch — and the configuration it writes is
``config/config.example.json`` with this installation's answers substituted in.

Nothing reaches the disk until Finish, and Finish asks before replacing an
existing ``config/config.local.json``. Cancel leaves the machine untouched.
"""

from __future__ import annotations

import json
import sqlite3
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

class InstancePage(QWizardPage):
    """Instance name, and the folder this installation's data lives in."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.setTitle("Name this installation")
        self.setSubTitle(
            "The instance name labels your data folder. Everything Bristol and "
            "the agents write for you lives under the folder below."
        )

        self.slug_edit = QLineEdit("default")
        self.slug_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(SLUG_PATTERN))
        )
        self.slug_edit.textChanged.connect(self._on_slug_changed)

        self.folder = FolderRow("Choose where this instance's data lives")
        self.folder.set_value(str(root / "data" / "default"))
        self.folder.field.textChanged.connect(self.completeChanged)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Instance name (lower case, no spaces)"))
        layout.addWidget(self.slug_edit)
        layout.addSpacing(10)
        layout.addWidget(QLabel("Data folder"))
        layout.addWidget(self.folder)
        layout.addStretch(1)

    def _on_slug_changed(self) -> None:
        """The default folder tracks the name until the user picks one."""
        if not self.folder.chosen_by_user:
            slug = self.slug_edit.text().strip() or "default"
            self.folder.set_value(str(self.root / "data" / slug))
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return bool(self.slug_edit.text().strip()) and bool(self.folder.value())

    def instance_dir(self) -> Path:
        """The folder holding this instance's data.

        A folder already named for the instance is taken as it stands; any other
        choice is read as the place to put the instance folder in.
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
            "Each agent is a role with its own charter and its own data folder. "
            "Unchecked agents are left out of your configuration."
        )

        self.boxes: dict[str, QCheckBox] = {}
        holder = QWidget()
        inner = QVBoxLayout(holder)
        for slug, notes in _shipped_agents(root):
            box = QCheckBox(f"{slug} — {notes}" if notes else slug)
            box.setChecked(True)
            box.setToolTip(notes)
            box.stateChanged.connect(self.completeChanged)
            self.boxes[slug] = box
            inner.addWidget(box)
        inner.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

    def isComplete(self) -> bool:
        return any(box.isChecked() for box in self.boxes.values())

    def enabled(self) -> list[str]:
        return [slug for slug, box in self.boxes.items() if box.isChecked()]


class IntegrationsPage(QWizardPage):
    """Optional folders outside the clone that agents read and write."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Connect your folders")
        self.setSubTitle("Both are optional. Leave either empty to skip it.")

        self.notebook = FolderRow("Choose your Markdown notebook folder", clearable=True)
        self.zotero = FolderRow("Choose your Zotero data folder", clearable=True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Markdown notebook — a folder of notes you edit yourself"))
        layout.addWidget(self.notebook)
        layout.addSpacing(10)
        layout.addWidget(QLabel("Zotero data folder — the reference library the librarian reads"))
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
        lines = [
            f"Data folder: {instance_dir}",
            f"Board: {instance_dir / 'tickets' / 'tickets.db'}",
            f"Configuration: {config_local_path(w.root)}",
            f"Pointer: {instance.pointer_path()}",
            f"Agents: {', '.join(w.agents_page.enabled())}",
        ]
        notebook = w.integrations_page.notebook.value()
        zotero = w.integrations_page.zotero.value()
        lines.append(f"Markdown notebook: {notebook or 'skipped'}")
        lines.append(f"Zotero: {zotero or 'skipped'}")
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
        except (OSError, sqlite3.Error, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, "Setup failed", f"{exc.__class__.__name__}: {exc}")
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


def apply_setup(root: Path, instance_dir: Path, slug: str, agents: list[str],
                notebook: str, zotero: str) -> Path:
    """Create the folders, the database, the configuration and the pointer.

    Returns the path of the provisioned board.
    """
    config = build_config(root, instance_dir, slug, agents, notebook, zotero)

    for path in _declared_dirs(root, config, instance_dir):
        path.mkdir(parents=True, exist_ok=True)

    db_path = instance_dir / "tickets" / "tickets.db"
    schema = (Path(__file__).resolve().parent.parent / "schema.sql").read_text(
        encoding="utf-8"
    )
    conn = sqlite3.connect(str(db_path), timeout=10)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        # // A mounted-folder bridge has wedged a database whose rollback journal
        # // was written to disk; MEMORY keeps the journal off the mount.
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()

    config_path = config_file.write(config, config_local_path(root))

    instance.write(root, instance_dir.parent, slug, config_path)
    return db_path


def run_setup(parent=None) -> Path | None:
    """Show the wizard. Returns the provisioned board, or None if cancelled."""
    root = project_root()
    if root is None:
        QMessageBox.critical(
            parent,
            "Bristol Tickets — Setup",
            "Setup needs the Bristol Tickets folder you cloned, and cannot find "
            "it from here. Launch Bristol from inside that folder.",
        )
        return None
    wizard = SetupWizard(root, parent)
    if wizard.exec() != QWizard.Accepted:
        return None
    return wizard.db_path
