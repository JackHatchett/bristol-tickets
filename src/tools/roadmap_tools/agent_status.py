#!/usr/bin/env python3
"""
agent_status.py — lightweight roadmap status reader for non‑CoS agents.

Machine-readable snapshot SCOPED TO ONE AGENT:
    - current milestone (fleet-wide; same for every agent)
    - the active board size (fleet-wide; stage='active')
    - this agent's own next action + own active-board queue
    - COMMENTS on this agent's active-board tasks (issue_log); user-authored
      ones flagged ⚠ — on-ticket decisions/direction a bare status line hides

Uses ONLY relative project structure under /agent_system. No personal data,
no usernames, no environment variables.

DB discovery rule:
    agent_system/src/tools/roadmap_tools/agent_status.py → parents[2] →
    agent_system/ → search data/*/roadmap/roadmap.db. There is ONE shared
    roadmap.db for the whole fleet; this script slices it to one agent.

NEXT-ACTION SEMANTICS (aligned with cos_status.py):
    An agent's next action is its OWN work, scoped to the ACTIVE BOARD
    (task.stage='active'), in precedence: active-board `doing` (priority desc) →
    active-board `todo` (priority desc) → (fallback only if both empty) own
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

STATUS_RANK = {"doing": 0, "todo": 1}


# ---------------------------------------------------------------------------
# DB PATH RESOLUTION (canonical)
# ---------------------------------------------------------------------------

def resolve_db_path() -> Path:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[2]          # agent_system/
    data_root = project_root / "data"

    matches = list(data_root.glob("*/roadmap/roadmap.db"))
    if not matches:
        sys.exit("agent_status: ERROR — no roadmap.db found under agent_system/data/*/roadmap/")
    return matches[0]


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
    """Backlog-stage tasks owned by me. Epic-less tasks included;
    epic'd ones limited to active/planning epics to cut noise. Priority desc."""
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
    user-authored ones (context to read, NOT a priority signal — priority/stage
    decide the next task, never a comment)."""
    latest = latest_comment_per_task(conn, [t["id"] for t in tasks])
    if not latest:
        return
    print("\n--- COMMENTS on your active-board tasks (⚠ = user; context to read, NOT a priority signal) ---")
    for t in tasks:
        c = latest.get(t["id"])
        if not c:
            continue
        mark = "⚠ " if (c["author"] or "").strip() == "user" else "  "
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
    return (f"  {r['status']:5} p{r['priority']:>3} {r['estimate'] or '-':>4}  "
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
    cur = conn.cursor()

    print(f"=== Agent Roadmap Status: {me} ({db_path}) ===\n")

    ms = cur.execute("SELECT name FROM theme WHERE is_milestone=1").fetchone()
    print(f"MILESTONE: {ms['name'] if ms else '(none set)'}")

    # This agent's own active epics (context)
    owner_like = f"%{me}%"
    actives = cur.execute(
        "SELECT name FROM epic WHERE status IN ('active','planning') "
        "AND owner LIKE ? ORDER BY id",
        (owner_like,),
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
              f"[{nxt['epic']}] {nxt['title']}  (p{nxt['priority']}, {nxt['estimate'] or '?'})")
        print("\nYOUR QUEUE (active board, doing→todo, priority order):")
        print("  Work it top to bottom. A `doing` card outranks every `todo`.")
        blockers = blocker_statuses(conn, board)
        for r in mine_q:
            print(fmt(r, blockers))
    else:
        bl = my_backlog(conn, me)
        print(f"▶ NEXT ACTION ({me}): nothing on the active board (no doing/todo).")
        if bl:
            print("   Fallback — your backlog (activate one onto the board before executing):")
            for r in bl[:5]:
                print(f"     backlog p{r['priority']:>3}  [{r['epic']}] {r['title']}")
        else:
            print("   Your backlog is also empty — await direction.")

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
