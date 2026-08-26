#!/usr/bin/env python3
"""
agent_status.py — lightweight ticket status reader for non‑CoS agents.

Machine-readable snapshot SCOPED TO ONE AGENT:
    - current milestone (fleet-wide; same for every agent)
    - the active board size (fleet-wide; stage='active')
    - this agent's own next action + own active-board queue
    - COMMENTS on this agent's active-board tasks (issue_log); user-authored
      ones flagged ⚠ — on-ticket decisions/direction a bare status line hides

Uses ONLY relative project structure under the project root. No personal data,
no usernames, no environment variables.

DB discovery rule:
    Walk up from this file to the nearest ancestor holding src/app.md — the
    project root — then search data/*/tickets/tickets.db. There is ONE shared
    tickets.db for the whole fleet; this script slices it to one agent. On a
    fresh clone nothing matches, and an empty board is provisioned there
    (create_tickets.locate_or_provision) rather than the run failing.

NEXT-ACTION SEMANTICS (aligned with cos_status.py):
    An agent's next action is its OWN work, scoped to the ACTIVE BOARD
    (task.stage='active'), in precedence: active-board `doing` (board order) →
    active-board `todo` (board order) → (fallback only if both empty) own
    `backlog` (stage='backlog'), surfaced as a planning signal to activate onto
    the board, not auto-executed. Work owned by other agents is never this
    agent's next action. A task's stage (not any sprint)
    is what puts it in play; stage is orthogonal to the epic.

    "Owned by me" resolves as: task.assignee == <agent_slug>; or, when a task
    has no explicit assignee, its epic's `owner` names the agent (substring
    match, since `owner` is sometimes a descriptive multi-agent string).

Usage:
    python3 agent_status.py <agent_slug>
    agent_slug is required (e.g. "career_coach", "librarian").
    chief_of_staff should use cos_status.py, which additionally prints a
    fleet-wide context section.

Environment note: don't shell out to a `sqlite3` CLI binary — not guaranteed
on PATH in sandboxed runtimes. Use Python's built-in sqlite3 (as below).
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_tickets  # noqa: E402  (owns the schema and first-use provisioning)


STATUS_RANK = {"doing": 0, "todo": 1}


# ---------------------------------------------------------------------------
# DB PATH RESOLUTION (canonical)
# ---------------------------------------------------------------------------

def resolve_db_path() -> Path:
    """The shared tickets.db, created empty on first use if it is not there."""
    return create_tickets.locate_or_provision()


# ---------------------------------------------------------------------------
# Ownership + active-board helpers (kept in lockstep with cos_status.py)
# ---------------------------------------------------------------------------

def owned_by(task_row: sqlite3.Row, me: str) -> bool:
    assignee = (task_row["assignee"] or "").strip()
    if assignee:
        return assignee == me
    return me in (task_row["epic_owner"] or "")


def board_tasks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every task on the active board — stage='active' (Kanban model).
    LEFT JOIN keeps epic-less tasks visible."""
    return conn.execute(
        "SELECT t.id, t.title, t.status, t.pressure, t.sort_order, t.estimate, "
        "       t.assignee, t.block_reason, "
        "       COALESCE(e.name, '(no epic)') AS epic, e.owner AS epic_owner "
        "FROM task t "
        "LEFT JOIN epic e ON t.epic_id = e.id "
        "WHERE t.stage = 'active'"
    ).fetchall()


def unmet_blockers(conn: sqlite3.Connection,
                   rows: list[sqlite3.Row]) -> dict[int, list[int]]:
    """{blocked task id -> the ids still blocking it}.

    A dependency is a `blocks` link: its task_id must be `done` before its
    other_id may start. Read live rather than stored, so a blocker that has
    since finished simply stops appearing — there is no flag to go stale and
    nothing to clear by hand.
    """
    ids = [r["id"] for r in rows]
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    out: dict[int, list[int]] = {}
    for blocked_id, blocker_id in conn.execute(
        f"SELECT l.other_id, l.task_id FROM task_link l "
        f"JOIN task b ON b.id = l.task_id "
        f"WHERE l.kind='issue' AND l.dep_type='blocks' AND b.status != 'done' "
        f"AND l.other_id IN ({ph}) ORDER BY l.task_id",
        ids,
    ):
        out.setdefault(blocked_id, []).append(blocker_id)
    return out

