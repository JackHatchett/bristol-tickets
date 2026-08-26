#!/usr/bin/env python3
"""
create_tickets.py — provision a fully robust tickets.db identical to the UI's schema.

This script:
    - Creates data/<instance>/tickets/tickets.db
    - Ensures the DB schema matches the UI's auto-migrated schema
    - Throws an error if the DB already exists
    - Uses ONLY relative project structure under the project root
    - Contains NO personal data, NO usernames, NO environment variables

It is also the home of the two functions the other ticket tools call when they
find no database at all: `provision()` applies the schema to an empty file, and
`locate_or_provision()` finds the one shared tickets.db or makes it.

Usage:
    python3 create_tickets.py --instance <name>
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "config_tools")
)
import data_paths  # noqa: E402  (the shared declared-path resolver)


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

# An epic's status, in the one vocabulary Bristol Tickets writes. The two
# frozensets carry the spellings retired versions wrote, so a reader classifies
# every row in a long-lived database without a second lookup table.
EPIC_STATUS_CHOICES = ("not started", "in progress", "completed", "on hold")
EPIC_STATUS_FINISHED = frozenset({"completed", "done"})
EPIC_STATUS_IN_FLIGHT = frozenset({"in progress", "active"})

# What kind of thing has stopped a card, in the one vocabulary every writer uses.
# A dependency names no card here — the 'blocks' link does that, and the status
# scripts resolve it live. The two that the user alone can clear are named
# separately, because that is what the status scripts surface.
# Mirrored in bristol/ui/record_dialog.py, which carries its own copy so the
# viewer depends on no package outside itself.
BLOCK_REASONS = ("dependency", "decision", "capability", "transient")
BLOCK_REASONS_NEEDING_USER = frozenset({"decision", "capability"})


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
    pressure    INTEGER NOT NULL DEFAULT 0,      -- 0-100 gestalt: how hard this card is pushing. A rating, not a rank; sort_order is the rank.
    estimate    TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now')),
    closed_at   TEXT,
    assignee    TEXT,
    reporter    TEXT,
    story_points INTEGER DEFAULT 0,
    record_type TEXT NOT NULL DEFAULT 'build',     -- 'build' (Story + acceptance criteria) | 'fix' (Expected/Observed).
    stage       TEXT NOT NULL DEFAULT 'backlog',   -- backlog | active | archive (which tab; orthogonal to status).
    sort_order  INTEGER NOT NULL DEFAULT 0,        -- manual drag-to-reorder position; lower = higher in its list.
    block_reason TEXT,                             -- NULL | dependency | decision | capability | transient. What kind of thing has stopped the card, never which card: a dependency resolves live from the 'blocks' links.
    FOREIGN KEY (epic_id)    REFERENCES epic  (id),
    FOREIGN KEY (scope_id)   REFERENCES scope (id)
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
-- the board. Carry-forward is a `doing` card with an owner and a pressure.)


-- task_event — the mechanical change log: one row per changed task field,
-- holding the field, its new value, the actor and an ISO timestamp. Written by
-- triggers in each writing connection's TEMP schema, in a fixed grammar, so no
-- agent or person ever composes an entry. Title and description changes record
-- only that they changed. Read by the Bristol Tickets Log pane, alongside
-- issue_log comments, and by the reports package (bristol/reports/).
CREATE TABLE IF NOT EXISTS task_event (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL,
    at         TEXT    NOT NULL,          -- ISO-8601 UTC
    actor      TEXT,                      -- 'user' (Bristol Tickets) or an agent write signature
    field      TEXT    NOT NULL,          -- the task column that changed
    from_value TEXT,                      -- NULL = card came into being here
    to_value   TEXT    NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task (id)
);
CREATE INDEX IF NOT EXISTS idx_task_event_task ON task_event (task_id, at);

-- attachment — image files pinned to a task from the viewer's comment poster.
-- The row stores only the filename; the bytes live in a per-instance images/
-- dir next to the DB, so no personal path is ever written here.
CREATE TABLE IF NOT EXISTS attachment (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id       INTEGER NOT NULL,
    filename      TEXT    NOT NULL,
    original_name TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES task (id)
);

-- task_link — a ticket's relations: to another ticket (kind='issue') or to an
-- external address (kind='uri': a web URL, a zotero:// citation, an
-- obsidian:// note, or a bare file path).
--
-- An issue link carries a dep_type: 'related' (the default) or 'blocks'.
-- A 'related' row is ONE symmetric edge, normalized to task_id=MIN(a,b) /
-- other_id=MAX(a,b), so it reads from either end and deletes once. A 'blocks'
-- row is the same single edge carrying a direction: task_id blocks other_id,
-- which renders as "blocks #other" on one card and "blocked by #task" on the
-- other. Direction lives on the row; there is never a mirror record.
CREATE TABLE IF NOT EXISTS task_link (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT    NOT NULL,
    task_id    INTEGER NOT NULL,
    other_id   INTEGER,
    dep_type   TEXT    NOT NULL DEFAULT 'related',   -- issue links only: related | blocks
    uri        TEXT,
    label      TEXT,
    author     TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id)  REFERENCES task (id),
    FOREIGN KEY (other_id) REFERENCES task (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_link_pair
    ON task_link (task_id, other_id) WHERE kind = 'issue';
CREATE INDEX IF NOT EXISTS idx_task_link_task  ON task_link (task_id);
CREATE INDEX IF NOT EXISTS idx_task_link_other ON task_link (other_id);
"""


