"""Fixtures for the unit tests: a board provisioned from Bristol's schema.sql in
a temporary folder, and the write CLI pointed at it.

Nothing here opens the real tickets.db. Every test gets a fresh board, so no
test sees another's cards.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2]
SCHEMA = TOOLS / "bristol" / "schema.sql"

for folder in ("bristol", "ticket_tools", "config_tools", "_shared"):
    path = str(TOOLS / folder)
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """An empty board at tmp_path/tickets.db, built from schema.sql."""
    path = tmp_path / "tickets.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def conn(db_path: Path):
    """An open connection to the temporary board, closed after the test."""
    connection = sqlite3.connect(db_path)
    yield connection
    connection.close()


def add_epic(conn: sqlite3.Connection, name: str, kind: str = "project") -> int:
    """An epic row; `kind` is epic.type."""
    cur = conn.execute(
        "INSERT INTO epic (name, type, status) VALUES (?, ?, 'in progress')", (name, kind)
    )
    conn.commit()
    return int(cur.lastrowid or 0)


def add_card(
    conn: sqlite3.Connection,
    title: str,
    epic_id: int | None = None,
    status: str = "todo",
    stage: str = "active",
    sort_order: int = 0,
    created_at: str = "2026-01-01T00:00:00+00:00",
) -> int:
    """A task row with only the fields the board rules read."""
    cur = conn.execute(
        "INSERT INTO task (epic_id, title, status, stage, sort_order, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (epic_id, title, status, stage, sort_order, created_at),
    )
    conn.commit()
    return int(cur.lastrowid or 0)


def card(conn: sqlite3.Connection, task_id: int) -> dict:
    """One task row as a dict."""
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM task WHERE id=?", (task_id,)).fetchone()
    conn.row_factory = None
    return dict(row)


@pytest.fixture
def cli(db_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Runs ticket_write.py's command line against the temporary board.

    Returns a function taking the arguments after `ticket_write.py`; it raises
    SystemExit where the command refuses, as the script does.
    """
    import ticket_write

    monkeypatch.setattr(ticket_write, "resolve_db_path", lambda: db_path)

    def run(*args: str) -> None:
        monkeypatch.setattr(sys, "argv", ["ticket_write.py", *args])
        ticket_write.main()

    return run