def queue_sort(rows: list[sqlite3.Row]) -> list[sqlite3.Row]:
    """Every `doing` card first, then every `todo` card, each in the board's own
    manual order (task.sort_order asc — the position the card sits at in its
    column). Nothing else reorders this queue.

    The order you see on the board IS the order the agent works. Dragging a card
    up a column moves it up the agent's queue, and an agent that reorders its
    own queue does it by rewriting sort_order. `pressure` is a 0–100 rating of
    how hard a card is pushing, not a rank, and it does not sort.

    A blocker deliberately does NOT sort. It was once the leading key, which
    silently sank a blocked `doing` card below every `todo` and made the script
    contradict the precedence it documents — the agent then executed the wrong
    ticket in good faith. A dependency annotates the queue and never reorders
    it: the card keeps its position wearing its blocker, and the agent stops
    there and says what would clear it rather than moving on to the card
    below."""
    return sorted(
        rows,
        key=lambda r: (STATUS_RANK.get(r["status"], 9), r["sort_order"], r["id"]),
    )


def my_backlog(conn: sqlite3.Connection, me: str) -> list[sqlite3.Row]:
    """Backlog-stage tasks owned by me. Epic-less tasks included;
    epic'd ones limited to unfinished epics to cut noise. Pressure desc."""
    rows = conn.execute(
        "SELECT t.id, t.title, t.status, t.pressure, t.assignee, "
        "       e.name AS epic, e.owner AS epic_owner "
        "FROM task t LEFT JOIN epic e ON t.epic_id = e.id "
        "WHERE t.stage = 'backlog' "
        "  AND (e.id IS NULL OR e.status NOT IN (%s))"
        % ",".join("?" * len(create_tickets.EPIC_STATUS_FINISHED)),
        tuple(create_tickets.EPIC_STATUS_FINISHED),
    ).fetchall()
    mine = [r for r in rows if owned_by(r, me)]
    return sorted(mine, key=lambda r: (-r["pressure"], r["id"]))


