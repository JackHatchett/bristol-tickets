"""
status_common.py — the board read that both status front ends share.

Every rule about how a queue is read lives here and nowhere else: what a task's
owner is, the precedence that orders a queue, which comments, links, carried
summaries and attachments a snapshot surfaces, and how a card is formatted. The
two front ends — `cos_status.py` and `agent_status.py` — hold their own slug,
their own headings, and, for chief_of_staff, the fleet section. Nothing else.

Which script an agent runs stays two commands rather than a flag, because that
choice is an identity rather than an option — `src/app.md` Phase 3.1.

DB discovery, the Kanban model, the next-action precedence and the reason a
`sqlite3` CLI binary is never shelled out to are all
`src/tools/ticket_tools/README.md`.
"""

import os
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
                   tasks: list[sqlite3.Row]) -> set[int]:
    """Surface the latest comment on each of `tasks` that has one. User-authored
    latest comments are flagged ⚠ as context to read — they are NOT a pressure
    signal and never reroute which task is next (pressure/stage decide that)."""
    latest = latest_comment_per_task(conn, [t["id"] for t in tasks])
    if not latest:
        return set()
    shown: set[int] = set()
    print("\n--- COMMENTS on your active-board tasks (⚠ = user; context to read, NOT a pressure signal) ---")
    for t in tasks:
        c = latest.get(t["id"])
        if not c:
            continue
        shown.add(t["id"])
        is_user = (c["author"] or "").strip() == "user"
        mark = "⚠ " if is_user else "  "
        body = " ".join((c["body"] or "").split())
        if len(body) > 300:
            body = body[:297] + "..."
        print(f"{mark}#{t['id']} [{c['created_at'][:10]} {c['author']}] {body}")
    return shown


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
        position: int | None = None, *, show_owner: bool = False) -> str:
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
    if show_owner:
        who = (r["assignee"] or "").strip() or f"(epic:{r['epic_owner']})"
        flag = f"  <{who}>{flag}"
    pos = f"{position:>2}." if position is not None else "   "
    return (f"  {pos} {r['status']:5} pr{r['pressure']:>3} {r['estimate'] or '-':>4}  "
            f"[{r['epic']}] {r['title']}{flag}")


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


