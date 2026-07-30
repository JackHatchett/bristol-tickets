"""ui/links.py — a ticket's links: to another ticket, or to an address.

A **link** is the relation a ticket carries to something else. There are two
kinds and they share one table (`task_link`):

* ``issue`` — a link between two tickets. It is stored as **one symmetric
  edge**: the row is normalized so ``task_id`` is the lower id and ``other_id``
  the higher, and both ends read it with ``WHERE task_id=? OR other_id=?``. So
  the link is bidirectional because of how it is *stored*, not because two rows
  are kept in step — there is no half-link state to drift into, and one delete
  removes it from both tickets at once.

* ``uri`` — a link from a ticket to an address: a web URL, a ``zotero://``
  citation, an ``obsidian://`` note, or a bare filesystem path. Whatever is
  stored is handed to the OS to open, so the tool encodes no scheme list, no
  vault name and no user-specific path. A bare path opens in whatever
  application owns that file type; an ``obsidian://`` URI always opens Obsidian.

Why links exist at all: a ticket Description must stay inside its Build/Fix
template, which left provenance — "this came out of that review", "this relates
to that note" — with nowhere to go, so it was being written into the description
as an off-template Source header. Links are where that belongs.

The widget is ``LinkBar``. It works before a task exists: links added while
*creating* a ticket are buffered in memory and flushed by the caller through
``flush_pending(task_id)`` once the INSERT has produced an id.

Mechanism only — no personal paths, no agent behaviour.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

MAX_LABEL_CHARS = 72  # where a long URI is elided in the one-line row


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Storage (Qt-free; roadmap_write.py mirrors this logic for the CLI)
# ---------------------------------------------------------------------------

def _pair(a: int, b: int) -> tuple[int, int]:
    """Normalize an issue pair so the same link is always the same row."""
    return (a, b) if a <= b else (b, a)


def add_issue_link(conn: sqlite3.Connection, task_id: int, other_id: int,
                   author: str = "user") -> str | None:
    """Link two tickets. Returns None on success, or a message explaining the
    refusal (self-link, missing ticket, already linked)."""
    if task_id == other_id:
        return "A ticket cannot be linked to itself."
    for tid in (task_id, other_id):
        if conn.execute("SELECT 1 FROM task WHERE id=?", (tid,)).fetchone() is None:
            return f"There is no ticket #{tid}."
    lo, hi = _pair(task_id, other_id)
    existing = conn.execute(
        "SELECT 1 FROM task_link WHERE kind='issue' AND task_id=? AND other_id=?",
        (lo, hi),
    ).fetchone()
    if existing:
        return f"#{task_id} and #{other_id} are already linked."
    conn.execute(
        "INSERT INTO task_link (kind, task_id, other_id, author, created_at) "
        "VALUES ('issue',?,?,?,?)",
        (lo, hi, author, _utcnow()),
    )
    conn.commit()
    return None


def add_uri_link(conn: sqlite3.Connection, task_id: int, uri: str,
                 label: str | None = None, author: str = "user") -> str | None:
    """Attach an address to a ticket. Returns None on success, else a message."""
    uri = (uri or "").strip()
    if not uri:
        return "Enter an address to link."
    if conn.execute("SELECT 1 FROM task WHERE id=?", (task_id,)).fetchone() is None:
        return f"There is no ticket #{task_id}."
    conn.execute(
        "INSERT INTO task_link (kind, task_id, uri, label, author, created_at) "
        "VALUES ('uri',?,?,?,?,?)",
        (task_id, uri, (label or "").strip() or None, author, _utcnow()),
    )
    conn.commit()
    return None


def list_links(conn: sqlite3.Connection, task_id: int | None) -> list[dict]:
    """Every link on ``task_id``, issue links first, each flattened to the shape
    the caller renders: ``{id, kind, other_id, other_title, uri, label}``. An
    issue link is returned regardless of which end of the pair this task is."""
    if task_id is None:
        return []
    out: list[dict] = []
    try:
        rows = conn.execute(
            "SELECT l.id, l.task_id, l.other_id, "
            "       ta.title, tb.title "
            "FROM task_link l "
            "LEFT JOIN task ta ON ta.id = l.task_id "
            "LEFT JOIN task tb ON tb.id = l.other_id "
            "WHERE l.kind='issue' AND (l.task_id=? OR l.other_id=?) "
            "ORDER BY l.id",
            (task_id, task_id),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    for link_id, a, b, title_a, title_b in rows:
        far_id, far_title = (b, title_b) if a == task_id else (a, title_a)
        out.append({
            "id": link_id, "kind": "issue", "other_id": far_id,
            "other_title": far_title or "(missing ticket)",
            "uri": None, "label": None,
        })
    try:
        rows = conn.execute(
            "SELECT id, uri, label FROM task_link "
            "WHERE kind='uri' AND task_id=? ORDER BY id",
            (task_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    for link_id, uri, label in rows:
        out.append({
            "id": link_id, "kind": "uri", "other_id": None,
            "other_title": None, "uri": uri, "label": label,
        })
    return out


def remove_link(conn: sqlite3.Connection, link_id: int) -> None:
    """Delete one link. For an issue link this removes it from both tickets,
    since both were reading the same row."""
    conn.execute("DELETE FROM task_link WHERE id=?", (link_id,))
    conn.commit()


def remove_links_for_task(conn: sqlite3.Connection, task_id: int) -> None:
    """Drop every link touching a task — called when the task itself is deleted,
    so no link is left pointing at a ticket that no longer exists."""
    try:
        conn.execute(
            "DELETE FROM task_link WHERE task_id=? OR other_id=?", (task_id, task_id)
        )
    except sqlite3.OperationalError:
        pass


def open_uri(uri: str) -> bool:
    """Hand an address to the OS. A string with a scheme goes as-is (so
    ``zotero://`` reaches Zotero and ``obsidian://`` reaches Obsidian); anything
    else is treated as a filesystem path and opened with whatever application
    owns that file type. Bristol deliberately knows nothing about which app that
    is."""
    url = QUrl(uri)
    if not url.scheme():
        url = QUrl.fromLocalFile(uri)
    return QDesktopServices.openUrl(url)


def _elide(text: str) -> str:
    return text if len(text) <= MAX_LABEL_CHARS else text[: MAX_LABEL_CHARS - 1] + "…"


# ---------------------------------------------------------------------------
# Add-link modal
# ---------------------------------------------------------------------------

class AddLinkDialog(QDialog):
    """A small modal with the two link kinds as mutually exclusive choices, so
    the entry fields cost one button on the screen that hosts them rather than
    two permanent rows. ``result_values()`` returns
    ``(kind, issue_id, uri, label)`` after an accepted exec()."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add link")
        self.setMinimumWidth(420)

        v = QVBoxLayout(self)

        self.issue_radio = QRadioButton("Link to another ticket")
        self.issue_radio.setChecked(True)
        v.addWidget(self.issue_radio)
        issue_row = QHBoxLayout()
        issue_row.addSpacing(22)
        issue_row.addWidget(QLabel("Ticket #"))
        self.issue_input = QLineEdit()
        self.issue_input.setPlaceholderText("153")
        issue_row.addWidget(self.issue_input, 1)
        v.addLayout(issue_row)

        self.uri_radio = QRadioButton("Link to an address")
        v.addWidget(self.uri_radio)
        uri_row = QHBoxLayout()
        uri_row.addSpacing(22)
        uri_row.addWidget(QLabel("Address"))
        self.uri_input = QLineEdit()
        self.uri_input.setPlaceholderText(
            "https://…   zotero://…   obsidian://…   or a file path"
        )
        uri_row.addWidget(self.uri_input, 1)
        v.addLayout(uri_row)
        label_row = QHBoxLayout()
        label_row.addSpacing(22)
        label_row.addWidget(QLabel("Caption"))
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("optional — shown instead of the address")
        label_row.addWidget(self.label_input, 1)
        v.addLayout(label_row)

        hint = QLabel(
            "A path opens in whichever app owns that file type. For a note that "
            "must open in Obsidian, paste its obsidian:// URL."
        )
        hint.setObjectName("metaText")
        hint.setWordWrap(True)
        v.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

        self.issue_radio.toggled.connect(self._sync_enabled)
        # Typing in one kind's field selects that kind, so the radio never
        # silently contradicts where the text went.
        self.issue_input.textEdited.connect(lambda _: self.issue_radio.setChecked(True))
        self.uri_input.textEdited.connect(lambda _: self.uri_radio.setChecked(True))
        self._sync_enabled()

    def _sync_enabled(self, *args) -> None:
        is_issue = self.issue_radio.isChecked()
        self.issue_input.setEnabled(is_issue)
        self.uri_input.setEnabled(not is_issue)
        self.label_input.setEnabled(not is_issue)

    def result_values(self) -> tuple[str, int | None, str, str]:
        if self.issue_radio.isChecked():
            raw = self.issue_input.text().strip().lstrip("#")
            try:
                return ("issue", int(raw), "", "")
            except ValueError:
                return ("issue", None, "", "")
        return ("uri", None, self.uri_input.text().strip(),
                self.label_input.text().strip())


