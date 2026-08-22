"""ui/setup_wizard.py — first-run setup, so a download or a fresh clone opens
into a board.

A downloaded ``.app`` carries the project tree inside it and has no clone to
sit above, so setup opens by asking where Bristol should live and putting it
there (``payload.py``). A run from source already has that folder and skips
the question.

Bristol Tickets imports nothing from the rest of ``src/tools``: this module
uses PySide6, the standard library, and the sibling ``instance`` module. The
database it provisions comes from ``bristol/schema.sql`` — the same generated
snapshot ``app.py`` applies on every launch — and the configuration it writes is
``config/config.example.json`` with this installation's answers substituted in.

The first page opens on the installation this machine already has — the one
``config/config.local.json`` declares, and failing that the one the instance
pointer names. Only a machine with neither opens on the operating system's user
name.

A data folder that already holds ``tickets/tickets.db`` is adopted instead:
no schema runs against that board, its configuration is left as it stands, and
the only file written is the instance pointer.

Whether it creates or adopts, the run writes the pointer only when the summary
page says to, so an installation can be set up without taking over which one
the app opens.

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
from PySide6.QtGui import QColor, QPalette, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

import config_file  # bristol-local; see module docstring
import instance
import payload

from .dialogs import ORDINARY, PRIMARY, choose, confirm, notify
from .theme import C, LAYOUT, space, type_size


def page_title(text: str) -> str:
    """A page title at the app's section size. The wizard reads its titles as
    rich text, so the type scale reaches them the same way it reaches every
    other heading."""
    return f'<span style="font-size: {type_size("section")}pt;">{text}</span>'


def page_layout(page: QWidget) -> QVBoxLayout:
    """A wizard page's column, on the app's margins and spacing so a page reads
    as the same application as the board behind it."""
    layout = QVBoxLayout(page)
    layout.setContentsMargins(space("xl"), space("lg"), space("xl"), space("lg"))
    layout.setSpacing(space("lg"))
    return layout

SLUG_PATTERN = r"[a-z0-9][a-z0-9_-]*"
REQUIRED_AGENT = "chief_of_staff"
INSTANCE_TOKEN = "<your-instance>"
PROJECT_TOKEN = "/path/to/project"
NOTEBOOK_TOKEN = "/path/to/notebook"
ZOTERO_TOKEN = "/path/to/Zotero"
HOME_TOKEN = "/path/to/your/home"

PAGE_INSTANCE, PAGE_AGENTS, PAGE_INTEGRATIONS, PAGE_SUMMARY = range(4)


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

project_root = config_file.project_root


def config_local_path(root: Path) -> Path:
    return root / "config" / "config.local.json"


def board_path(instance_dir: Path) -> Path:
    return instance_dir / "tickets" / "tickets.db"


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
        choose_btn = QPushButton("Choose…")
        choose_btn.clicked.connect(self._choose)
        row.addWidget(self.field, 1)
        row.addWidget(choose_btn)
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


def configured_instance_dir(root: Path) -> Path | None:
    """The installation folder ``config.local.json`` declares, or None.

    ``important_paths.tickets_db`` names the board, so its grandparent is the
    installation folder. A relative declaration is read against the clone.
    """
    declared = config_file.get("important_paths.tickets_db")
    if not isinstance(declared, str) or not declared.strip():
        return None
    board = Path(declared.strip()).expanduser()
    if not board.is_absolute():
        board = root / board
    parents = board.parents
    return parents[1] if len(parents) > 1 else None


def pointed_instance_dir() -> Path | None:
    """The installation folder the instance pointer names, or None."""
    pointer = instance.read()
    slug = str(pointer.get("instance_slug") or "").strip()
    data_root = str(pointer.get("data_root") or "").strip()
    if not slug or not data_root:
        return None
    return Path(data_root).expanduser() / slug


def existing_installation(root: Path) -> tuple[Path | None, Path | None]:
    """The installation this machine is already set up with, from both sources.

    Returns what the configuration declares and what the pointer names, either
    of which may be absent. The configuration is the installation; the pointer
    only says which one the app opens, so a caller that needs one value takes
    the configured one first.
    """
    return configured_instance_dir(root), pointed_instance_dir()


class InstancePage(QWizardPage):
    """The installation's name, and the folder its data lives in."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.setTitle(page_title("Name this installation"))
        self.setSubTitle(
            "This name labels the folder holding your board and everything you "
            "save. Lower case, no spaces."
        )

        configured, pointed = existing_installation(root)
        existing = configured or pointed
        # The folder a name change moves the installation within: the parent of
        # whatever is already set up, and otherwise the clone's own data folder.
        self.base = existing.parent if existing is not None else root / "data"
        opening_slug = existing.name if existing is not None else default_slug()

        self.slug_edit = QLineEdit(opening_slug)
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

        self.disagreement = QLabel(self._disagreement_text(configured, pointed))
        self.disagreement.setWordWrap(True)
        self.disagreement.setVisible(bool(self.disagreement.text()))

        self.folder = FolderRow("Choose where this installation's data lives")
        self.folder.set_value(str(self.base / opening_slug))
        self.folder.field.textChanged.connect(self.completeChanged)

        layout = page_layout(self)
        layout.addWidget(QLabel("Installation name"))
        layout.addWidget(self.slug_edit)
        layout.addWidget(self.rejected_hint)
        layout.addSpacing(10)
        layout.addWidget(QLabel("Data folder"))
        layout.addWidget(self.folder)
        layout.addWidget(self.disagreement)
        layout.addStretch(1)

    @staticmethod
    def _disagreement_text(configured: Path | None, pointed: Path | None) -> str:
        """What to say when the configuration and the pointer name different
        installations. Empty when they agree or when either is absent."""
        if configured is None or pointed is None or configured == pointed:
            return ""
        return (
            f"Your configuration names {configured} and the app is currently "
            f"opening {pointed}. The configured one is filled in above; choose "
            f"the other here if it is the one you meant."
        )

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
            self.folder.set_value(str(self.base / slug))
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

    def adopting(self) -> bool:
        """True when the chosen folder already holds a board."""
        return board_path(self.instance_dir()).exists()

    def nextId(self) -> int:
        """Adoption asks nothing more than the summary; creation asks the rest."""
        return PAGE_SUMMARY if self.adopting() else PAGE_AGENTS

    def validatePage(self) -> bool:
        """Say the folder holds an installation, and offer to adopt it."""
        if not self.adopting():
            return True
        return bool(choose(
            self, "This folder already holds an installation",
            f"{self.instance_dir()} already holds a board:\n\n"
            f"{board_path(self.instance_dir())}\n\n"
            "Setup can adopt it. Nothing inside it is read or changed, no "
            "schema runs against that board, and its configuration is left as "
            "it stands.",
            [("Choose another folder", ORDINARY, False),
             ("Adopt it", PRIMARY, True)],
            default_index=1,
        ))