def latest_comment_per_task(conn: sqlite3.Connection,
                            task_ids: list[int]) -> dict[int, sqlite3.Row]:
    """Most recent issue_log row per task id. issue_log holds task-level
    comments (agent notes AND user decisions); nothing else in this snapshot
    reads it, so a user's on-ticket comment is otherwise invisible at start."""
    if not task_ids:
        return {}
    placeholders = ",".join("?" * len(task_ids))
    try:
        rows = conn.execute(
            f"SELECT task_id, author, body, created_at FROM issue_log "
            f"WHERE task_id IN ({placeholders}) ORDER BY created_at",
            task_ids,
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    latest: dict[int, sqlite3.Row] = {}
    for r in rows:                       # ascending, so last write wins
        latest[r["task_id"]] = r
    return latest


def print_comments(conn: sqlite3.Connection,
                   tasks: list[sqlite3.Row]) -> None:
    """Surface the latest comment on each of `tasks` that has one; ⚠ marks
    user-authored ones (context to read, NOT a pressure signal — pressure/stage
    decide the next task, never a comment)."""
    latest = latest_comment_per_task(conn, [t["id"] for t in tasks])
    if not latest:
        return
    print("\n--- COMMENTS on your active-board tasks (⚠ = user; context to read, NOT a pressure signal) ---")
    for t in tasks:
        c = latest.get(t["id"])
        if not c:
            continue
        mark = "⚠ " if (c["author"] or "").strip() == "user" else "  "
        body = " ".join((c["body"] or "").split())
        if len(body) > 300:
            body = body[:297] + "..."
        print(f"{mark}#{t['id']} [{c['created_at'][:10]} {c['author']}] {body}")


def print_needs_you(rows: list[sqlite3.Row]) -> None:
    """The cards only the user can clear, named rather than left in the queue.

    A decision block and a capability block are the two reasons no agent can
    resolve by working: one waits on a judgement that is the user's, the other
    on access that was never granted. A dependency waits on another card and a
    transient failure waits on a retry, so neither is listed here.
    """
    held = [r for r in rows
            if (r["block_reason"] or "") in create_tickets.BLOCK_REASONS_NEEDING_USER]
    if not held:
        return
    print("\n--- NEEDS YOU (blocked on something no agent can clear) ---")
    for r in held:
        print(f"  #{r['id']} [{r['block_reason']}] {r['title']}")


def fmt(r: sqlite3.Row, blockers: dict | None = None,
        position: int | None = None) -> str:
    # A blocker is named on the card so the agent sees it before it acts, and it
    # is a stop rather than a warning: the card keeps its place in the queue, and
    # the agent that reaches it says what would clear it instead of starting it,
    # doing "the unblocked part", or moving down to the next card.
    held_by = (blockers or {}).get(r["id"]) or []
    flag = ""
    if held_by:
        flag = " [BLOCKED by " + ", ".join(f"#{b}" for b in held_by) + "]"
    # The typed reason says what KIND of thing is in the way. 'dependency' names
    # no card and prints nothing of its own: the live blocker flag above is its
    # whole display, so a dependency whose blocker has finished disappears with
    # the flag rather than lingering as a stale word.
    reason = (r["block_reason"] or "").strip()
    if reason and reason != "dependency":
        flag += f" [BLOCKED: {reason}]"
    pos = f"{position:>2}." if position is not None else "   "
    return (f"  {pos} {r['status']:5} pr{r['pressure']:>3} {r['estimate'] or '-':>4}  "
            f"[{r['epic']}] {r['title']}{flag}")


def task_image_paths(conn: sqlite3.Connection, task_id: int, db_path) -> list[str]:
    """Absolute paths of images attached to a task (bytes live in an images/ dir
    beside the DB). [] if the attachment table predates this feature."""
    try:
        rows = conn.execute(
            "SELECT filename FROM attachment WHERE task_id=? ORDER BY id", (task_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    img_dir = Path(db_path).parent / "images"
    return [str(img_dir / r["filename"]) for r in rows]


def print_attachments(conn: sqlite3.Connection, tasks: list[sqlite3.Row], db_path) -> None:
    """Surface image attachments on your active-board tasks with real paths so they get
    VIEWED (Read the file), not ignored — attached images are supplementary
    prompt material the ticket text alone drops."""
    hits = [(t, task_image_paths(conn, t["id"], db_path)) for t in tasks]
    hits = [(t, paths) for t, paths in hits if paths]
    if not hits:
        return
    print("\n--- ATTACHED IMAGES (Read each path before acting on that task) ---")
    for t, paths in hits:
        for p in paths:
            print(f"  #{t['id']} {t['title']}\n      {p}")


def task_links(conn: sqlite3.Connection, task_id: int) -> list[str]:
    """One line per link on a task. Issue links are a single row read from
    either end (`task_id=? OR other_id=?`); a `blocks` row reads as "blocks" on
    the ticket that must finish first and "blocked by" on the one waiting. []
    if the table predates this feature."""
    out: list[str] = []
    try:
        rows = conn.execute(
            "SELECT l.task_id, l.other_id, l.dep_type, ta.title, tb.title "
            "FROM task_link l "
            "LEFT JOIN task ta ON ta.id = l.task_id "
            "LEFT JOIN task tb ON tb.id = l.other_id "
            "WHERE l.kind='issue' AND (l.task_id=? OR l.other_id=?) ORDER BY l.id",
            (task_id, task_id),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    for a, b, dep_type, title_a, title_b in rows:
        near_is_first = a == task_id
        far, title = (b, title_b) if near_is_first else (a, title_a)
        if dep_type == "blocks":
            relation = "blocks" if near_is_first else "blocked by"
        else:
            relation = "ticket"
        out.append(f"{relation} #{far} — {title or '(missing)'}")
    for uri, label in conn.execute(
        "SELECT uri, label FROM task_link WHERE kind='uri' AND task_id=? ORDER BY id",
        (task_id,),
    ).fetchall():
        out.append(f"{uri}" + (f"  ({label})" if label else ""))
    return out


def print_links(conn: sqlite3.Connection, tasks: list[sqlite3.Row]) -> None:
    """Surface each task's links. A link is where a ticket's provenance and
    related material live — the Description is confined to its record-type
    template — so a linked note or sibling ticket is context you are expected to
    follow before acting, exactly like an attached image."""
    hits = [(t, task_links(conn, t["id"])) for t in tasks]
    hits = [(t, links) for t, links in hits if links]
    if not hits:
        return
    print("\n--- LINKS on your active-board tasks (context to follow before acting) ---")
    for t, links in hits:
        print(f"  #{t['id']} {t['title']}")
        for line in links:
            print(f"      → {line}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1]:
        sys.exit(
            "agent_status: ERROR — agent_slug is required, e.g.\n"
            "  python3 agent_status.py career_coach\n"
            "(chief_of_staff should use cos_status.py instead)"
        )
    me = sys.argv[1]

    db_path = resolve_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # This reader writes: migrate() below brings a database one schema behind up
    # to date, and any write over a file bridge takes the same journal rule every
    # other writer takes — src/tools/ticket_tools/README.md §Invariants.
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=MEMORY")
    # A snapshot of a database one schema behind would read blockers that are
    # not there yet, so the schema is brought current first — the same reason
    # resolve_db_path provisions a missing database instead of failing.
    create_tickets.migrate(conn)
    cur = conn.cursor()

    print(f"=== Agent Ticket Status: {me} ({db_path}) ===\n")

    ms = cur.execute("SELECT name FROM theme WHERE is_milestone=1").fetchone()
    print(f"MILESTONE: {ms['name'] if ms else '(none set)'}")

    # This agent's own active epics (context)
    owner_like = f"%{me}%"
    actives = cur.execute(
        "SELECT name FROM epic WHERE status IN (%s) AND owner LIKE ? ORDER BY id"
        % ",".join("?" * len(create_tickets.EPIC_STATUS_IN_FLIGHT)),
        (*create_tickets.EPIC_STATUS_IN_FLIGHT, owner_like),
    ).fetchall()
    print(f"ACTIVE EPICS ({me}): {', '.join(e['name'] for e in actives) or '(none)'}")

    board = board_tasks(conn)
    print(f"ACTIVE BOARD (stage=active): {len(board)} task(s)\n")

    mine_all = [r for r in board if owned_by(r, me)]
    mine_q = queue_sort([r for r in board
                         if owned_by(r, me) and r["status"] in STATUS_RANK])

    if mine_q:
        nxt = mine_q[0]
        print(f"▶ NEXT ACTION ({me}, active board): "
              f"[{nxt['epic']}] {nxt['title']}  (pressure {nxt['pressure']}, {nxt['estimate'] or '?'})")
        print("\nYOUR QUEUE (active board, doing→todo, board order):")
        print("  Work it top to bottom. A `doing` card outranks every `todo`.")
        blockers = unmet_blockers(conn, board)
        for n, r in enumerate(mine_q, start=1):
            print(fmt(r, blockers, position=n))
    else:
        bl = my_backlog(conn, me)
        print(f"▶ NEXT ACTION ({me}): nothing on the active board (no doing/todo).")
        if bl:
            print("   Fallback — your backlog (activate one onto the board before executing):")
            for r in bl[:5]:
                print(f"     backlog pr{r['pressure']:>3}  [{r['epic']}] {r['title']}")
        else:
            print("   Your backlog is also empty — await direction.")

    print_needs_you(mine_all)
    print_comments(conn, mine_all)
    print_links(conn, mine_all)
    print_attachments(conn, mine_all, db_path)

    _tail(cur, conn, me)


def _tail(cur: sqlite3.Cursor, conn: sqlite3.Connection, me: str) -> None:
    # No handoff section by design — see cos_status._tail. Carry-forward is a
    # `doing` card on the active board, never a narrative note.
    conn.close()


if __name__ == "__main__":
    main()