# ---------------------------------------------------------------------------
# PROVISIONING (schema only — the shape every reader of this DB relies on)
# ---------------------------------------------------------------------------

def provision(db_path: Path) -> Path:
    """Apply SCHEMA to `db_path`, creating the file and its folder if absent.

    This is what the ticket tools call when they find no database: an agent on
    a fresh clone gets an empty board rather than a missing-path error. The
    board is created empty — a sample record is invented content, not
    provisioning (`src/templates/identity_template.md` §Data locations).

    Idempotent: every statement is IF NOT EXISTS, so running it against a live
    database adds only what is missing.
    """
    return data_paths.ensure_db(db_path, SCHEMA)


def locate_or_provision() -> Path:
    """The one shared tickets.db, created on first use if it is not there yet.

    Discovery is data_root/*/tickets/tickets.db, the same glob every reader has
    always used. When nothing matches — a fresh clone, or a data root the user
    has just pointed somewhere new — the database is provisioned empty at
    data_root/<instance>/tickets/tickets.db instead of the caller exiting with a
    missing-path error.
    """
    root = data_paths.data_root()
    matches = sorted(root.glob("*/tickets/tickets.db"))
    if matches:
        return matches[0]
    return provision(root / data_paths.instance_slug() / "tickets" / "tickets.db")


# ---------------------------------------------------------------------------
# MIGRATION (bring a live DB up to the schema above; idempotent)
# ---------------------------------------------------------------------------

def migrate(conn: sqlite3.Connection) -> None:
    """Apply the schema changes an existing database is missing.

    Every step is idempotent and non-destructive to content, so this is safe to
    run on every connection. Bristol Tickets carries its own copy in
    ui/schema_guard.py — the two clients each hold their own DB logic so
    neither package depends on the other.
    """
    _ensure_link_dep_type(conn)
    _ensure_block_reason(conn)
    _retire_blocked_columns(conn)
    conn.commit()


def _ensure_link_dep_type(conn: sqlite3.Connection) -> None:
    """Add task_link.dep_type to a DB that predates typed links. Existing rows
    default to 'related', which is what every link written before the type
    existed meant."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(task_link)").fetchall()]
    if cols and "dep_type" not in cols:
        conn.execute(
            "ALTER TABLE task_link ADD COLUMN dep_type TEXT NOT NULL DEFAULT 'related'"
        )


def _ensure_block_reason(conn: sqlite3.Connection) -> None:
    """Add task.block_reason to a DB that predates it. A card written before the
    column existed is not blocked, which is what NULL means, so nothing is
    backfilled.

    This is not a return of task.blocked: that column named the blocking card
    and was retired into a link. This one names the KIND of thing in the way —
    dependency, decision, capability, transient — and a dependency still
    resolves live from the links.
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(task)").fetchall()]
    if cols and "block_reason" not in cols:
        conn.execute("ALTER TABLE task ADD COLUMN block_reason TEXT")


def _retire_blocked_columns(conn: sqlite3.Connection) -> None:
    """Fold task.blocked / task.depends_on into 'blocks' links, then drop them.

    There is one dependency mechanism: a typed link. The old pair of columns
    could only say "this card depends on that one" once per card, was set by
    hand and never cleared, and had to be trusted against the depended-on
    ticket's real status. Each row that named a dependency becomes the link that
    says the same thing, and the columns go.

    // ALTER TABLE ... DROP COLUMN needs SQLite 3.35; on an older library the
    // drop is skipped and the columns are left in place at their defaults,
    // unread and unwritten by anything.
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(task)").fetchall()]
    if "depends_on" not in cols and "blocked" not in cols:
        return

    if "depends_on" in cols:
        pairs = conn.execute(
            "SELECT id, depends_on FROM task WHERE depends_on IS NOT NULL"
        ).fetchall()
        for task_id, blocker_id in pairs:
            if conn.execute("SELECT 1 FROM task WHERE id=?", (blocker_id,)).fetchone() is None:
                continue
            row = conn.execute(
                "SELECT id FROM task_link WHERE kind='issue' AND "
                "((task_id=? AND other_id=?) OR (task_id=? AND other_id=?))",
                (blocker_id, task_id, task_id, blocker_id),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE task_link SET dep_type='blocks', task_id=?, other_id=? "
                    "WHERE id=?",
                    (blocker_id, task_id, row[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO task_link (kind, task_id, other_id, dep_type, author) "
                    "VALUES ('issue',?,?,'blocks','migration')",
                    (blocker_id, task_id),
                )
    conn.commit()

    for column, neutral in (("blocked", "0"), ("depends_on", "NULL")):
        if column not in cols:
            continue
        try:
            conn.execute(f"ALTER TABLE task DROP COLUMN {column}")
        except sqlite3.OperationalError:
            conn.execute(f"UPDATE task SET {column} = {neutral}")


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

    conn.close()

    print("Done. Launch agent with:")
    print(f"  python3 <agent entrypoint>  # DB auto-discovered via relative structure")


if __name__ == "__main__":
    main()
