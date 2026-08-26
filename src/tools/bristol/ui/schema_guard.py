"""ui/schema_guard.py — on-launch, non-destructive schema migration.

The viewer is a read/write client of a database it does not own (the shared
tickets.db). Older databases may predate columns/tables this UI expects, so on
every launch we add only what is missing. This never drops or rewrites data —
it is safe to run against an already-current database (all operations are
idempotent: ADD COLUMN only when absent, CREATE TABLE IF NOT EXISTS).
"""

from __future__ import annotations

import sqlite3


def ensure_schema_up_to_date(conn: sqlite3.Connection) -> None:
    """Safely migrate the DB schema on the fly if new fields are missing."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(task)")
    columns = [row[1] for row in cursor.fetchall()]

    # `priority` is now `pressure` — one 0–100 rating of how much a card is
    # pushing to be done, not a rank. Rank is task.sort_order. The rename is a
    # column rename, so every existing value carries over unchanged.
    if "pressure" not in columns and "priority" in columns:
        conn.execute("ALTER TABLE task RENAME COLUMN priority TO pressure;")
        columns = [c if c != "priority" else "pressure" for c in columns]

    if "assignee" not in columns:
        conn.execute("ALTER TABLE task ADD COLUMN assignee TEXT;")
    if "reporter" not in columns:
        conn.execute("ALTER TABLE task ADD COLUMN reporter TEXT;")
    if "story_points" not in columns:
        conn.execute("ALTER TABLE task ADD COLUMN story_points INTEGER DEFAULT 0;")
    # record_type splits the single ticket concept into two record kinds:
    # 'build' (a thing to build — carries a Story + Given/When/Then acceptance
    # criteria) and 'fix' (a broken thing — carries Expected/Observed). Default
    # 'build' so every pre-existing task is a Build until reclassified; nothing
    # is ever null.
    if "record_type" not in columns:
        conn.execute("ALTER TABLE task ADD COLUMN record_type TEXT NOT NULL DEFAULT 'build';")

    # Kanban model: a task carries TWO orthogonal fields —
    #   * status: todo | doing | done   (the board's columns)
    #   * stage:  backlog | active | archive   (which tab the task lives in)
    # 'backlog' used to be a status value; it is now a stage. sort_order is the
    # manual, drag-to-reorder position within a list (backlog, or a board
    # column); lower sorts higher. See _migrate_stage_from_sprints, which
    # backfills the two new columns from any old sprint membership and then
    # drops the sprint tables.
    if "stage" not in columns:
        conn.execute("ALTER TABLE task ADD COLUMN stage TEXT NOT NULL DEFAULT 'backlog';")
    if "sort_order" not in columns:
        conn.execute("ALTER TABLE task ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;")

    # block_reason names what kind of thing has stopped a card — a dependency,
    # a decision the user owns, a capability that was never granted, or
    # something transient. It never names WHICH card: a dependency resolves live
    # from the 'blocks' links, which is why the old task.blocked / depends_on
    # pair was retired. NULL means nothing is blocking it.
    if "block_reason" not in columns:
        conn.execute("ALTER TABLE task ADD COLUMN block_reason TEXT;")

    _migrate_stage_from_sprints(conn)

    # The `handoff` table is retired. A per-agent "where things stand" note is
    # work state living somewhere other than a card, which is exactly what the
    # board exists to prevent — being stored inside tickets.db never made it
    # part of the board. Carry-forward is now a `doing` card on the active
    # board with a real owner and pressure. Dropped on launch; idempotent.
    _drop_retired_handoff(conn)

    # (Cross-agent suggestions are ordinary active-board cards: task.assignee =
    # target agent and task.reporter = originator, so they live in the board
    # the user watches.
    # No CREATE TABLE here. A leftover inbox table on an old DB is left untouched
    # rather than dropped, since this guard is non-destructive; retiring the live
    # table is a deliberate migration step, not an on-launch side effect.)

    # issue_log — the single, visible, structured per-issue progress log
    # (author + timestamp + body). Both the user (via the viewer's Post
    # button) and agents (via ticket_write.py add-issue-log) append to it.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS issue_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id    INTEGER NOT NULL,
            author     TEXT    NOT NULL,
            body       TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (task_id) REFERENCES task (id)
        );
    """)
    # attachment — image files a user pins to a task from a comment poster.
    # The DB stores only the filename; the bytes live in a per-instance images/
    # dir next to the DB (resolved at runtime — see ui/attachments.py), so no
    # personal path is ever written here.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attachment (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id       INTEGER NOT NULL,
            filename      TEXT    NOT NULL,
            original_name TEXT,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (task_id) REFERENCES task (id)
        );
    """)

    # task_link — a ticket's relations: to another ticket (kind='issue') or to
    # an external address (kind='uri': a web URL, a zotero:// citation, an
    # obsidian:// note, or a bare file path). An issue link is ONE edge that
    # reads from either end and deletes once — bidirectional by storage rather
    # than by two rows a write path has to keep in sync. Its dep_type says what
    # it means: 'related' (normalized to task_id=MIN / other_id=MAX) or 'blocks'
    # (task_id must be done before other_id starts, direction on the row). See
    # ui/links.py.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_link (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            kind       TEXT    NOT NULL,
            task_id    INTEGER NOT NULL,
            other_id   INTEGER,
            dep_type   TEXT    NOT NULL DEFAULT 'related',
            uri        TEXT,
            label      TEXT,
            author     TEXT,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (task_id)  REFERENCES task (id),
            FOREIGN KEY (other_id) REFERENCES task (id)
        );
    """)
    _ensure_link_dep_type(conn)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_task_link_pair "
        "ON task_link (task_id, other_id) WHERE kind = 'issue'"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_link_task ON task_link (task_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_link_other ON task_link (other_id)")

    # task_event — the mechanical change log. One row per changed task field:
    # field, new value, actor, ISO timestamp. Written by database triggers (see
    # install_change_log below), never composed by a human or an agent. Two
    # readers: the inspector's Log, which interleaves these with issue_log
    # comments, and the reports package, which measures cycle time and
    # work-item age from the status/stage rows.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_event (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id    INTEGER NOT NULL,
            at         TEXT    NOT NULL,
            actor      TEXT,
            field      TEXT    NOT NULL,
            from_value TEXT,
            to_value   TEXT    NOT NULL,
            FOREIGN KEY (task_id) REFERENCES task (id)
        );
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_task_event_task ON task_event (task_id, at)"
    )

    _consolidate_legacy_history(conn)
    _retire_blocked_columns(conn)
    install_change_log(conn, actor="user")
    conn.commit()