class AgentsPage(QWizardPage):
    """Which of the shipped agents this installation runs."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.setTitle(page_title("Choose your agents"))
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
        layout = page_layout(self)
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
        self.setTitle(page_title("Link your notes and library"))
        self.setSubTitle("Both are optional. Leave either empty to skip it.")

        self.notebook = FolderRow("Choose your Markdown notebook folder", clearable=True)
        self.zotero = FolderRow("Choose your Zotero data folder", clearable=True)

        zotero_label = QLabel(
            "Zotero data folder — your reference library. Skip this if you do "
            "not use Zotero."
        )
        zotero_label.setWordWrap(True)

        layout = page_layout(self)
        layout.addWidget(QLabel("Markdown notebook — a folder of notes you edit yourself"))
        layout.addWidget(self.notebook)
        layout.addSpacing(10)
        layout.addWidget(zotero_label)
        layout.addWidget(self.zotero)
        layout.addStretch(1)


class SummaryPage(QWizardPage):
    """What Finish will write, and which installation the app opens after it."""

    def __init__(self, wizard: "SetupWizard") -> None:
        super().__init__()
        self._wizard = wizard
        self.setTitle(page_title("Ready to set up"))
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.take_over = QCheckBox("Open this installation when Bristol Tickets starts")
        self.take_over.setChecked(True)
        self.take_over.stateChanged.connect(self._render)
        self.pointer_note = QLabel()
        self.pointer_note.setWordWrap(True)
        self.pointer_note.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout = page_layout(self)
        layout.addWidget(self.body)
        layout.addSpacing(12)
        layout.addWidget(self.take_over)
        layout.addWidget(self.pointer_note)
        layout.addStretch(1)

    def initializePage(self) -> None:
        self._render()

    def _render(self) -> None:
        w = self._wizard
        instance_dir = w.instance_page.instance_dir()
        slug = w.instance_page.slug_edit.text().strip()
        taking_over = self.take_over.isChecked()

        if w.instance_page.adopting():
            self.setSubTitle(
                "This installation already exists. Nothing in it is changed."
            )
            lines = [
                f"Installation: {slug}",
                f"Data folder: {instance_dir}",
                f"Board: {board_path(instance_dir)} — already there, and left "
                f"as it is",
                f"Configuration: {config_local_path(w.root)} — left as it "
                f"stands",
                "",
                "The only file Finish writes is the pointer below."
                if taking_over else
                "Finish writes nothing: the installation is already set up and "
                "the pointer is being left alone.",
            ]
        else:
            notebook = w.integrations_page.notebook.value()
            zotero = w.integrations_page.zotero.value()
            self.setSubTitle("Nothing has been written yet. Finish creates the following.")
            lines = [
                f"Data folder: {instance_dir}",
                f"Board: {board_path(instance_dir)}",
                f"Configuration: {config_local_path(w.root)}",
                f"Agents: {', '.join(w.agents_page.enabled())}",
                f"Markdown notebook: {notebook or 'skipped'}",
                f"Zotero: {zotero or 'skipped'}",
                "",
                "Finish creates those folders, provisions the board and writes "
                "the configuration. Cancel writes nothing.",
            ]
        self.body.setText("\n".join(lines))
        self.pointer_note.setText("\n".join(self._pointer_lines(slug, instance_dir,
                                                                taking_over)))

    def _pointer_lines(self, slug: str, instance_dir: Path,
                       taking_over: bool) -> list[str]:
        """Which installation the app opens afterwards, and which it stops opening.

        Both sides are named as an installation folder, the same shape the
        pointer's ``data_root`` and ``instance_slug`` resolve to together, so
        the reader compares two paths of one kind.
        """
        current_slug = str(instance.read().get("instance_slug") or "").strip()
        current_dir = pointed_instance_dir()
        current_name = (f"{current_slug} ({current_dir})" if current_dir
                        else current_slug)
        same = current_dir is not None and current_dir == instance_dir

        if taking_over:
            if same:
                head = (f"Bristol Tickets already opens {current_name}, and "
                        f"goes on opening it.")
            elif not current_slug:
                head = f"Bristol Tickets opens {slug} ({instance_dir}) from now on."
            else:
                head = (f"Bristol Tickets opens {current_name} today. After "
                        f"Finish it opens {slug} ({instance_dir}) instead, and "
                        f"stops opening {current_name}.")
            return [head, f"Written to: {instance.pointer_path()}"]

        if same:
            return [
                f"Bristol Tickets goes on opening {current_name}, which is this "
                f"installation.",
                f"Left as it is: {instance.pointer_path()}",
            ]
        if current_slug:
            return [
                f"Bristol Tickets goes on opening {current_name}, and never "
                f"opens {slug} ({instance_dir}) until you run setup again and "
                f"adopt it.",
                f"Left as it is: {instance.pointer_path()}",
            ]
        return [
            f"Bristol Tickets is left with no installation to open, and never "
            f"opens {slug} ({instance_dir}) until you run setup again and adopt "
            f"it.",
            f"Not written: {instance.pointer_path()}",
        ]


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
        self.setTitleFormat(Qt.RichText)
        # // The wizard's header band is painted by the style from the palette's
        # // Base role, which no stylesheet rule reaches.
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor(C["CANVAS"]))
        self.setPalette(palette)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setMinimumSize(LAYOUT["wizard_min_w"], LAYOUT["wizard_min_h"])

        self.instance_page = InstancePage(root)
        self.agents_page = AgentsPage(root)
        self.integrations_page = IntegrationsPage()
        self.summary_page = SummaryPage(self)
        self.setPage(PAGE_INSTANCE, self.instance_page)
        self.setPage(PAGE_AGENTS, self.agents_page)
        self.setPage(PAGE_INTEGRATIONS, self.integrations_page)
        self.setPage(PAGE_SUMMARY, self.summary_page)

        # The button that carries the run forward takes the app's primary rank;
        # the rest keep the ordinary one.
        for role in (QWizard.NextButton, QWizard.FinishButton):
            button = self.button(role)
            if button is not None:
                button.setObjectName("globalCreateBtn")
                # // A stylesheet rule keyed to an object name only reaches a
                # // widget that already existed if its style is re-polished.
                button.style().unpolish(button)
                button.style().polish(button)

    def accept(self) -> None:
        """Write everything, or nothing."""
        instance_dir = self.instance_page.instance_dir()
        slug = self.instance_page.slug_edit.text().strip()
        write_pointer = self.summary_page.take_over.isChecked()

        if self.instance_page.adopting():
            try:
                self.db_path = adopt_setup(
                    root=self.root,
                    instance_dir=instance_dir,
                    slug=slug,
                    write_pointer=write_pointer,
                )
            except SetupStepError as exc:
                self._report(exc)
                return
            super().accept()
            return

        config_path = config_local_path(self.root)
        if config_path.exists():
            if not confirm(
                self, "Replace your configuration",
                f"{config_path} already exists.\n\n"
                f"Finishing setup replaces it with your answers.",
                "Replace it", destructive=True,
            ):
                return

        try:
            self.db_path = apply_setup(
                root=self.root,
                instance_dir=instance_dir,
                slug=slug,
                agents=self.agents_page.enabled(),
                notebook=self.integrations_page.notebook.value(),
                zotero=self.integrations_page.zotero.value(),
                write_pointer=write_pointer,
            )
        except SetupStepError as exc:
            self._report(exc)
            return
        super().accept()

    def _report(self, exc: "SetupStepError") -> None:
        notify(
            self, "Setup failed",
            f"Setup could not {exc.step}.\n\n{exc.remedy}\n\n"
            f"Nothing this run created was left behind.\n\n"
            f"Details: {exc.cause}",
        )


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


def adopt_setup(root: Path, instance_dir: Path, slug: str,
                write_pointer: bool) -> Path:
    """Take on an installation that already exists.

    Writes the instance pointer and nothing else: no folder is created, no
    schema runs against the adopted board, and its configuration is untouched.
    Returns the path of the adopted board.
    """
    if write_pointer:
        with _step("write the instance pointer",
                   "Check that you can write to your user Application Support "
                   "folder."):
            instance.write(root, instance_dir.parent, slug,
                           config_local_path(root))
    return board_path(instance_dir)


def apply_setup(root: Path, instance_dir: Path, slug: str, agents: list[str],
                notebook: str, zotero: str, write_pointer: bool = True) -> Path:
    """Create the folders, the database, the configuration and the pointer.

    Returns the path of the provisioned board.
    """
    with _step("read the shipped configuration template",
               "Check that config/config.example.json is present in your clone "
               "and is valid JSON."):
        config = build_config(root, instance_dir, slug, agents, notebook,
                              zotero)

    created: list[Path] = []
    placed: list[Path] = []
    db_path = board_path(instance_dir)
    try:
        with _step("create your data folders",
                   "Choose a data folder you can write to, then run setup "
                   "again."):
            payload.make_dirs(_declared_dirs(root, config, instance_dir),
                              created)

        with _step("provision the board",
                   "A file at that path may already be open or may not be a "
                   "database. Close the app holding it, or choose another data "
                   "folder."):
            schema_file = payload.schema_path(Path(__file__))
            if schema_file is None:
                raise FileNotFoundError(
                    "schema.sql is missing, so a board cannot be provisioned")
            schema = schema_file.read_text(encoding="utf-8")
            if not db_path.exists():
                placed.append(db_path)
            conn = sqlite3.connect(str(db_path), timeout=10)
            try:
                conn.execute("PRAGMA busy_timeout=5000")
                # // A mounted-folder bridge has wedged a database whose
                # // rollback journal was written to disk; MEMORY keeps it off
                # // the mount.
                conn.execute("PRAGMA journal_mode=MEMORY")
                conn.executescript(schema)
                conn.commit()
            finally:
                conn.close()

        with _step("write your configuration",
                   "Check that you can write to the config/ folder in your "
                   "clone."):
            target = config_local_path(root)
            if not target.exists():
                placed.append(target)
            config_path = config_file.write(config, target)

        if write_pointer:
            with _step("write the instance pointer",
                       "Check that you can write to your user Application "
                       "Support folder."):
                instance.write(root, instance_dir.parent, slug, config_path)
    except SetupStepError:
        payload.unmake(created, placed)
        raise
    return db_path


DEFAULT_HOME_FOLDER = "Bristol"


class PlacementDialog(QDialog):
    """Where the project tree goes, for an app that carries one.

    Asked once, before the wizard, because every page after it reads the folder
    this writes. A folder that already holds a Bristol tree is taken as it
    stands rather than overwritten.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bristol Tickets — Setup")
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["wizard_min_w"])
        self.chosen: Path | None = None
        # Whether this run put the tree there, so an abandoned setup can take
        # it back off a folder that held nothing before.
        self.placed = False

        heading = QLabel("Where should Bristol live?")
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)

        body = QLabel(
            "This folder holds the agents, the board and everything you save. "
            "You will point your AI app at it, so somewhere you can find again "
            "is the right answer — your home folder is fine."
        )
        body.setWordWrap(True)

        self.folder = FolderRow("Choose where Bristol lives")
        self.folder.set_value(str(Path.home() / DEFAULT_HOME_FOLDER))

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        install = QPushButton("Put it here")
        install.setObjectName(PRIMARY)
        install.setDefault(True)
        install.clicked.connect(self._accept)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(install)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("lg"), space("xl"), space("lg"))
        column.setSpacing(space("lg"))
        column.addWidget(heading)
        column.addWidget(body)
        column.addWidget(self.folder)
        column.addStretch(1)
        column.addLayout(row)

    def _accept(self) -> None:
        target = Path(self.folder.value()).expanduser()
        source = payload.bundled()
        if source is None:
            self.reject()
            return
        if payload.installed_at(target):
            self.chosen = target
            self.accept()
            return
        try:
            payload.stage(source, target)
            self.placed = True
        except OSError as exc:
            notify(self, "Setup failed",
                   f"Bristol could not be written to {target}.\n\n"
                   f"Choose a folder you can write to, then try again.\n\n"
                   f"Details: {exc}")
            return
        self.chosen = target
        self.accept()


