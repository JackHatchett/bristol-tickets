"""finishing.py — what a card reaching done, or leaving it, means for the board.

The Done column holds work waiting for something. A project card waits for its
epic to close, which archives it and writes that epic's report — `epic_closure`.
A standing card waits for nothing, so it is never in Done: finishing it is what
archives it, and the board has no sweep button because the two kinds of card
each leave on their own event.

Every writer that takes a card to done calls `finish`, and every writer that
takes one out of done calls `reopen`, so the rule cannot be half-applied. The
callers are Bristol Tickets' board drop, record dialog and detail pane, and
`src/tools/ticket_tools/ticket_write.py`'s `update-task-status`. Neither
function commits: each is part of the write its caller is already making.
"""

from __future__ import annotations

import sqlite3

# Mirrors create_tickets.EPIC_KIND_STANDING, as epic_closure does, so the
# viewer carries its own copy of the board's vocabulary.
STANDING_KIND = "standing"


def standing_epic(conn: sqlite3.Connection) -> int | None:
    """The board's standing workstream, or None where it has none.

    One epic per board carries `epic.type` = 'standing' and never closes. A
    board provisioned empty has no such epic until someone opens one, and the
    rules below say what happens in the meantime rather than inventing one.
    """
    row = conn.execute(
        "SELECT id FROM epic WHERE LOWER(COALESCE(type,'')) = ? ORDER BY id",
        (STANDING_KIND,)).fetchone()
    return row[0] if row else None


def standing_conflict(conn: sqlite3.Connection, epic_id=None) -> str | None:
    """The reason this epic may not be made the standing workstream, or None.

    One epic per board is the standing workstream. A second would divide upkeep
    between two homes, and every rule that reaches for "the" standing epic would
    pick whichever was opened first.
    """
    held = standing_epic(conn)
    if held is None or held == epic_id:
        return None
    name = conn.execute("SELECT name FROM epic WHERE id=?",
                        (held,)).fetchone()[0] or f"#{held}"
    return (f"{name} is already this board's standing workstream, and a board "
            "has one. Make that epic a project first, or keep this one a "
            "project.")


def _append_to(conn: sqlite3.Connection, stage: str, status: str | None) -> int:
    """The bottom of the list a card is moving into: one active-board status
    column, or the whole of any other tab."""
    if stage == "active":
        return conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM task "
            "WHERE stage='active' AND status=?", (status,)).fetchone()[0] + 1
    return conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage=?",
        (stage,)).fetchone()[0] + 1


def finish(conn: sqlite3.Connection, task_id: int) -> bool:
    """Settle a card that has just been taken to done. True where it left the
    board.

    A card with no epic is standing by definition, so it is attributed to the
    standing workstream before it is archived and nothing reaches the Archive
    unattributed. A project card stays in Done until its epic closes. A board
    with no standing workstream has nothing to attribute an epicless card to, so
    that card stays in Done as well.
    """
    row = conn.execute(
        "SELECT epic_id, COALESCE(stage,'active') FROM task WHERE id=?",
        (task_id,)).fetchone()
    if row is None:
        return False
    epic_id, stage = row
    standing = standing_epic(conn)
    if standing is None:
        return False
    if epic_id is None:
        conn.execute("UPDATE task SET epic_id=? WHERE id=?", (standing, task_id))
        epic_id = standing
    if epic_id != standing:
        return False
    if stage != "archive":
        conn.execute("UPDATE task SET stage='archive', sort_order=? WHERE id=?",
                     (_append_to(conn, "archive", None), task_id))
    return True


def reopen(conn: sqlite3.Connection, task_id: int) -> bool:
    """Return a card that has just been taken out of done to the active board.
    True where it moved.

    Archiving is what finishing a standing card does, so unfinishing one has to
    undo it or the card would be unreachable from the board it belongs on.
    """
    row = conn.execute(
        "SELECT COALESCE(stage,'active'), status FROM task WHERE id=?",
        (task_id,)).fetchone()
    if row is None or row[0] != "archive":
        return False
    conn.execute("UPDATE task SET stage='active', sort_order=? WHERE id=?",
                 (_append_to(conn, "active", row[1]), task_id))
    return True
