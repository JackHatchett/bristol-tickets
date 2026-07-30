#!/usr/bin/env python3
"""
cos_status.py — machine-readable ticket status snapshot for chief_of_staff.

This version uses ONLY relative project structure under the project root.
No personal data, no usernames, no environment variables.

DB discovery rule:
    Walk up from this file to the nearest ancestor holding src/app.md — the
    project root, whatever the user named its folder — then search:
        data/*/tickets/tickets.db

Environment note: don't shell out to a `sqlite3` CLI binary — it is not
guaranteed to be on PATH in every execution environment this script may run
in (e.g. sandboxed Cowork runtimes). Python's built-in sqlite3 module (used
below) has no such dependency.

NEXT-ACTION SEMANTICS (Kanban model):
    "What should chief_of_staff do next" is NOT the global top of a fleet-wide
    doing/todo queue. It is chief_of_staff's OWN work, scoped to the ACTIVE
    BOARD (task.stage='active'), in this precedence:
        1. active-board tasks owned by me, status `doing`  (priority desc)
        2. active-board tasks owned by me, status `todo`   (priority desc)
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

import sys
import sqlite3
from pathlib import Path


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


ME = "chief_of_staff"
STATUS_RANK = {"doing": 0, "todo": 1}


# ---------------------------------------------------------------------------
# DB PATH RESOLUTION (canonical)
# ---------------------------------------------------------------------------

def resolve_db_path() -> Path:
    data_root = _project_root() / "data"

    matches = list(data_root.glob("*/tickets/tickets.db"))
    if not matches:
        sys.exit("cos_status: ERROR — no tickets.db found under data/*/tickets/")
    return matches[0]


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


def board_tasks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every task on the active board — i.e. stage='active' (Kanban model).
    These are the tasks 'in play right now'. A
    LEFT JOIN keeps epic-less tasks visible."""
    return conn.execute(
        "SELECT t.id, t.title, t.status, t.priority, t.blocked, t.depends_on, t.estimate, "
        "       t.assignee, COALESCE(e.name, '(no epic)') AS epic, e.owner AS epic_owner "
        "FROM task t "
        "LEFT JOIN epic e ON t.epic_id = e.id "
        "WHERE t.stage = 'active'"
    ).fetchall()


def blocker_statuses(conn: sqlite3.Connection,
                     rows: list[sqlite3.Row]) -> dict[int, str]:
    """{task id -> status} for every ticket some row claims to depend on, so the
    BLOCKED flag can be checked against reality instead of trusted."""
    ids = sorted({r["depends_on"] for r in rows if r["blocked"] and r["depends_on"]})
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    return {i: s for i, s in
            conn.execute(f"SELECT id, status FROM task WHERE id IN ({ph})", ids)}

def queue_sort(rows: list[sqlite3.Row]) -> list[sqlite3.Row]:
    """Every `doing` card first (priority desc), then every `todo` card
    (priority desc). Nothing else reorders this queue.

    `blocked` deliberately does NOT sort. It used to be the leading key, which
    silently sank a blocked `doing` card below every `todo` and made the script
    contradict the precedence it documents — the agent then executed the wrong
    ticket in good faith. Blocked is a flag to act on, not a reason to skip: the
    card stays at the top of the queue wearing its flag, and the agent unblocks
    it, works what it can, or reports why it cannot."""
    return sorted(
        rows,
        key=lambda r: (STATUS_RANK.get(r["status"], 9), -r["priority"], r["id"]),
    )


