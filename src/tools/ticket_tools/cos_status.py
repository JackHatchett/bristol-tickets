#!/usr/bin/env python3
"""
cos_status.py — machine-readable ticket status snapshot for chief_of_staff.

This version uses ONLY relative project structure under the project root.
No personal data, no usernames, no environment variables.

DB discovery rule:
    Walk up from this file to the nearest ancestor holding src/app.md — the
    project root, whatever the user named its folder — then search:
        data/*/tickets/tickets.db
    On a fresh clone nothing matches, and an empty board is provisioned there
    (create_tickets.locate_or_provision) rather than the run failing.

Environment note: don't shell out to a `sqlite3` CLI binary — it is not
guaranteed to be on PATH in every execution environment this script may run
in (a sandboxed runtime often carries none). Python's built-in sqlite3 module (used
below) has no such dependency.

NEXT-ACTION SEMANTICS (Kanban model):
    "What should chief_of_staff do next" is NOT the global top of a fleet-wide
    doing/todo queue. It is chief_of_staff's OWN work, scoped to the ACTIVE
    BOARD (task.stage='active'), in this precedence:
        1. active-board tasks owned by me, status `doing`  (board order)
        2. active-board tasks owned by me, status `todo`   (board order)
        3. (fallback, only if 1+2 are empty) my `backlog` (stage='backlog') —
           surfaced as a planning signal to activate onto the board, NOT
           auto-executed.
    Tasks owned by OTHER agents are never my next action. They are printed in a
    clearly-labeled FLEET section for coordination visibility only — that is
    the one thing that stays fleet-wide in the CoS view.

    "Owned by me" resolves as: task.assignee == 'chief_of_staff'; or, when a
    task has no explicit assignee, its epic's owner names chief_of_staff.
    A task's stage (backlog | active | archive) — not any sprint — decides what's in play. stage is orthogonal to the epic, so
    the active board can span epics.

This script prints:
    - current milestone
    - active epics (fleet-wide)
    - active board (count of stage='active' tasks)
    - YOUR next action + YOUR active-board queue (chief_of_staff, scoped)
    - COMMENTS on your active-board tasks (issue_log), user-authored ones
      flagged with ⚠ — these are decisions/direction left ON a ticket that a
      bare status line does NOT show. Not reading them is how a user decision
      gets missed.
    - FLEET active-board items owned by other agents (context only)
"""

import os
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_tickets  # noqa: E402  (owns the schema and first-use provisioning)


ME = "chief_of_staff"
STATUS_RANK = {"doing": 0, "todo": 1}


# ---------------------------------------------------------------------------
# DB PATH RESOLUTION (canonical)
# ---------------------------------------------------------------------------

def resolve_db_path() -> Path:
    """The shared tickets.db, created empty on first use if it is not there."""
    return create_tickets.locate_or_provision()


# ---------------------------------------------------------------------------
# Ownership + active-board helpers
# ---------------------------------------------------------------------------

def owned_by(task_row: sqlite3.Row, me: str) -> bool:
    """A task is 'mine' if its assignee is me, or — when it has no explicit
    assignee — its epic's owner names me. `owner` may be a descriptive
    multi-agent string, so we substring-match it (assignee is a bare slug)."""
    assignee = (task_row["assignee"] or "").strip()
    if assignee:
        return assignee == me
    return me in (task_row["epic_owner"] or "")


# Under this much free space, a session is told before it starts choosing work.
LOW_SPACE_BYTES = 500_000_000



def warn_if_low_on_space() -> None:
    """Say so when the filesystem this script runs on is nearly full.

    Every board write is this process writing to a file, so a volume with no
    room left stops the board rather than slowing it — and the failure arrives
    as a tool error with no mention of disk, which reads like a broken bridge
    rather than a full one. The warning costs one statvfs and is printed before
    any work is chosen.

    // Measured at the home directory rather than at this file, because the file
    // may sit on a mount of another machine's disk whose free space says nothing
    // about the one the process is running out of.
    """
    try:
        stat = os.statvfs(Path.home())
    except (OSError, AttributeError):
        return
    free = stat.f_bavail * stat.f_frsize
    total = stat.f_blocks * stat.f_frsize
    if total <= 0 or free >= LOW_SPACE_BYTES:
        return
    print(f"!! LOW DISK: {free / 1_000_000:.0f} MB free of "
          f"{total / 1_000_000_000:.1f} GB on the filesystem this session runs "
          f"on.\n   At zero, every board write fails and the failure does not "
          f"mention disk. Clear space before working.\n")


