#!/usr/bin/env python3
"""
ticket_write.py — safe write helper for the tickets DB.

Why this exists: an ad-hoc raw sqlite3 INSERT against tickets.db
(run from a Cowork sandbox session, over the mounted-folder bridge to the
user's real filesystem) can fail mid-write with a disk I/O error and leave a
stuck rollback-journal file that then blocks ALL further access to the DB,
including plain reads, until the journal is manually cleared. Root cause is
unconfirmed, but the on-disk rollback journal is the suspect: this script
avoids writing one at all (journal_mode=MEMORY) as a first line of defense.
See src/tools/ticket_tools/README.md (3a) for the read/write asymmetry
observed on this mount.

Usage:
    python3 ticket_write.py add-epic --name "..." --owner "..."
        [--type "..."] [--description "..."] [--next-action "..."]
        [--status not started|planning|active|done]
        Owner should be a single agent slug (e.g. "career_coach") for an
        epic that belongs to one agent; only use a descriptive multi-agent
        string ("librarian (execution), chief_of_staff (coordination)") for
        genuinely shared work. Tasks inherit ownership from their epic (see
        `add-task` below) -- there is no separate per-task owner column.

    python3 ticket_write.py add-task --title "..." [--description "..."]
        [--epic-id N] [--stage backlog|active|archive] [--status todo|doing|done]
        [--pressure N] [--estimate S|M|L|XL] [--reporter "..."] [--assignee "..."]
        [--record-type build|fix]
        (defaults: stage=backlog, status=todo, reporter="Claude (Cowork)",
        record-type=build)
        A task carries TWO orthogonal fields (Kanban model):
        `stage` = which tab it lives in (backlog | active | archive), and
        `status` = the board column (todo | doing | done). New self-authored
        tasks default to the Backlog stage, appended to the BOTTOM of the
        backlog's manual order (task.sort_order). 'backlog' is not a
        status; passing --status backlog is accepted but redirected to
        --stage backlog / --status todo.
        A task's owning agent is its --assignee if set, else whatever agent owns
        its --epic-id (see `epic.owner`); pass an epic that belongs to the right
        agent so `agent_status.py <slug>` picks it up. A ticket is a *build* (a
        thing to build — its --description is a Story + Given/When/Then
        acceptance criteria) or a *fix* (a broken thing — its --description is
        Expected/Observed). Follow the format in playbooks/manage_tickets.md
        (§Record types); the viewer shows the same skeletons when you create in
        the GUI.

        CROSS-AGENT SUGGESTION: to suggest work
        that lands in another agent's or the user's zone, add a card with
        --stage active, --assignee <that agent/user> and --reporter <you>. It
        lands in that agent's `todo` on the board the user actually watches.
        The --assignee is what makes it a proposal rather than a command: it is
        that agent's card to accept, reorder, or drop.

    python3 ticket_write.py add-issue-log --task N --author <slug|user>
        --body "..."
        Appends one brief, attributed line to a task's per-issue progress log
        (the `issue_log` table, surfaced in the viewer's inspector). Use it to
        track progress on an individual issue instead of spawning throwaway
        tasks. One
        short thought per entry (what happened / what's next).

    python3 ticket_write.py link-add --task N
        (--to-task M | --uri "...") [--label "..."] [--author <slug|user>]
    python3 ticket_write.py link-list --task N
    python3 ticket_write.py link-remove --id L
        A ticket's Description must stay inside its record-type template, so
        provenance -- "this came out of that review", "this relates to that
        note" -- belongs in a LINK, never in an off-template Source header.
        Two kinds:
          --to-task M  links two tickets. The row is stored ONCE, normalized
                       (task_id = the lower id), so the link appears on both
                       tickets from the moment it is written. Never run the
                       mirror call; there is no second row to create and no
                       one-way state to fall into.
          --uri "..."  links the ticket to an address: a web URL, a zotero://
                       citation, an obsidian:// note, or a filesystem path. The
                       viewer hands it to the OS to open, so nothing here knows
                       about schemes, vaults or user paths.
        `link-list` prints ids; `link-remove --id` deletes one, and for an issue
        link that clears it from both tickets at once.

DB discovery: same project-relative rule as cos_status.py / agent_status.py
(find the project root, then data/*/tickets/tickets.db). Resolved design: there is ONE shared tickets.db for the whole fleet, not one per
agent. Every agent reads and writes the same database; `epic.owner` tags
which agent an epic belongs to (a task's owner is its `assignee`, else implicit
via its epic). Cross-agent suggestions are ordinary active-board cards
(`--stage active`, `--assignee` = the target agent, `--reporter` = the
originator), not a separate store. "First glob match" is safe under this model
specifically because there's exactly one tickets.db to match — don't
provision a second one under a different data/<agent>/tickets/ path; use
`add-epic` in this file instead to give a new agent its own epic in the
existing db.
"""