# ---------------------------------------------------------------------------
# Reusable widget — embedded by both the record dialog and the inspector
# ---------------------------------------------------------------------------

class LinkBar(QWidget):
    """An 'Add link' button over one full-width row per link. Issue links render
    as ``#153 — Title`` and select that ticket when clicked; URI links render as
    their caption or address and open via the OS. Each row carries an ✕ that
    confirms before deleting.

    Call ``set_task(task_id)`` to point it at a saved ticket, or
    ``set_task(None)`` while a ticket is still being created — in that mode
    links are buffered and the host flushes them with ``flush_pending(new_id)``
    after the INSERT.

    ``on_open_issue`` is an optional callback taking a ticket id; when set,
    clicking an issue link calls it (the inspector uses this to jump). Without
    it, issue rows are plain text.
    """

    def __init__(self, conn: sqlite3.Connection, parent=None,
                 allow_pending: bool = False, author: str = "user") -> None:
        super().__init__(parent)
        self.conn = conn
        self.task_id: int | None = None
        self.author = author
        self.allow_pending = allow_pending
        self.on_open_issue = None
        # Links entered before the ticket exists: (kind, other_id, uri, label).
        self._pending: list[tuple[str, int | None, str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.header = QLabel("Links")
        self.header.setObjectName("sectionHeader")
        layout.addWidget(self.header)

        self.add_btn = QPushButton("Add link")
        self.add_btn.setToolTip("Link this ticket to another ticket, or to an address")
        self.add_btn.clicked.connect(self._prompt)
        # Sized to its own text rather than stretched across the pane — a
        # full-width button on a tall form wastes the vertical space the form
        # is already short of.
        self.add_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(self.add_btn, 0, Qt.AlignLeft)

        self._list_layout = QVBoxLayout()
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        layout.addLayout(self._list_layout)

    # ----- host API ---------------------------------------------------------

    def set_task(self, task_id: int | None) -> None:
        self.task_id = task_id
        self._pending.clear()
        self.add_btn.setEnabled(task_id is not None or self.allow_pending)
        self._refresh()

    def flush_pending(self, task_id: int) -> None:
        """Write the links buffered during creation against the new ticket id.
        A pending link that has become invalid (the other ticket was deleted in
        the meantime) is dropped silently rather than blocking the save."""
        for kind, other_id, uri, label in self._pending:
            if kind == "issue" and other_id is not None:
                add_issue_link(self.conn, task_id, other_id, self.author)
            elif kind == "uri":
                add_uri_link(self.conn, task_id, uri, label, self.author)
        self._pending.clear()

    def has_pending(self) -> bool:
        return bool(self._pending)

    def pending_signature(self) -> tuple:
        """A comparable snapshot of the buffered links, so a host dialog can
        fold them into its unsaved-changes check. Links added to an already-saved
        ticket commit immediately (like a log post) and are deliberately absent
        here — there is nothing unsaved about them."""
        return tuple(self._pending)

    # ----- add / remove -----------------------------------------------------

    def _prompt(self) -> None:
        dlg = AddLinkDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        kind, issue_id, uri, label = dlg.result_values()

        if kind == "issue":
            if issue_id is None:
                QMessageBox.warning(self, "Add link",
                                    "A ticket link needs a ticket number.")
                return
            if self.task_id is None:
                if issue_id == 0 or self.conn.execute(
                        "SELECT 1 FROM task WHERE id=?", (issue_id,)).fetchone() is None:
                    QMessageBox.warning(self, "Add link", f"There is no ticket #{issue_id}.")
                    return
                self._pending.append(("issue", issue_id, "", ""))
            else:
                problem = add_issue_link(self.conn, self.task_id, issue_id, self.author)
                if problem:
                    QMessageBox.warning(self, "Add link", problem)
                    return
        else:
            if not uri:
                QMessageBox.warning(self, "Add link", "Enter an address to link.")
                return
            if self.task_id is None:
                self._pending.append(("uri", None, uri, label))
            else:
                problem = add_uri_link(self.conn, self.task_id, uri, label, self.author)
                if problem:
                    QMessageBox.warning(self, "Add link", problem)
                    return
        self._refresh()

    def _confirm_remove(self, link_id: int, description: str) -> None:
        if QMessageBox.question(
            self, "Delete link?", f"Remove the link to {description}?"
        ) == QMessageBox.Yes:
            remove_link(self.conn, link_id)
            self._refresh()

    def _confirm_remove_pending(self, index: int, description: str) -> None:
        if QMessageBox.question(
            self, "Delete link?", f"Remove the link to {description}?"
        ) == QMessageBox.Yes:
            if 0 <= index < len(self._pending):
                self._pending.pop(index)
            self._refresh()

    # ----- rendering --------------------------------------------------------

    def _clear_list(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _row(self, text: str, tooltip: str, on_click, on_remove) -> QWidget:
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        if on_click is None:
            body = QLabel(text)
        else:
            body = QPushButton(text)
            body.setObjectName("linkRow")
            body.setFlat(True)
            body.setCursor(Qt.PointingHandCursor)
            body.clicked.connect(lambda _=False: on_click())
        body.setToolTip(tooltip)
        rl.addWidget(body, 1)
        x = QPushButton("X")
        x.setObjectName("attachRemoveBtn")
        x.setFixedWidth(26)
        x.setToolTip("Remove this link")
        x.clicked.connect(lambda _=False: on_remove())
        rl.addWidget(x)
        return row

    def _refresh(self) -> None:
        self._clear_list()

        for link in list_links(self.conn, self.task_id):
            if link["kind"] == "issue":
                other = link["other_id"]
                text = f"#{other} — {_elide(link['other_title'])}"
                click = None
                if callable(self.on_open_issue):
                    click = (lambda o=other: self.on_open_issue(o))
                self._list_layout.addWidget(self._row(
                    text, f"Ticket #{other}", click,
                    (lambda i=link["id"], d=f"#{other}": self._confirm_remove(i, d)),
                ))
            else:
                uri = link["uri"] or ""
                text = _elide(link["label"] or uri)
                self._list_layout.addWidget(self._row(
                    text, uri, (lambda u=uri: open_uri(u)),
                    (lambda i=link["id"], d=_elide(link["label"] or uri):
                     self._confirm_remove(i, d)),
                ))

        for idx, (kind, other_id, uri, label) in enumerate(self._pending):
            text = (f"#{other_id} (on save)" if kind == "issue"
                    else f"{_elide(label or uri)} (on save)")
            desc = f"#{other_id}" if kind == "issue" else _elide(label or uri)
            self._list_layout.addWidget(self._row(
                text, "Written when this ticket is saved", None,
                (lambda i=idx, d=desc: self._confirm_remove_pending(i, d)),
            ))