def place_project(parent=None) -> tuple[Path | None, bool]:
    """The project folder for this run, and whether this run placed it.

    Either the folder around this file, or the one the user picks for a payload
    the app is carrying. The second value is what lets an abandoned run undo a
    placement.
    """
    root = project_root()
    if root is not None:
        return root, False
    if payload.bundled() is None:
        return None, False
    dialog = PlacementDialog(parent)
    if dialog.exec() != QDialog.Accepted:
        return None, False
    return dialog.chosen, dialog.placed


def connect_instructions(root: Path) -> str:
    """The line a user pastes into an agent host that takes project
    instructions, written from the folder name down the way a host that sees
    several folders at once resolves it."""
    return (
        f"Read {root.name}/src/app.md, then the note in "
        f"{root.name}/src/host_notes/ that matches the host you are running "
        f"under.\nagent_override: none"
    )


class ConnectDialog(QDialog):
    """Where the installation went, and how to point an agent at it."""

    def __init__(self, root: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bristol Tickets — Setup")
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["wizard_min_w"])

        heading = QLabel("Bristol is set up")
        heading.setObjectName("dialogHeading")
        heading.setWordWrap(True)

        body = QLabel(
            f"Everything lives in {root}.\n\n"
            "The board works on its own from here. To have an agent work it, "
            "point your AI app at that folder. Most read AGENTS.md or "
            "CLAUDE.md there on their own; one that takes typed project "
            "instructions instead wants this:"
        )
        body.setWordWrap(True)

        self.instructions = QLabel(connect_instructions(root))
        self.instructions.setWordWrap(True)
        self.instructions.setObjectName("formCaption")
        self.instructions.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.copied = QLabel()
        self.copied.setObjectName("formCaption")

        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy)
        done = QPushButton("Open the board")
        done.setObjectName(PRIMARY)
        done.setDefault(True)
        done.clicked.connect(self.accept)

        row = QHBoxLayout()
        row.setSpacing(space("md"))
        row.addWidget(copy_btn)
        row.addWidget(self.copied)
        row.addStretch(1)
        row.addWidget(done)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("lg"), space("xl"), space("lg"))
        column.setSpacing(space("lg"))
        column.addWidget(heading)
        column.addWidget(body)
        column.addWidget(self.instructions)
        column.addStretch(1)
        column.addLayout(row)

    def _copy(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.instructions.text())
        self.copied.setText("Copied.")


def run_setup(parent=None) -> Path | None:
    """Show the wizard. Returns the provisioned board, or None if cancelled."""
    root, placed = place_project(parent)
    if root is None:
        notify(
            parent,
            "Bristol Tickets — Setup",
            "Setup needs the project folder, and cannot find it from here. "
            "Launch Bristol Tickets from inside that folder.",
        )
        return None
    wizard = SetupWizard(root, parent)
    if wizard.exec() != QWizard.Accepted:
        if placed:
            payload.unstage(root)
        return None
    ConnectDialog(root, parent).exec()
    return wizard.db_path