import argparse
import datetime
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_tickets  # noqa: E402  (owns the schema and first-use provisioning)


def resolve_db_path() -> Path:
    """The shared tickets.db, created empty on first use if it is not there."""
    return create_tickets.locate_or_provision()


def connect(actor: str = "agent") -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_db_path(), timeout=10)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=MEMORY")  # avoid the on-disk journal that can wedge the DB over the mount
    # Self-healing: the per-issue progress log (mirrors the viewer's
    # schema_guard). Agents append here via `add-issue-log` so a task's
    # progress is tracked on the card itself, without spawning new tasks.
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
    # Self-healing: the mechanical change log (mirrors the viewer's
    # schema_guard). One row per changed task field — field, new value, actor,
    # ISO timestamp — appended by the triggers installed below. Read by
    # Bristol's Log pane, alongside issue_log comments, and by the reports
    # package, which measures cycle time from the status and stage rows.
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
    # Self-healing: a ticket's links (mirrors the viewer's schema_guard). An
    # issue link is ONE symmetric row normalized to task_id=MIN / other_id=MAX,
    # so it reads from either end and deletes once; a uri link hangs an address
    # (web URL, zotero://, obsidian://, or a file path) off a single ticket.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_link (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            kind       TEXT    NOT NULL,
            task_id    INTEGER NOT NULL,
            other_id   INTEGER,
            uri        TEXT,
            label      TEXT,
            author     TEXT,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (task_id)  REFERENCES task (id),
            FOREIGN KEY (other_id) REFERENCES task (id)
        );
    """)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_task_link_pair "
        "ON task_link (task_id, other_id) WHERE kind = 'issue'"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_link_task ON task_link (task_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_link_other ON task_link (other_id)")
    _ensure_stage_columns(conn)
    conn.commit()
    install_change_log(conn, actor)
    return conn


# ---------------------------------------------------------------------------
# The mechanical change log
# ---------------------------------------------------------------------------

# Fields logged with their new value.
CHANGE_LOG_FIELDS = (
    "epic_id", "scope_id", "status", "stage", "pressure", "estimate",
    "blocked", "depends_on", "assignee", "reporter", "story_points",
    "record_type",
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

    Mirrors `_change_log_sql` in bristol/ui/schema_guard.py — the two writers
    each carry their own copy of shared DB logic (the existing convention in
    this repo for the schema self-healing above), so neither package depends on
    the other and the viewer can still ship as a relocatable .app.

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

    Called from connect(), before any write. Entries are machine-written from a
    fixed grammar — no command composes one, and nothing here appends to
    task_event by hand, so a move made from the CLI is recorded identically to
    one made by dragging a card in Bristol. task.updated_at is refreshed from
    the newest entry rather than maintained by each writer.
    """
    conn.executescript(_change_log_sql(actor))


def _ensure_stage_columns(conn: sqlite3.Connection) -> None:
    """Self-heal the Kanban Stage columns into a DB that predates them (mirrors
    the viewer's schema_guard), so this writer never fails on an older schema.
    Only adds the columns — the full sprint backfill/drop is the viewer's
    schema_guard migration; a DB touched by the CLI first simply gets the new
    columns at their defaults."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(task)").fetchall()]
    if "pressure" not in cols and "priority" in cols:
        conn.execute("ALTER TABLE task RENAME COLUMN priority TO pressure;")
        cols = [c if c != "priority" else "pressure" for c in cols]
    if "stage" not in cols:
        conn.execute("ALTER TABLE task ADD COLUMN stage TEXT NOT NULL DEFAULT 'backlog';")
    if "sort_order" not in cols:
        conn.execute("ALTER TABLE task ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;")


def _append_order(conn: sqlite3.Connection, stage: str, status: str) -> int:
    """The sort_order that appends a task to the BOTTOM of its destination list:
    the Backlog is one combined list (keyed on stage alone), while the active
    Board is a separate list per status column (keyed on stage+status). Archive
    is shown chronologically, so its sort_order is unused but still assigned for
    consistency."""
    if stage == "active":
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage='active' AND status=?",
            (status,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage=?", (stage,)
        ).fetchone()
    return int(row[0]) + 1


def _normalize_stage_status(stage, status):
    """Fold the legacy 'backlog' *status* into the Stage model: --status backlog
    means stage=backlog / status=todo unless an explicit --stage was given."""
    if (status or "").lower() == "backlog":
        return (stage or "backlog"), "todo"
    return (stage or "backlog"), (status or "todo")


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def add_epic(args: argparse.Namespace) -> None:
    conn = connect()
    try:
        cur = conn.execute(
            """INSERT INTO epic (name, type, status, owner, description, next_action, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (args.name, args.type, args.status, args.owner, args.description,
             args.next_action, now()),
        )
        conn.commit()
        print(f"OK: epic #{cur.lastrowid} added — {args.name} (owner: {args.owner})")
    finally:
        conn.close()


