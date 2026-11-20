"""smoke_targets/check_ticket_tier.py — the `ticket_tier` smoke target, run by smoke.py."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

from qt_headless import TOOLS
from smoke_targets.failure import SmokeFailure


def check_ticket_tier() -> list[str]:
    """The write CLI carries a card's tier, a board written before the tier
    existed opens through it without losing a card, and the status scripts read
    the tier where pressure used to sit.

    No Qt: the CLI and the status readers are plain sqlite3.
    """

    ok: list[str] = []
    tools = TOOLS / "ticket_tools"
    sys.path.insert(0, str(tools))
    import create_tickets
    import status_common
    import ticket_write

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "tickets.db"
        legacy = sqlite3.connect(db)
        legacy.executescript(
            "CREATE TABLE epic (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, "
            "owner TEXT, status TEXT);"
            "CREATE TABLE task (id INTEGER PRIMARY KEY AUTOINCREMENT, epic_id "
            "INTEGER, scope_id INTEGER, title TEXT NOT NULL, description TEXT, "
            "status TEXT NOT NULL DEFAULT 'todo', pressure INTEGER NOT NULL "
            "DEFAULT 0, estimate TEXT, created_at TEXT, updated_at TEXT, "
            "closed_at TEXT, assignee TEXT, reporter TEXT, story_points INTEGER "
            "DEFAULT 0, record_type TEXT NOT NULL DEFAULT 'build', stage TEXT "
            "NOT NULL DEFAULT 'active', sort_order INTEGER NOT NULL DEFAULT 0);"
            "CREATE TABLE task_link (id INTEGER PRIMARY KEY AUTOINCREMENT, kind "
            "TEXT NOT NULL, task_id INTEGER NOT NULL, other_id INTEGER, uri TEXT, "
            "label TEXT, author TEXT, created_at TEXT);"
            "INSERT INTO task (title, status, pressure, estimate, assignee) "
            "VALUES ('kept', 'doing', 70, 'M', 'chief_of_staff');"
        )
        legacy.commit()
        legacy.close()

        original = ticket_write.resolve_db_path
        ticket_write.resolve_db_path = lambda: db
        argv = sys.argv
        try:

            def run(*args):
                sys.argv = ["ticket_write.py", *args]
                ticket_write.main()

            run(
                "add-task",
                "--title",
                "rated",
                "--tier",
                "max",
                "--estimate",
                "S",
                "--assignee",
                "chief_of_staff",
                "--actor",
                "chief_of_staff",
            )
            conn = sqlite3.connect(db)
            cols = [r[1] for r in conn.execute("PRAGMA table_info(task)")]
            if "pressure" in cols or "tier" not in cols:
                raise SmokeFailure(f"the CLI left a legacy board with {cols}")
            kept = conn.execute(
                "SELECT title, status, estimate, tier FROM task WHERE id=1"
            ).fetchone()
            if kept != ("kept", "doing", "M", None):
                raise SmokeFailure(f"the migration changed a card: {kept}")
            if conn.execute("SELECT tier FROM task WHERE id=2").fetchone()[0] != "max":
                raise SmokeFailure("add-task --tier did not store the tier")
            ok.append(
                "a board carrying pressure opens through the CLI with "
                "every card intact and pressure retired"
            )

            run("update-task", "--id", "1", "--tier", "standard", "--actor", "chief_of_staff")
            if conn.execute("SELECT tier FROM task WHERE id=1").fetchone()[0] != "standard":
                raise SmokeFailure("update-task --tier did not store the tier")
            if not conn.execute(
                "SELECT COUNT(*) FROM task_event WHERE task_id=1 AND field='tier'"
            ).fetchone()[0]:
                raise SmokeFailure("a tier edit was not recorded by the change log")
            run("update-task", "--id", "1", "--tier", "none")
            if conn.execute("SELECT tier FROM task WHERE id=1").fetchone()[0] is not None:
                raise SmokeFailure("update-task --tier none did not clear it")
            ok.append("update-task sets and clears a tier, and the change log records it")

            conn.row_factory = sqlite3.Row
            rows = status_common.board_tasks(conn)
            lines = [status_common.fmt(r, {}) for r in rows]
            if not any(" Max " in line for line in lines) or not any(
                "no tier" in line for line in lines
            ):
                raise SmokeFailure(f"the queue line does not read the tier: {lines}")
            ok.append("the status scripts print a card's tier, and say so when it has none")
            conn.close()
        finally:
            sys.argv = argv
            ticket_write.resolve_db_path = original

        create_tickets.provision(Path(tmp) / "fresh.db")
        fresh = sqlite3.connect(Path(tmp) / "fresh.db")
        cols = [r[1] for r in fresh.execute("PRAGMA table_info(task)")]
        fresh.close()
        if "pressure" in cols or "tier" not in cols:
            raise SmokeFailure(f"a new board is provisioned with {cols}")
        ok.append("a new board is provisioned with tier and without pressure")
    return ok
