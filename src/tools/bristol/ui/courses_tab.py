"""ui/courses_tab.py — the Courses tab: every course, and the one control that
opens one.

Every fact on this page comes from one call to
``src/tools/teaching_assistant/study_server/serve.py --list-json``, the same
program that then serves the pages, so the tab and the server cannot disagree
about which courses exist or where one was left.

Study starts that server as a child process and hands the browser the address it
prints. The lesson is drawn by the browser rather than by Qt: a built bundle
carries no browser engine — ``bristol/slim.py`` — so a page rendered inside the
window would lose the styling the renderer already gave it.

The server outlives no window. It is stopped when the tab is torn down, so
closing Bristol Tickets leaves nothing listening.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local; see module docstring

from .links import open_uri
from .theme import space

SERVE_CLI = Path("src") / "tools" / "teaching_assistant" / "study_server" / "serve.py"

# The address the server prints on its first line of output.
ADDRESS = re.compile(r"https?://[^\s]+")

PAGE_NOTE = (
    "A course opens in your browser, served from your own machine. Where you "
    "stopped is kept with the rest of your records, so the same lesson comes "
    "back on any browser and survives clearing its data.")


class CoursesTab(QWidget):
    """What there is to study, and the control that opens it."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._courses: list[dict] = []
        self._server: QProcess | None = None
        self._base = ""
        self._pending = ""  # the course to open once the server announces itself

        self.note = QLabel(PAGE_NOTE)
        self.note.setObjectName("formCaption")
        self.note.setWordWrap(True)

        self.status = QLabel()
        self.status.setObjectName("formCaption")
        self.status.setWordWrap(True)

        self.list = QListWidget()
        self.list.setObjectName("searchResults")
        self.list.currentItemChanged.connect(lambda *_: self._sync_actions())
        self.list.itemActivated.connect(lambda *_: self._study())

        self.study_btn = QPushButton("Study")
        self.study_btn.setObjectName("globalCreateBtn")
        self.study_btn.setCursor(Qt.PointingHandCursor)
        self.study_btn.clicked.connect(self._study)

        self.stop_btn = QPushButton("Stop serving")
        self.stop_btn.clicked.connect(self._stop)

        actions = QHBoxLayout()
        actions.setSpacing(space("md"))
        actions.addStretch(1)
        actions.addWidget(self.stop_btn)
        actions.addWidget(self.study_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("lg"))
        layout.addWidget(self.note)
        layout.addWidget(self.status)
        layout.addWidget(self.list, 1)
        layout.addLayout(actions)

        self.reload()

    # ----- the listing ------------------------------------------------------

    def _cli(self) -> Path | None:
        root = config_file.project_root()
        if root is None:
            return None
        script = root / SERVE_CLI
        return script if script.is_file() else None

    def reload(self) -> None:
        """Show what the study server currently reports.

        A root that is not declared, not on disk, or holds no rendered course
        all arrive here as the same thing: a message and an empty list.
        """
        self._courses = []
        self.list.clear()
        script = self._cli()
        if script is None:
            self.status.setText(
                "No study server here — this build cannot find "
                "src/tools/teaching_assistant/study_server/serve.py.")
            self._sync_actions()
            return

        done = subprocess.run(
            [sys.executable, str(script), "--list-json"],
            capture_output=True, text=True, cwd=str(script.parents[4]))
        if done.returncode != 0:
            self.status.setText(
                done.stderr.strip() or "The study server found no course.")
            self._sync_actions()
            return
        try:
            self._courses = json.loads(done.stdout).get("courses", [])
        except json.JSONDecodeError:
            self._courses = []
            self.status.setText("The study server answered with nothing readable.")
            self._sync_actions()
            return

        self._fill_list()
        self._say_where()
        self._sync_actions()

    def _fill_list(self) -> None:
        for course in self._courses:
            where = ("last opened lesson %02d" % course["last_opened"]
                     if course["last_opened"] else "not opened yet")
            item = QListWidgetItem(
                "%s — %d lessons · %s"
                % (course["title"], course["lessons"], where))
            item.setData(Qt.UserRole, course["name"])
            self.list.addItem(item)
        if self._courses:
            self.list.setCurrentRow(0)

    def _say_where(self) -> None:
        if not self._courses:
            self.status.setText("No course has rendered output yet.")
        elif self._base:
            self.status.setText("Serving at %s" % self._base)
        else:
            self.status.setText("")

    def _selected(self) -> str:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item is not None else ""

    def _sync_actions(self) -> None:
        self.study_btn.setEnabled(bool(self._selected()))
        self.stop_btn.setEnabled(self._server is not None)

    # ----- the server -------------------------------------------------------

    def _study(self) -> None:
        course = self._selected()
        if not course:
            return
        if self._base:
            self._open(course)
            return
        script = self._cli()
        if script is None:
            return
        self._pending = course
        self._server = QProcess(self)
        self._server.readyReadStandardOutput.connect(self._on_output)
        self._server.finished.connect(self._on_finished)
        self._server.start(sys.executable, [str(script), "--port", "0"])
        self.status.setText("Starting the study server…")
        self._sync_actions()

    def _on_output(self) -> None:
        """The server prints its address as it comes up; that is the signal."""
        if self._server is None:
            return
        text = bytes(self._server.readAllStandardOutput()).decode("utf-8", "replace")
        if self._base:
            return
        found = ADDRESS.search(text)
        if not found:
            return
        base = found.group(0).rstrip("/")
        cut = base.find("/", len("http://"))
        self._base = base[:cut] if cut != -1 else base
        self.status.setText("Serving at %s" % self._base)
        if self._pending:
            self._open(self._pending)
            self._pending = ""

    def _open(self, course: str) -> None:
        """Hand the browser the course's resume address."""
        open_uri("%s/%s/resume" % (self._base, course))

    def _on_finished(self, *_args) -> None:
        self._server = None
        self._base = ""
        self._pending = ""
        self.status.setText("The study server has stopped.")
        self._sync_actions()

    def _stop(self) -> None:
        if self._server is None:
            return
        server, self._server = self._server, None
        server.finished.disconnect()
        server.terminate()
        if not server.waitForFinished(3000):
            server.kill()
        self._base = ""
        self._pending = ""
        self._say_where()
        self._sync_actions()

    # ----- teardown ---------------------------------------------------------

    def shutdown(self) -> None:
        """Stop the server. The window calls this on its way out, so no child
        process outlives the application that started it."""
        self._stop()