def add_task(args: argparse.Namespace) -> None:
    conn = connect(getattr(args, "actor", None) or args.reporter or "agent")
    try:
        ts = now()
        # Self-heal record_type into DBs that predate it, mirroring the viewer's
        # schema_guard, so this writer never fails on an older schema.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(task)").fetchall()]
        if "record_type" not in cols:
            conn.execute("ALTER TABLE task ADD COLUMN record_type TEXT NOT NULL DEFAULT 'build';")
            conn.commit()
        record_type = (args.record_type or "build").lower()
        if record_type not in ("build", "fix"):
            sys.exit("add-task: ERROR — --record-type must be 'build' or 'fix'")
        stage, status = _normalize_stage_status(args.stage, args.status)
        if stage not in ("backlog", "active", "archive"):
            sys.exit("add-task: ERROR — --stage must be backlog|active|archive")
        if status not in ("todo", "doing", "done"):
            sys.exit("add-task: ERROR — --status must be todo|doing|done")
        sort_order = _append_order(conn, stage, status)
        cur = conn.execute(
            """INSERT INTO task (epic_id, scope_id, title, description, status,
                   pressure, estimate, blocked, depends_on, created_at, updated_at,
                   closed_at, assignee, reporter, story_points, record_type,
                   stage, sort_order)
               VALUES (?, NULL, ?, ?, ?, ?, ?, 0, NULL, ?, ?, NULL, ?, ?, 0, ?, ?, ?)""",
            (args.epic_id, args.title, args.description, status,
             args.pressure, args.estimate, ts, ts, args.assignee, args.reporter,
             record_type, stage, sort_order),
        )
        conn.commit()
        print(f"OK: {record_type} #{cur.lastrowid} added — {args.title} "
              f"(stage={stage}, status={status})")
    finally:
        conn.close()


