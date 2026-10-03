"""ui/folders.py — the two windows Settings opens on where things are: the
Markdown notebook and its attached folders, and every other location the
configuration points at.

Both read and write through command-line tools rather than the file itself —
``src/tools/config_tools/notebook.py`` and ``locations.py`` — so a session and
the app change these the same way. A location that is not on disk is marked
where it is listed, and the button that opens its window carries the same mark,
so a folder moved or renamed outside Bristol shows up in Settings and is fixed
there.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local

from . import dialogs
from .theme import LAYOUT, space

NOTEBOOK_CLI = Path("src") / "tools" / "config_tools" / "notebook.py"
LOCATIONS_CLI = Path("src") / "tools" / "config_tools" / "locations.py"
MISSING = "Missing"


def run(script: Path, *args: str) -> tuple[int, str, str]:
    """One config tool command. Returns (code, stdout, stderr)."""
    root = config_file.project_root()
    found = root / script if root is not None else None
    if found is None or not found.is_file():
        return 1, "", f"This build cannot find {script.as_posix()}."
    done = subprocess.run([sys.executable, str(found), *args],
                          capture_output=True, text=True, cwd=str(root))
    return done.returncode, done.stdout, done.stderr


def notebook_state() -> dict:
    code, out, _ = run(NOTEBOOK_CLI, "show", "--json")
    try:
        return json.loads(out) if code == 0 else {}
    except json.JSONDecodeError:
        return {}


def notebook_missing(state: dict | None = None) -> bool:
    """Whether the notebook, or a folder attached to it, is not on disk."""
    state = notebook_state() if state is None else state
    if not state:
        return False
    return not state.get("root_exists") or \
        any(not f["exists"] for f in state.get("folders", []))


def locations() -> list[dict]:
    code, out, _ = run(LOCATIONS_CLI, "list", "--json")
    try:
        return json.loads(out) if code == 0 else []
    except json.JSONDecodeError:
        return []


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("formCaption")
    return label


def _path_label(text: str, missing: bool) -> QLabel:
    label = QLabel(text)
    label.setObjectName("pathRow")
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    label.setProperty("fieldMissing", missing)
    return label


class NotebookDialog(QDialog):
    """The notebook folder, with Change, and the folders attached to it, with
    Add and Remove. The notebook itself can be changed and never removed."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Notebook")
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["dialog_min_w"])
        self.setMinimumHeight(LAYOUT["wizard_min_h"])

        heading = QLabel("Notebook")
        heading.setObjectName("dialogHeading")

        self.root_label = _path_label("", False)
        change = QPushButton("Change…")
        change.clicked.connect(self._change)
        root_row = QHBoxLayout()
        root_row.setSpacing(space("md"))
        root_row.addWidget(self.root_label, 1)
        root_row.addWidget(change)

        self.list = QListWidget()
        self.list.setObjectName("searchResults")
        self.list.currentItemChanged.connect(lambda *_: self._sync())
        self.add_btn = QPushButton("Add…")
        self.add_btn.clicked.connect(self._add)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove)
        folder_actions = QHBoxLayout()
        folder_actions.setSpacing(space("md"))
        folder_actions.addWidget(self.add_btn)
        folder_actions.addWidget(self.remove_btn)
        folder_actions.addStretch(1)

        close = QPushButton("Close")
        close.setObjectName("globalCreateBtn")
        close.clicked.connect(self.accept)
        foot = QHBoxLayout()
        foot.addStretch(1)
        foot.addWidget(close)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("md"))
        column.addWidget(heading)
        column.addSpacing(space("sm"))
        column.addWidget(_caption("Notebook Folder"))
        column.addLayout(root_row)
        column.addSpacing(space("md"))
        column.addWidget(_caption("Attached Folders"))
        column.addWidget(self.list, 1)
        column.addLayout(folder_actions)
        column.addSpacing(space("lg"))
        column.addLayout(foot)
        self.reload()

    def reload(self) -> None:
        state = notebook_state()
        self._state = state
        shown = state.get("root_path") or state.get("root") or "—"
        self.root_label.setText(shown)
        self.root_label.setProperty("fieldMissing", not state.get("root_exists"))
        self.root_label.style().unpolish(self.root_label)
        self.root_label.style().polish(self.root_label)
        self.list.clear()
        for f in state.get("folders", []):
            item = QListWidgetItem(f["folder"] if f["exists"]
                                   else f"{f['folder']}   ·   {MISSING}")
            item.setData(Qt.UserRole, f["folder"])
            self.list.addItem(item)
        self._sync()

    def _sync(self) -> None:
        self.add_btn.setEnabled(bool(self._state.get("root_exists")))
        self.remove_btn.setEnabled(self.list.currentItem() is not None)

    def _say(self, code: int, out: str, err: str, title: str) -> bool:
        if code != 0:
            dialogs.notify(self, title, (err or out).strip() or "Nothing changed.")
            return False
        return True

    def _change(self) -> None:
        picked = QFileDialog.getExistingDirectory(
            self, "Notebook Folder", self._state.get("root_path", ""))
        if not picked or picked == self._state.get("root_path"):
            return
        if self._state.get("folders") and not dialogs.confirm(
                self, "Change Notebook?",
                "Every attached folder is detached, and every agent's "
                "per-folder choices are cleared.", "Change"):
            return
        if self._say(*run(NOTEBOOK_CLI, "repoint", picked), "Not Changed"):
            self.reload()

    def _add(self) -> None:
        picked = QFileDialog.getExistingDirectory(
            self, "Attach a Folder", self._state.get("root_path", ""))
        if not picked:
            return
        if self._say(*run(NOTEBOOK_CLI, "attach", picked), "Not Attached"):
            self.reload()

    def _remove(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        folder = item.data(Qt.UserRole)
        if not dialogs.confirm(
                self, "Detach This Folder?",
                f"{folder} leaves the notebook Bristol knows, and every agent's "
                f"choice for it is dropped. Nothing on disk is touched.",
                "Detach"):
            return
        if self._say(*run(NOTEBOOK_CLI, "detach", folder), "Not Detached"):
            self.reload()


class LocationsDialog(QDialog):
    """Every other folder and file the configuration points at, grouped by
    where it is set, each with Change and a mark where it is not on disk."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Locations")
        self.setModal(True)
        self.setMinimumWidth(LAYOUT["agent_dialog_min_w"])
        self.setMinimumHeight(LAYOUT["agent_dialog_min_h"])

        heading = QLabel("Locations")
        heading.setObjectName("dialogHeading")

        self.body = QWidget()
        self.rows = QVBoxLayout(self.body)
        self.rows.setContentsMargins(0, 0, space("lg"), 0)
        self.rows.setSpacing(space("sm"))
        scroll = QScrollArea()
        scroll.setObjectName("filterScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.body)

        close = QPushButton("Close")
        close.setObjectName("globalCreateBtn")
        close.clicked.connect(self.accept)
        foot = QHBoxLayout()
        foot.addStretch(1)
        foot.addWidget(close)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("md"))
        column.addWidget(heading)
        column.addWidget(scroll, 1)
        column.addLayout(foot)
        self.reload()

    def reload(self) -> None:
        while self.rows.count():
            child = self.rows.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
        rows = locations()
        # Missing ones first, then by where they are set.
        rows.sort(key=lambda r: (r["exists"], r["label"].lower()))
        group = None
        for row in rows:
            head = MISSING if not row["exists"] else row["label"].split(" › ")[0]
            if head != group:
                group = head
                header = QLabel(head)
                header.setObjectName("sectionHeader")
                header.setContentsMargins(0, space("md"), 0, 0)
                self.rows.addWidget(header)
            self.rows.addWidget(self._row(row))
        self.rows.addStretch(1)

    def _row(self, row: dict) -> QWidget:
        holder = QWidget()
        line = QHBoxLayout(holder)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(space("md"))
        name = QLabel(row["label"].split(" › ", 1)[-1])
        name.setFixedWidth(LAYOUT["palette_caption_w"] + LAYOUT["env_name_w"])
        name.setWordWrap(True)
        line.addWidget(name)
        path = _path_label(row["value"], not row["exists"])
        # A long path is cut at the window's edge rather than widening it; the
        # whole of it is the tooltip.
        path.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        path.setToolTip(row["resolved"])
        line.addWidget(path, 1)
        change = QPushButton("Change…")
        change.clicked.connect(lambda _=False, r=row: self._change(r))
        line.addWidget(change)
        return holder

    def _change(self, row: dict) -> None:
        start = str(Path(row["resolved"]).parent)
        if row["kind"] == "file":
            picked, _ = QFileDialog.getOpenFileName(self, row["label"], start)
        else:
            picked = QFileDialog.getExistingDirectory(self, row["label"], start)
        if not picked:
            return
        code, out, err = run(LOCATIONS_CLI, "set", json.dumps(row["pointer"]),
                             picked)
        if code != 0:
            dialogs.notify(self, "Not Changed", (err or out).strip())
            return
        self.reload()


def any_missing() -> tuple[bool, bool]:
    """(the notebook has something missing, a location is missing)."""
    return notebook_missing(), any(not r["exists"] for r in locations())