# ---------------------------------------------------------------------------
# The mechanical change log
# ---------------------------------------------------------------------------

# Fields logged with their new value. A dependency is not among them: it lives
# on a link now, and a link's own history is the row's presence or absence.
CHANGE_LOG_FIELDS = (
    "epic_id", "scope_id", "status", "stage", "pressure", "estimate",
    "assignee", "reporter", "story_points", "record_type", "block_reason",
)

# Fields logged as having changed, without their content. A change log records
# movement, not text; a diff of a Description would turn the log into a second
# copy of the ticket.
CHANGE_LOG_REDACTED_FIELDS = ("title", "description")

# Not logged: sort_order (a rendering position, and every column move already
# re-seats it), closed_at (mechanically implied by status), created_at, and
# updated_at (derived from this log).

_NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%f000+00:00','now')"


def _change_log_sql(actor: str) -> str:
    """The two triggers that write the change log, with `actor` baked in.

    Mirrored by `_change_log_sql` in ticket_tools/ticket_write.py, following
    this repo's convention that Bristol Tickets and the CLI writer each carry
    their own copy of shared DB logic so neither depends on the other's package
    (the viewer also ships as a relocatable .app).

    // A trigger in the main schema cannot reference a temp table, so the actor
    // cannot be read from a session variable at fire time. The triggers are
    // therefore created in the TEMP schema with the actor as a literal, which
    // scopes them to one connection and makes every entry attributable.
    """
    who = actor.replace("'", "''")
    inserts = []
    for field in CHANGE_LOG_FIELDS:
        inserts.append(
            "  INSERT INTO task_event (task_id, at, actor, field, from_value, to_value)\n"
            f"  SELECT new.id, {_NOW_SQL}, '{who}', '{field}', old.{field},\n"
            f"         COALESCE(CAST(new.{field} AS TEXT), '(none)')\n"
            f"  WHERE old.{field} IS NOT new.{field};"
        )
    for field in CHANGE_LOG_REDACTED_FIELDS:
        inserts.append(
            "  INSERT INTO task_event (task_id, at, actor, field, from_value, to_value)\n"
            f"  SELECT new.id, {_NOW_SQL}, '{who}', '{field}', NULL, '(changed)'\n"
            f"  WHERE old.{field} IS NOT new.{field};"
        )
    body = "\n".join(inserts)
    return f"""
DROP TRIGGER IF EXISTS temp.trg_task_change_log;
CREATE TEMP TRIGGER trg_task_change_log AFTER UPDATE ON main.task
BEGIN
{body}
  UPDATE task SET updated_at = COALESCE(
      (SELECT MAX(at) FROM task_event WHERE task_id = new.id), new.updated_at)
  WHERE id = new.id;
END;

DROP TRIGGER IF EXISTS temp.trg_task_genesis_log;
CREATE TEMP TRIGGER trg_task_genesis_log AFTER INSERT ON main.task
BEGIN
  INSERT INTO task_event (task_id, at, actor, field, from_value, to_value)
  VALUES (new.id, {_NOW_SQL}, '{who}', 'status', NULL, new.status);
  INSERT INTO task_event (task_id, at, actor, field, from_value, to_value)
  VALUES (new.id, {_NOW_SQL}, '{who}', 'stage', NULL,
          COALESCE(new.stage, 'backlog'));
END;
"""


