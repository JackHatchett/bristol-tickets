#!/usr/bin/env python3
"""
create_tickets.py — provision a fully robust tickets.db identical to the UI's schema.

This script:
    - Creates data/<instance>/tickets/tickets.db
    - Ensures the DB schema matches the UI's auto-migrated schema
    - Seeds the DB with a default epic + default tasks
    - Throws an error if the DB already exists
    - Uses ONLY relative project structure under the project root
    - Contains NO personal data, NO usernames, NO environment variables

Usage:
    python3 create_tickets.py --instance <name>
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone



def _project_root() -> Path:
    """The project root: the nearest ancestor holding src/app.md.

    Located by marker rather than by folder name, so the install works whatever
    the user named the folder they cloned into.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "app.md").is_file():
            return parent
    raise SystemExit(
        "no project root above this file (no ancestor holds src/app.md)"
    )


# ---------------------------------------------------------------------------
# DB PATH RESOLUTION (canonical)
# ---------------------------------------------------------------------------

def resolve_output_path(instance: str) -> Path:
    """
    Create:
        data/<instance>/tickets/tickets.db
    """
    data_root = _project_root() / "data"

    instance_dir = data_root / instance
    tickets_dir = instance_dir / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)

    return tickets_dir / "tickets.db"


# ---------------------------------------------------------------------------
# SCHEMA — fully robust, matching UI auto-migrations
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS theme (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    description    TEXT,
    is_milestone   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS epic (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_id           INTEGER,
    name               TEXT NOT NULL,
    type               TEXT,
    status             TEXT NOT NULL DEFAULT 'not started',
    owner              TEXT,
    approver           TEXT,
    description        TEXT,
    hard_constraints   TEXT,
    definition_of_done TEXT,
    detail_path        TEXT,
    next_action        TEXT,
    created_at         TEXT DEFAULT (datetime('now')),
    closed_at          TEXT,
    FOREIGN KEY (theme_id) REFERENCES theme (id)
);

CREATE TABLE IF NOT EXISTS scope (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_id     INTEGER NOT NULL,
    version     TEXT NOT NULL,
    label       TEXT,
    description TEXT,
    FOREIGN KEY (epic_id) REFERENCES epic (id)
);

-- (The board is full-Kanban: a task's tab is task.stage, its manual order is
-- task.sort_order. No sprint or sprint_task table is provisioned.)

CREATE TABLE IF NOT EXISTS task (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_id     INTEGER,
    scope_id    INTEGER,
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'todo',      -- todo | doing | done (board columns)
    priority    INTEGER NOT NULL DEFAULT 0,
    estimate    TEXT,
    blocked     INTEGER NOT NULL DEFAULT 0,
    depends_on  INTEGER,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now')),
    closed_at   TEXT,
    assignee    TEXT,
    reporter    TEXT,
    story_points INTEGER DEFAULT 0,
    record_type TEXT NOT NULL DEFAULT 'build',     -- 'build' (Story + acceptance criteria) | 'fix' (Expected/Observed).
    stage       TEXT NOT NULL DEFAULT 'backlog',   -- backlog | active | archive (which tab; orthogonal to status).
    sort_order  INTEGER NOT NULL DEFAULT 0,        -- manual drag-to-reorder position; lower = higher in its list.
    FOREIGN KEY (epic_id)    REFERENCES epic  (id),
    FOREIGN KEY (scope_id)   REFERENCES scope (id),
    FOREIGN KEY (depends_on) REFERENCES task  (id)
);

CREATE TABLE IF NOT EXISTS task_meta (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id      INTEGER NOT NULL,
    issue_type   TEXT,
    assignee     TEXT,
    reporter     TEXT,
    labels       TEXT,
    story_points INTEGER,
    due_date     TEXT,
    FOREIGN KEY (task_id) REFERENCES task (id)
);

CREATE TABLE IF NOT EXISTS issue_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL,
    author     TEXT NOT NULL,             -- agent slug, or 'user' / 'system'
    body       TEXT NOT NULL,             -- one brief progress note
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES task (id)
);