def carried_summaries(conn: sqlite3.Connection, task_id: int) -> list[tuple]:
    """The closing comment of every finished ticket that blocks `task_id`, in
    the order those tickets closed. `ui/links.py::carried_summaries` is the
    viewer's copy of this read; the two are checked against each other in the
    smoke suite rather than trusted to stay in step.

    A join, never a copy: the `blocks` row and the blocking ticket's own log are
    both read live, so editing that ticket's last comment changes what appears
    here, and nothing is stored on the blocked ticket. A blocker that has not
    finished, or finished having said nothing, contributes no entry."""
    try:
        blockers = conn.execute(
            "SELECT b.id, b.title, b.closed_at "
            "FROM task_link l JOIN task b ON b.id = l.task_id "
            "WHERE l.kind='issue' AND l.dep_type='blocks' AND l.other_id=? "
            "AND b.status='done' "
            "ORDER BY b.closed_at IS NULL, b.closed_at, b.id",
            (task_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    out: list[tuple] = []
    for blocker_id, title, _closed_at in blockers:
        last = conn.execute(
            "SELECT author, body, created_at FROM issue_log WHERE task_id=? "
            "ORDER BY id DESC LIMIT 1",
            (blocker_id,),
        ).fetchone()
        if last is None or not (last[1] or "").strip():
            continue
        out.append((blocker_id, title or "(missing)", last[0] or "",
                    last[2] or "", last[1]))
    return out


def print_carried_summaries(conn: sqlite3.Connection,
                            tasks: list[sqlite3.Row]) -> set[int]:
    """What the tickets each task waited on said as they finished, whole.

    The other sections point at something to go and read; this one is the
    reading, which is why it is not truncated. A card that has been unblocked
    starts with what the last agent decided instead of a link back into another
    ticket's log."""
    hits = [(t, carried_summaries(conn, t["id"])) for t in tasks]
    hits = [(t, rows) for t, rows in hits if rows]
    if not hits:
        return set()
    shown: set[int] = set()
    print("\n--- CARRIED SUMMARIES (how each finished blocker closed; "
          "you need not open those tickets) ---")
    for t, rows in hits:
        print(f"  #{t['id']} {t['title']}")
        for blocker_id, title, author, at, body in rows:
            shown.add(blocker_id)
            print(f"    ← #{blocker_id} {title} [{at[:10]} {author}]")
            for line in (body or "").splitlines():
                print(f"        {line}")
    return shown


# How many finished cards a session opens with. Three, because a closing
# comment here is a paragraph rather than a run record: five of them displaces
# the queue this section exists to orient, and the section points at the board
# rather than standing in for reading it.
ROLE_HISTORY_CARDS = 3

# A closing comment is shown here to orient and not to be worked from, so it is
# cut. The whole of it is on the card.
ROLE_HISTORY_CHARS = 400


def role_history(conn: sqlite3.Connection, me: str,
                 limit: int = ROLE_HISTORY_CARDS) -> list[tuple]:
    """This agent's most recently finished cards, and how each one closed.

    A read-time join over `task` and `issue_log` across every epic and both the
    active board and the archive. Nothing is stored: a closing comment edited
    later reads differently here the next time, and there is no second copy to
    go stale.

    Ownership is `task.assignee` — the same key that decides the queue. The
    change log records which actor moved a card to `done`, and reading it here
    would be the more literal answer to "who closed it", but a third of finished
    cards carry no such row, so an agent's history would silently shorten the
    further back it reached.
    """
    try:
        rows = conn.execute(
            "SELECT t.id, t.title, t.closed_at, "
            "       COALESCE(e.name, '(no epic)') AS epic "
            "FROM task t LEFT JOIN epic e ON t.epic_id = e.id "
            "WHERE t.assignee = ? AND t.status = 'done' "
            "ORDER BY t.closed_at IS NULL, t.closed_at DESC, t.id DESC "
            "LIMIT ?",
            (me, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    out: list[tuple] = []
    for r in rows:
        last = conn.execute(
            "SELECT body FROM issue_log WHERE task_id=? ORDER BY id DESC LIMIT 1",
            (r["id"],),
        ).fetchone()
        body = " ".join(((last[0] if last else "") or "").split())
        out.append((r["id"], r["title"] or "(missing)", r["epic"],
                    (r["closed_at"] or "")[:10], body))
    return out


def print_role_history(conn: sqlite3.Connection, me: str,
                       already_shown: set[int]) -> None:
    """What this agent last finished, so a session starts inside its role.

    Printed last, after the queue and everything the queue points at, because it
    is continuity rather than work.

    `already_shown` is every card whose comment this read has printed above. One
    of those keeps its line and loses its body: the same comment twice in one
    status read teaches the reader to skim both.
    """
    rows = role_history(conn, me)
    if not rows:
        return
    print(f"\n--- LAST FINISHED by {me} ({len(rows)} most recent, any epic; "
          f"continuity, not a queue) ---")
    for tid, title, epic, closed, body in rows:
        print(f"  #{tid} [{epic}] {title}  (closed {closed})")
        if not body:
            continue
        if tid in already_shown:
            print("      (its closing comment is printed above)")
            continue
        if len(body) > ROLE_HISTORY_CHARS:
            body = body[:ROLE_HISTORY_CHARS - 3] + "..."
        print(f"      {body}")


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
# The snapshot's shared body
# ---------------------------------------------------------------------------

def open_board() -> tuple[Path, sqlite3.Connection, sqlite3.Cursor]:
    """The board, ready to read: connected, journalled and brought current."""
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
    return db_path, conn, conn.cursor()


def milestone_name(cur: sqlite3.Cursor) -> str:
    row = cur.execute("SELECT name FROM theme WHERE is_milestone=1").fetchone()
    return row["name"] if row else "(none set)"


def active_epic_names(cur: sqlite3.Cursor, owner: str | None = None) -> str:
    """The in-flight epics, fleet-wide, or only those an owner's name appears in.

    `owner` is matched as a substring because an epic's owner is sometimes a
    descriptive multi-agent string rather than a bare slug.
    """
    placeholders = ",".join("?" * len(create_tickets.EPIC_STATUS_IN_FLIGHT))
    if owner is None:
        rows = cur.execute(
            f"SELECT name FROM epic WHERE status IN ({placeholders}) ORDER BY id",
            tuple(create_tickets.EPIC_STATUS_IN_FLIGHT)).fetchall()
    else:
        rows = cur.execute(
            f"SELECT name FROM epic WHERE status IN ({placeholders}) "
            f"AND owner LIKE ? ORDER BY id",
            (*create_tickets.EPIC_STATUS_IN_FLIGHT, f"%{owner}%")).fetchall()
    return ", ".join(e["name"] for e in rows) or "(none)"


def print_queue(conn: sqlite3.Connection, board: list, mine_q: list, me: str,
                *, label: str, show_owner: bool) -> None:
    """The next action and the queue under it, or the backlog fallback.

    The precedence is `src/app.md` Phase 3.2 and is computed in `queue_sort`;
    nothing here re-derives it. `label` is the front end's own wording.
    """
    if mine_q:
        nxt = mine_q[0]
        print(f"▶ {label} ({me}, active board): "
              f"[{nxt['epic']}] {nxt['title']}  (pressure {nxt['pressure']}, {nxt['estimate'] or '?'})")
        print("\nYOUR QUEUE (active board, doing→todo, board order):")
        print("  Work it top to bottom. A `doing` card outranks every `todo`.")
        blockers = unmet_blockers(conn, board)
        for n, r in enumerate(mine_q, start=1):
            print(fmt(r, blockers, position=n, show_owner=show_owner))
        return
    bl = my_backlog(conn, me)
    print(f"▶ {label} ({me}): nothing on the active board (no doing/todo).")
    if bl:
        print("   Fallback — your backlog (activate one onto the board before executing):")
        for r in bl[:5]:
            print(f"     backlog pr{r['pressure']:>3}  [{r['epic']}] {r['title']}")
    else:
        print("   Your backlog is also empty — await direction.")


def print_body(conn: sqlite3.Connection, db_path, me: str,
               mine_all: list, mine_q: list) -> None:
    """Everything under the queue, in the one order both front ends print it."""
    shown = print_comments(conn, mine_all)
    print_links(conn, mine_all)
    # Scoped to the queue rather than to every card on the board: a
    # handoff is what the agent about to work a card needs, and a card
    # already done has nothing to be handed.
    shown |= print_carried_summaries(conn, mine_q)
    print_attachments(conn, mine_all, db_path)
    print_role_history(conn, me, shown)