def update_task_status(args: argparse.Namespace) -> None:
    conn = connect(getattr(args, "actor", None) or "agent")
    try:
        ts = now()
        # --status backlog is redirected to a stage move (backlog is not a
        # status). An explicit --stage always wins.
        stage = args.stage
        status = args.status
        if (status or "").lower() == "backlog":
            stage = stage or "backlog"
            status = None  # leave the board column unchanged on a bare stage move
        if status is not None and status not in ("todo", "doing", "done"):
            sys.exit("update-task-status: ERROR — --status must be todo|doing|done")

        row = conn.execute("SELECT stage, status FROM task WHERE id=?", (args.id,)).fetchone()
        if row is None:
            print(f"WARN: no task with id {args.id}")
            return
        cur_stage, cur_status = row
        new_stage = stage if stage is not None else cur_stage
        new_status = status if status is not None else cur_status

        # updated_at is not set here: the change log's triggers derive it from
        # the newest entry this write produces.
        sets, vals = [], []
        if status is not None:
            sets.append("status = ?"); vals.append(status)
            # closed_at tracks the done transition; clear it if reopened.
            sets.append("closed_at = ?"); vals.append(ts if status == "done" else None)
        if stage is not None:
            sets.append("stage = ?"); vals.append(new_stage)
        # A stage or status move re-homes the task, so re-seat it at the bottom
        # of its (new) destination list.
        if stage is not None or status is not None:
            sets.append("sort_order = ?"); vals.append(_append_order(conn, new_stage, new_status))
        if args.pressure is not None:
            sets.append("pressure = ?"); vals.append(args.pressure)
        if args.assignee is not None:
            sets.append("assignee = ?"); vals.append(args.assignee)
        if sets:
            vals.append(args.id)
            conn.execute(f"UPDATE task SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
        extras = []
        if stage is not None:
            extras.append(f"stage {new_stage}")
        if args.pressure is not None:
            extras.append(f"pressure {args.pressure}")
        if args.assignee is not None:
            extras.append(f"assignee {args.assignee}")
        tail = (" (" + ", ".join(extras) + ")") if extras else ""
        print(f"OK: task #{args.id} -> status {new_status}{tail}")
    finally:
        conn.close()


def set_stage(args: argparse.Namespace) -> None:
    """Move a task between tabs. It is appended to the BOTTOM of the
    destination's manual order — the backlog's single list, or the active board's
    matching status column. The move reaches the change log through its
    triggers, which is also what carries updated_at forward for the Archive
    tab's most-recently-modified order. CLI equivalent of the
    viewer's Board "Bulk Change" and the Backlog tab's "Activate"."""
    conn = connect(getattr(args, "actor", None) or "agent")
    try:
        if args.stage not in ("backlog", "active", "archive"):
            sys.exit("set-stage: ERROR — --stage must be backlog|active|archive")
        row = conn.execute("SELECT status, stage FROM task WHERE id=?", (args.id,)).fetchone()
        if row is None:
            print(f"WARN: no task with id {args.id}")
            return
        status, prior_stage = row
        conn.execute(
            "UPDATE task SET stage=?, sort_order=? WHERE id=?",
            (args.stage, _append_order(conn, args.stage, status), args.id),
        )
        conn.commit()
        print(f"OK: task #{args.id} -> stage {args.stage}")
    finally:
        conn.close()


def set_order(args: argparse.Namespace) -> None:
    """Move a task to a position in its own list — the CLI equivalent of
    dragging its card up or down a column in Bristol.

    A list is one active-board status column (stage='active' + that status), or
    the whole backlog. `--position 1` is the top. The whole list is renumbered
    contiguously afterwards, so positions stay readable instead of drifting into
    gaps. This is the only thing that reorders an agent's queue: the status
    scripts read sort_order, and pressure never sorts."""
    conn = connect(getattr(args, "actor", None) or "agent")
    try:
        row = conn.execute(
            "SELECT status, stage FROM task WHERE id=?", (args.id,)).fetchone()
        if row is None:
            print(f"WARN: no task with id {args.id}")
            return
        status, stage = row
        if stage == "active":
            siblings = conn.execute(
                "SELECT id FROM task WHERE stage='active' AND status=? "
                "ORDER BY sort_order ASC, id ASC", (status,)).fetchall()
        else:
            siblings = conn.execute(
                "SELECT id FROM task WHERE stage=? ORDER BY sort_order ASC, id ASC",
                (stage,)).fetchall()
        ids = [r[0] for r in siblings if r[0] != args.id]
        target = max(1, min(args.position, len(ids) + 1))
        ids.insert(target - 1, args.id)
        for pos, tid in enumerate(ids):
            conn.execute("UPDATE task SET sort_order=? WHERE id=?", (pos, tid))
        conn.commit()
        listname = f"{stage}/{status}" if stage == "active" else stage
        print(f"OK: task #{args.id} -> position {target} of {len(ids)} in {listname}")
    finally:
        conn.close()


def add_issue_log(args: argparse.Namespace) -> None:
    """Append one brief, attributed line to a task's issue_log. This is the
    DB-native way to record progress on an individual issue, instead of
    creating throwaway tasks. Keep each entry short: what happened, one thought."""
    conn = connect()
    try:
        if conn.execute("SELECT 1 FROM task WHERE id = ?", (args.task,)).fetchone() is None:
            sys.exit(f"add-issue-log: ERROR — no task with id {args.task}")
        cur = conn.execute(
            "INSERT INTO issue_log (task_id, author, body, created_at) VALUES (?, ?, ?, ?)",
            (args.task, args.author, args.body, now()),
        )
        conn.commit()
        print(f"OK: issue_log #{cur.lastrowid} added — task #{args.task} ({args.author})")
    finally:
        conn.close()


def link_add(args: argparse.Namespace) -> None:
    """Attach a link to a ticket: either another ticket (--to-task) or an
    address (--uri). An issue link is stored once, normalized, so it appears on
    BOTH tickets immediately — there is no second call to make and no way to end
    up with a one-way link."""
    if (args.to_task is None) == (args.uri is None):
        sys.exit("link-add: ERROR — pass exactly one of --to-task or --uri")
    conn = connect()
    try:
        if conn.execute("SELECT 1 FROM task WHERE id=?", (args.task,)).fetchone() is None:
            sys.exit(f"link-add: ERROR — no task with id {args.task}")

        if args.to_task is not None:
            if args.to_task == args.task:
                sys.exit("link-add: ERROR — a ticket cannot be linked to itself")
            if conn.execute("SELECT 1 FROM task WHERE id=?",
                            (args.to_task,)).fetchone() is None:
                sys.exit(f"link-add: ERROR — no task with id {args.to_task}")
            lo, hi = sorted((args.task, args.to_task))
            if conn.execute(
                "SELECT 1 FROM task_link WHERE kind='issue' AND task_id=? AND other_id=?",
                (lo, hi),
            ).fetchone():
                print(f"OK: #{args.task} and #{args.to_task} were already linked")
                return
            cur = conn.execute(
                "INSERT INTO task_link (kind, task_id, other_id, author, created_at) "
                "VALUES ('issue',?,?,?,?)",
                (lo, hi, args.author, now()),
            )
            conn.commit()
            print(f"OK: link #{cur.lastrowid} — #{args.task} <-> #{args.to_task}")
        else:
            cur = conn.execute(
                "INSERT INTO task_link (kind, task_id, uri, label, author, created_at) "
                "VALUES ('uri',?,?,?,?,?)",
                (args.task, args.uri, args.label, args.author, now()),
            )
            conn.commit()
            print(f"OK: link #{cur.lastrowid} — #{args.task} -> {args.uri}")
    finally:
        conn.close()


def link_list(args: argparse.Namespace) -> None:
    """Print every link on a ticket, from either end of an issue pair."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT l.id, l.task_id, l.other_id, ta.title, tb.title "
            "FROM task_link l "
            "LEFT JOIN task ta ON ta.id = l.task_id "
            "LEFT JOIN task tb ON tb.id = l.other_id "
            "WHERE l.kind='issue' AND (l.task_id=? OR l.other_id=?) ORDER BY l.id",
            (args.task, args.task),
        ).fetchall()
        for link_id, a, b, title_a, title_b in rows:
            far, title = (b, title_b) if a == args.task else (a, title_a)
            print(f"  [{link_id}] issue -> #{far} {title or '(missing)'}")
        for link_id, uri, label in conn.execute(
            "SELECT id, uri, label FROM task_link WHERE kind='uri' AND task_id=? "
            "ORDER BY id", (args.task,)
        ).fetchall():
            print(f"  [{link_id}] uri   -> {uri}" + (f"  ({label})" if label else ""))
    finally:
        conn.close()


def link_remove(args: argparse.Namespace) -> None:
    """Delete one link by its id (from `link-list`). Removing an issue link
    removes it from both tickets, because both were reading the same row."""
    conn = connect()
    try:
        if conn.execute("SELECT 1 FROM task_link WHERE id=?",
                        (args.id,)).fetchone() is None:
            sys.exit(f"link-remove: ERROR — no link with id {args.id}")
        conn.execute("DELETE FROM task_link WHERE id=?", (args.id,))
        conn.commit()
        print(f"OK: link #{args.id} removed")
    finally:
        conn.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Safe writer for tickets.db")
    sub = p.add_subparsers(dest="command", required=True)

    pe = sub.add_parser("add-epic")
    pe.add_argument("--name", required=True)
    pe.add_argument("--owner", required=True,
                     help="agent slug that owns this epic (single agent), or a "
                          "descriptive multi-agent string for genuinely shared work")
    pe.add_argument("--type", default=None)
    pe.add_argument("--description", default=None)
    pe.add_argument("--next-action", dest="next_action", default=None)
    pe.add_argument("--status", default="not started")
    pe.set_defaults(func=add_epic)

    pt = sub.add_parser("add-task")
    pt.add_argument("--title", required=True)
    pt.add_argument("--description", default=None)
    pt.add_argument("--epic-id", dest="epic_id", type=int, default=None)
    pt.add_argument("--stage", default="backlog",
                     help="which tab: backlog | active | archive (default backlog).")
    pt.add_argument("--status", default="todo",
                     help="board column: todo | doing | done (default todo). "
                          "'backlog' is accepted for back-compat and redirected to --stage backlog.")
    pt.add_argument("--pressure", type=int, default=0)
    pt.add_argument("--estimate", default=None,
                     help="S|M|L|XL — how much of a full usage budget this "
                          "card would take. Scale and anchors in src/app.md "
                          "(Effort sizing); XL means split it, not start it.")
    pt.add_argument("--reporter", default="Claude (Cowork)",
                     help="who/what originated this task (default: Claude (Cowork))")
    pt.add_argument("--assignee", default=None,
                     help="agent slug (or 'user') that owns this task. Set it to "
                          "leave a cross-agent suggestion: file it with --stage active, "
                          "assigned to that agent.")
    pt.add_argument("--record-type", dest="record_type", default="build",
                     choices=["build", "fix"],
                     help="'build' (a thing to build — Story + acceptance criteria) "
                          "or 'fix' (a broken thing — Expected/Observed). Default build. "
                          "Write --description in that record type's format (see "
                          "playbooks/manage_tickets.md §Record types).")
    pt.add_argument("--actor", default=None,
                     help="who is making this change, for the change log "
                          "(your write signature, e.g. cowork_chief_of_staff). "
                          "Defaults to --reporter.")
    pt.set_defaults(func=add_task)

    pu = sub.add_parser("update-task-status")
    pu.add_argument("--id", type=int, required=True)
    pu.add_argument("--status", required=True, choices=["backlog", "todo", "doing", "done"],
                     help="board column: todo|doing|done. 'backlog' is accepted for "
                          "back-compat and redirected to a --stage backlog move.")
    pu.add_argument("--stage", default=None, choices=["backlog", "active", "archive"],
                     help="optionally move the task's tab in the same call")
    pu.add_argument("--pressure", type=int, default=None,
                     help="optionally reset pressure in the same call")
    pu.add_argument("--assignee", default=None,
                     help="optionally set the task's assignee (an agent slug)")
    pu.add_argument("--actor", default=None,
                     help="who is making this change, for the change log "
                          "(your write signature, e.g. cowork_chief_of_staff). "
                          "Recorded against every field this call changes.")
    pu.set_defaults(func=update_task_status)

    psg = sub.add_parser("set-stage")
    psg.add_argument("--id", type=int, required=True)
    psg.add_argument("--stage", required=True, choices=["backlog", "active", "archive"],
                      help="destination tab; task is appended to the bottom of its order")
    psg.add_argument("--actor", default=None,
                      help="who is making this change, for the change log "
                           "(your write signature, e.g. cowork_chief_of_staff). "
                           "Recorded against every field this call changes.")
    psg.set_defaults(func=set_stage)

    pso = sub.add_parser("set-order")
    pso.add_argument("--id", type=int, required=True)
    pso.add_argument("--position", type=int, required=True,
                      help="1 = top of the card's own list (its active-board "
                           "status column, or the whole backlog). The list is "
                           "renumbered contiguously. This is what reorders an "
                           "agent's queue — pressure does not.")
    pso.add_argument("--actor", default=None,
                      help="who is making this change, for the change log "
                           "(your write signature, e.g. cowork_chief_of_staff).")
    pso.set_defaults(func=set_order)

    pil = sub.add_parser("add-issue-log")
    pil.add_argument("--task", type=int, required=True, help="task/issue id to log against")
    pil.add_argument("--author", required=True,
                      help="who is posting (agent slug, or 'user')")
    pil.add_argument("--body", required=True, help="brief progress note")
    pil.set_defaults(func=add_issue_log)

    pla = sub.add_parser("link-add")
    pla.add_argument("--task", type=int, required=True, help="the ticket the link hangs off")
    pla.add_argument("--to-task", dest="to_task", type=int, default=None,
                      help="link to another ticket. Stored once and symmetric, so it "
                           "shows on BOTH tickets — do not also run the mirror call.")
    pla.add_argument("--uri", default=None,
                      help="link to an address: a web URL, a zotero:// citation, an "
                           "obsidian:// note, or a file path. The viewer hands it to "
                           "the OS, so any scheme the machine knows will open.")
    pla.add_argument("--label", default=None,
                      help="optional caption shown instead of the address")
    pla.add_argument("--author", default="user",
                      help="who added the link (your write signature, or 'user')")
    pla.set_defaults(func=link_add)

    pll = sub.add_parser("link-list")
    pll.add_argument("--task", type=int, required=True)
    pll.set_defaults(func=link_list)

    plr = sub.add_parser("link-remove")
    plr.add_argument("--id", type=int, required=True,
                      help="link id from link-list. An issue link is removed from both "
                           "tickets at once.")
    plr.set_defaults(func=link_remove)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