-- (There is no `handoff` table. A per-agent "where things stand" note is work
-- state living outside the cards; being inside this DB never made it part of
-- the board. Carry-forward is a `doing` card with an owner and a priority.)


-- task_event — the mechanical change log: one row per changed task field,
-- holding the field, its new value, the actor and an ISO timestamp. Written by
-- triggers in each writing connection's TEMP schema, in a fixed grammar, so no
-- agent or person ever composes an entry. Title and description changes record
-- only that they changed. Read by Bristol's Log pane, alongside issue_log
-- comments, and by the reports package (bristol/reports/).
CREATE TABLE IF NOT EXISTS task_event (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL,
    at         TEXT    NOT NULL,          -- ISO-8601 UTC
    actor      TEXT,                      -- 'user' (Bristol) or an agent write signature
    field      TEXT    NOT NULL,          -- the task column that changed
    from_value TEXT,                      -- NULL = card came into being here
    to_value   TEXT    NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task (id)
);
CREATE INDEX IF NOT EXISTS idx_task_event_task ON task_event (task_id, at);
"""


# ---------------------------------------------------------------------------
# SEEDING
# ---------------------------------------------------------------------------

# Seed tasks land in the Backlog stage (status 'todo'); sort_order is assigned
# sequentially below so they keep this listed order in the Backlog tab.
DEFAULT_TASKS = [
    ("Define agent purpose and scope", "Write a clear one-paragraph statement.", 80),
    ("Create agent loader", "Scaffold CLAUDE.md with load order.", 70),
    ("Create charter", "Draft identity, authority, mandate.", 60),
    ("Set up data store", "Create state and ticket stubs.", 50),
    ("Register agent", "Add entry to global registry.", 40),
]


def seed_db(conn: sqlite3.Connection, instance: str) -> None:
    now = datetime.now(timezone.utc).isoformat()

    cur = conn.execute(
        "INSERT INTO epic (name, type, status, owner, description, next_action) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            f"{instance} — initial setup",
            "Epic (bounded)",
            "not started",
            instance,
            f"Bootstrap work to get the {instance} agent operational.",
            "Define agent purpose and scope.",
        ),
    )
    epic_id = cur.lastrowid

    conn.execute(
        "INSERT INTO scope (epic_id, version, label, description) VALUES (?,?,?,?)",
        (epic_id, "v1", "bootstrap", "Initial provisioning tasks."),
    )

    for order_idx, (title, desc, priority) in enumerate(DEFAULT_TASKS):
        cur2 = conn.execute(
            "INSERT INTO task (epic_id, title, description, status, stage, sort_order, priority) "
            "VALUES (?,?,?,?,?,?,?)",
            (epic_id, title, desc, "todo", "backlog", order_idx, priority),
        )
        conn.execute(
            "INSERT INTO issue_log (task_id, author, body, created_at) VALUES (?,?,?,?)",
            (cur2.lastrowid, "system", "created by create_tickets.py", now),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    if "--instance" not in sys.argv:
        sys.exit("Usage: create_tickets.py --instance <name>")

    try:
        instance = sys.argv[sys.argv.index("--instance") + 1].strip()
    except Exception:
        sys.exit("create_tickets: missing instance name")

    db_path = resolve_output_path(instance)

    if db_path.exists():
        sys.exit(f"create_tickets: ERROR — DB already exists at {db_path}")

    print(f"Provisioning tickets DB for instance '{instance}'")
    print(f"  DB path: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    print("  Schema applied.")

    seed_db(conn, instance)
    conn.close()

    print("Done. Launch agent with:")
    print(f"  python3 <agent entrypoint>  # DB auto-discovered via relative structure")


if __name__ == "__main__":
    main()