def install_change_log(conn: sqlite3.Connection, actor: str) -> None:
    """Arm this connection so every task write appends its own change entries.

    Call once per connection, before any write. Entries are machine-written
    from a fixed grammar — no client composes one, and no client appends to
    task_event by hand, so a board move made by dragging a card and one made by
    the CLI are recorded identically. task.updated_at is refreshed from the
    newest entry rather than maintained by each writer.
    """
    conn.executescript(_change_log_sql(actor))


def _migrate_stage_from_sprints(conn: sqlite3.Connection) -> None:
    """One-time, idempotent migration to the Kanban Stage model.

    The presence of a `sprint` table is the "not yet migrated" signal: an old DB
    still has it, a migrated DB does not. When it is present we:
      1. backfill task.stage from the task's sprint membership —
         active sprint -> 'active', closed sprint -> 'archive',
         everything else (inactive sprint, or no sprint at all) -> 'backlog';
      2. fold the old 'backlog' *status* into the new stage: any task whose
         status is still 'backlog' becomes stage='backlog', status='todo' (the
         status axis is now only todo/doing/done);
      3. seed sort_order so each list keeps roughly its old on-screen order
         (pressure desc, then id) — a contiguous sequence per (stage, status);
      4. DROP sprint_task then sprint.
    After the drop this function is a no-op, so it is safe to run on every
    launch. Runs inside the caller's transaction (committed by
    ensure_schema_up_to_date)."""
    has_sprint = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sprint'"
    ).fetchone()
    if not has_sprint:
        return  # already migrated (or a fresh DB that never had sprints)

    # 1. stage from sprint membership. Do the broad default first, then the
    #    active/closed overrides, so a task in multiple sprints resolves to the
    #    "most in-play" stage (active wins over archive wins over backlog).
    conn.execute("UPDATE task SET stage='backlog'")
    conn.execute(
        "UPDATE task SET stage='archive' WHERE id IN ("
        "  SELECT st.task_id FROM sprint_task st "
        "  JOIN sprint s ON s.id = st.sprint_id WHERE s.status='closed')"
    )
    conn.execute(
        "UPDATE task SET stage='active' WHERE id IN ("
        "  SELECT st.task_id FROM sprint_task st "
        "  JOIN sprint s ON s.id = st.sprint_id WHERE s.status='active')"
    )

    # 2. retire the 'backlog' status value.
    conn.execute("UPDATE task SET status='todo' WHERE status='backlog'")

    # 3. seed a manual order from the old pressure ordering. The ordering key
    #    matches how each stage is DISPLAYED, so seeded order == old on-screen
    #    order: the Backlog is ONE combined list (key = stage alone), while the
    #    active Board is three separate columns (key = stage+status). Archive is
    #    shown chronologically by modified date, so its sort_order is unused.
    rows = conn.execute(
        "SELECT id, stage, status FROM task "
        "ORDER BY stage, pressure DESC, id ASC"
    ).fetchall()
    counters: dict[tuple, int] = {}
    for tid, stage, status in rows:
        key = (stage,) if stage != "active" else (stage, status)
        idx = counters.get(key, 0)
        conn.execute("UPDATE task SET sort_order=? WHERE id=?", (idx, tid))
        counters[key] = idx + 1

    # 4. drop the sprint tables.
    conn.execute("DROP TABLE IF EXISTS sprint_task")
    conn.execute("DROP TABLE IF EXISTS sprint")