def board_tasks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every task on the active board — i.e. stage='active' (Kanban model).
    These are the tasks 'in play right now'. A
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
    """Fallback only: my Backlog-stage tasks. Epic-less tasks are
    included; epic'd ones are limited to unfinished epics to cut noise.
    Pressure desc (a planning signal, not an execution order)."""
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
    """Most recent issue_log row per task id. issue_log is where task-level
    comments live (both agent notes and USER decisions/direction); nothing
    else in this snapshot reads it, so a user's on-ticket comment is otherwise
    invisible at session start."""
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
    """Surface the latest comment on each of `tasks` that has one. User-authored
    latest comments are flagged ⚠ as context to read — they are NOT a pressure
    signal and never reroute which task is next (pressure/stage decide that)."""
    latest = latest_comment_per_task(conn, [t["id"] for t in tasks])
    if not latest:
        return
    print("\n--- COMMENTS on your active-board tasks (⚠ = user; context to read, NOT a pressure signal) ---")
    for t in tasks:
        c = latest.get(t["id"])
        if not c:
            continue
        is_user = (c["author"] or "").strip() == "user"
        mark = "⚠ " if is_user else "  "
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

    Fleet-wide, like the rest of this script: a card any agent left waiting on
    the user is the user's to clear whoever owns it.
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
    who = (r["assignee"] or "").strip() or f"(epic:{r['epic_owner']})"
    pos = f"{position:>2}." if position is not None else "   "
    return (f"  {pos} {r['status']:5} pr{r['pressure']:>3} {r['estimate'] or '-':>4}  "
            f"[{r['epic']}] {r['title']}  <{who}>{flag}")


def task_image_paths(conn: sqlite3.Connection, task_id: int, db_path) -> list[str]:
    """Absolute paths of images attached to a task. Attachments store only the
    filename; the bytes live in an images/ dir beside the DB. Returns [] if the
    table predates this feature."""
    try:
        rows = conn.execute(
            "SELECT filename FROM attachment WHERE task_id=? ORDER BY id", (task_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    img_dir = Path(db_path).parent / "images"
    return [str(img_dir / r["filename"]) for r in rows]


def print_attachments(conn: sqlite3.Connection, tasks: list[sqlite3.Row], db_path) -> None:
    """Surface image attachments on your active-board tasks with their real paths, so
    they get VIEWED (Read the file), not ignored. Attached images are
    supplementary prompt material — a screenshot of a bug, a mock of the wanted
    result — and reading the ticket text alone silently drops them."""
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

    print(f"=== CoS Ticket status ({db_path}) ===\n")
    warn_if_low_on_space()

    ms = cur.execute("SELECT name FROM theme WHERE is_milestone=1").fetchone()
    print(f"DIRECTION — current milestone: {ms['name'] if ms else '(none set)'}")

    actives = cur.execute(
        "SELECT name FROM epic WHERE status IN (%s) ORDER BY id"
        % ",".join("?" * len(create_tickets.EPIC_STATUS_IN_FLIGHT)),
        tuple(create_tickets.EPIC_STATUS_IN_FLIGHT),
    ).fetchall()
    print(f"ACTIVE EPICS: {', '.join(e['name'] for e in actives) or '(none)'}")

    board = board_tasks(conn)
    print(f"ACTIVE BOARD (stage=active): {len(board)} task(s)\n")

    mine_all = [r for r in board if owned_by(r, ME)]
    mine_q = queue_sort([r for r in board
                         if owned_by(r, ME) and r["status"] in STATUS_RANK])
    others_q = queue_sort([r for r in board
                           if not owned_by(r, ME) and r["status"] in STATUS_RANK])

    if mine_q:
        nxt = mine_q[0]
        print(f"▶ YOUR NEXT ACTION ({ME}, active board): "
              f"[{nxt['epic']}] {nxt['title']}  (pressure {nxt['pressure']}, {nxt['estimate'] or '?'})")
        print("\nYOUR QUEUE (active board, doing→todo, board order):")
        print("  Work it top to bottom. A `doing` card outranks every `todo`.")
        blockers = unmet_blockers(conn, board)
        for n, r in enumerate(mine_q, start=1):
            print(fmt(r, blockers, position=n))
    else:
        bl = my_backlog(conn, ME)
        print(f"▶ YOUR NEXT ACTION ({ME}): nothing on the active board (no doing/todo).")
        if bl:
            print("   Fallback — your backlog (activate one onto the board before executing):")
            for r in bl[:5]:
                print(f"     backlog pr{r['pressure']:>3}  [{r['epic']}] {r['title']}")
        else:
            print("   Your backlog is also empty — await direction.")

    print_needs_you(board)
    print_comments(conn, mine_all)
    print_links(conn, mine_all)
    print_attachments(conn, mine_all, db_path)

    print("\n--- FLEET (active-board items owned by OTHER agents — context only, not yours) ---")
    if others_q:
        for r in others_q:
            print(fmt(r, unmet_blockers(conn, board)))
    else:
        print("  (none)")

    _tail(cur, conn)


def _tail(cur: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    # No handoff section by design. A session's carry-forward IS its cards: work
    # left mid-flight is a `doing` card on the active board with a real owner and
    # pressure. There is no per-agent narrative block, because a note saying
    # "where things stand" is work state living somewhere other than a ticket.
    conn.close()


if __name__ == "__main__":
    main()