def my_backlog(conn: sqlite3.Connection, me: str) -> list[sqlite3.Row]:
    """Fallback only: my Backlog-stage tasks. Epic-less tasks are
    included; epic'd ones are limited to active/planning epics to cut noise.
    Priority desc (a planning signal, not an execution order)."""
    rows = conn.execute(
        "SELECT t.id, t.title, t.status, t.priority, t.assignee, "
        "       e.name AS epic, e.owner AS epic_owner "
        "FROM task t LEFT JOIN epic e ON t.epic_id = e.id "
        "WHERE t.stage = 'backlog' "
        "  AND (e.id IS NULL OR e.status IN ('active','planning'))"
    ).fetchall()
    mine = [r for r in rows if owned_by(r, me)]
    return sorted(mine, key=lambda r: (-r["priority"], r["id"]))


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
    latest comments are flagged ⚠ as context to read — they are NOT a priority
    signal and never reroute which task is next (priority/stage decide that)."""
    latest = latest_comment_per_task(conn, [t["id"] for t in tasks])
    if not latest:
        return
    print("\n--- COMMENTS on your active-board tasks (⚠ = user; context to read, NOT a priority signal) ---")
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


def fmt(r: sqlite3.Row, blockers: dict | None = None) -> str:
    # BLOCKED is shown only while it is still TRUE. The stored flag is set by
    # hand and was never cleared when the depended-on ticket finished, so a card
    # could sit flagged for weeks after nothing was actually blocking it. Resolve
    # it against the dependency's live status and name the blocker.
    flag = ""
    if r["blocked"]:
        dep = r["depends_on"]
        dep_status = (blockers or {}).get(dep)
        if dep is None:
            flag = " [BLOCKED]"
        elif dep_status != "done":
            flag = f" [BLOCKED by #{dep}]"
        else:
            flag = f" [blocked flag is STALE — #{dep} is done; clear it]"
    who = (r["assignee"] or "").strip() or f"(epic:{r['epic_owner']})"
    return (f"  {r['status']:5} p{r['priority']:>3} {r['estimate'] or '-':>4}  "
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
    """One line per link on a task. Issue links are a single symmetric row, so
    both ends are found with `task_id=? OR other_id=?`. [] if the table predates
    this feature."""
    out: list[str] = []
    try:
        rows = conn.execute(
            "SELECT l.task_id, l.other_id, ta.title, tb.title "
            "FROM task_link l "
            "LEFT JOIN task ta ON ta.id = l.task_id "
            "LEFT JOIN task tb ON tb.id = l.other_id "
            "WHERE l.kind='issue' AND (l.task_id=? OR l.other_id=?) ORDER BY l.id",
            (task_id, task_id),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    for a, b, title_a, title_b in rows:
        far, title = (b, title_b) if a == task_id else (a, title_a)
        out.append(f"ticket #{far} — {title or '(missing)'}")
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
    cur = conn.cursor()

    print(f"=== CoS Ticket status ({db_path}) ===\n")

    ms = cur.execute("SELECT name FROM theme WHERE is_milestone=1").fetchone()
    print(f"DIRECTION — current milestone: {ms['name'] if ms else '(none set)'}")

    actives = cur.execute(
        "SELECT name FROM epic WHERE status IN ('active','planning') ORDER BY id"
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
              f"[{nxt['epic']}] {nxt['title']}  (p{nxt['priority']}, {nxt['estimate'] or '?'})")
        print("\nYOUR QUEUE (active board, doing→todo, priority order):")
        print("  Work it top to bottom. A `doing` card outranks every `todo`.")
        blockers = blocker_statuses(conn, board)
        for r in mine_q:
            print(fmt(r, blockers))
    else:
        bl = my_backlog(conn, ME)
        print(f"▶ YOUR NEXT ACTION ({ME}): nothing on the active board (no doing/todo).")
        if bl:
            print("   Fallback — your backlog (activate one onto the board before executing):")
            for r in bl[:5]:
                print(f"     backlog p{r['priority']:>3}  [{r['epic']}] {r['title']}")
        else:
            print("   Your backlog is also empty — await direction.")

    print_comments(conn, mine_all)
    print_links(conn, mine_all)
    print_attachments(conn, mine_all, db_path)

    print("\n--- FLEET (active-board items owned by OTHER agents — context only, not yours) ---")
    if others_q:
        for r in others_q:
            print(fmt(r, blocker_statuses(conn, board)))
    else:
        print("  (none)")

    _tail(cur, conn)


def _tail(cur: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    # No handoff section by design. A session's carry-forward IS its cards: work
    # left mid-flight is a `doing` card on the active board with a real owner and
    # priority. There is no per-agent narrative block, because a note saying
    # "where things stand" is work state living somewhere other than a ticket.
    conn.close()


if __name__ == "__main__":
    main()