def _ensure_link_dep_type(conn: sqlite3.Connection) -> None:
    """Add task_link.dep_type to a DB that predates typed links. Existing rows
    default to 'related', which is what every link written before the type
    existed meant. Mirrors create_tickets._ensure_link_dep_type."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(task_link)").fetchall()]
    if cols and "dep_type" not in cols:
        conn.execute(
            "ALTER TABLE task_link ADD COLUMN dep_type TEXT NOT NULL DEFAULT 'related'"
        )


def _retire_blocked_columns(conn: sqlite3.Connection) -> None:
    """Fold task.blocked / task.depends_on into 'blocks' links, then drop them.

    There is one dependency mechanism: a typed link. The old pair of columns
    could only say "this card depends on that one" once per card, was set by
    hand and never cleared, and had to be trusted against the depended-on
    ticket's real status. Each row that named a dependency becomes the link that
    says the same thing, and the columns go. Mirrors
    create_tickets._retire_blocked_columns; runs before the change-log triggers
    are installed, since they name the task columns.

    // ALTER TABLE ... DROP COLUMN needs SQLite 3.35; on an older library the
    // drop is skipped and the columns are left in place at their defaults,
    // unread and unwritten by anything.
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(task)").fetchall()]
    if "depends_on" not in cols and "blocked" not in cols:
        return

    if "depends_on" in cols:
        for task_id, blocker_id in conn.execute(
            "SELECT id, depends_on FROM task WHERE depends_on IS NOT NULL"
        ).fetchall():
            if conn.execute("SELECT 1 FROM task WHERE id=?",
                            (blocker_id,)).fetchone() is None:
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


def _drop_retired_handoff(conn: sqlite3.Connection) -> None:
    """Drop the retired `handoff` table if a DB still carries one.

    Retired deliberately, not deprecated: a per-agent narrative block is a
    second place a session could learn what is in flight, and the board is the
    only place that may answer that. Work left mid-flight is a `doing` card.
    Idempotent — a no-op once the table is gone."""
    conn.execute("DROP TABLE IF EXISTS handoff")


def _consolidate_legacy_history(conn: sqlite3.Connection) -> None:
    """One-time, non-destructive consolidation of the legacy `history` table
    into `issue_log`. `history` was an auto audit trail (events like 'edited',
    'moved to done') that the current UI never surfaced or appended to — only
    seeded and deleted — so it was invisible in-DB state. We fold its rows into
    the visible log as author='system' and drop the redundant table. Idempotent:
    once `history` is gone, this is a no-op."""
    has_history = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='history'"
    ).fetchone()
    if not has_history:
        return
    for task_id, event, created_at in conn.execute(
        "SELECT task_id, event, created_at FROM history"
    ).fetchall():
        conn.execute(
            "INSERT INTO issue_log (task_id, author, body, created_at) VALUES (?,?,?,?)",
            (task_id, "system", event, created_at),
        )
    conn.execute("DROP TABLE history")
