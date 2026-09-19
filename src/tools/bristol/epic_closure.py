"""epic_closure.py — closing an epic: its finished cards leave the board, and
the report for that effort is written.

A Kanban board has no sprints, so the period is the epic. A project epic is
opened for an effort, its cards close under it, and closing it is what says the
effort is over, so that is the moment its finished cards leave the board and its
report is written.

Both front ends call in here — Bristol Tickets' epic dialog and
`src/tools/ticket_tools/ticket_write.py`'s `update-epic` — so the act is the same
from either. Nothing here imports Qt: it takes an open connection and returns
what happened.
"""

from __future__ import annotations

import sqlite3

# Mirrors create_tickets.EPIC_KIND_STANDING and EPIC_STATUS_FINISHED, following
# this repo's convention that Bristol Tickets carries its own copy of shared
# board vocabulary rather than importing the CLI's package, since the viewer
# also ships as a relocatable .app.
STANDING_KIND = "standing"
FINISHED_STATUSES = frozenset({"completed", "done"})


class ClosureResult:
    """What the closure did, in a form both front ends can act on."""

    def __init__(self, archived=(), reported=(), refused=None, report=None):
        self.archived = list(archived)   # cards this closure moved to the Archive
        self.reported = list(reported)   # cards the report covers
        self.refused = refused           # str, when the epic may not be closed
        self.report = report             # the reports package's own result

    @property
    def ok(self):
        return self.refused is None

    def __str__(self):
        if self.refused:
            return f"refused: {self.refused}"
        said = f"archived {len(self.archived)} card(s)"
        if self.report is not None:
            said += f"; {self.report}"
        return said


def refusal(conn: sqlite3.Connection, epic_id: int) -> str | None:
    """Why this epic may not be closed, or None where it may.

    Asked before the status is written, so a refused closure never leaves an
    epic marked finished with nothing having happened.
    """
    row = conn.execute("SELECT type, name FROM epic WHERE id=?", (epic_id,)).fetchone()
    if row is None:
        return f"no epic with id {epic_id}"
    kind, name = (row[0] or ""), (row[1] or f"#{epic_id}")
    if kind.strip().lower() == STANDING_KIND:
        return (f"{name} is the standing workstream, which never closes — there "
                "is no effort to end, so it is measured over a date range "
                "instead")
    return None


def _finished_cards(conn: sqlite3.Connection, epic_id: int) -> list[int]:
    """The epic's cards that are finished — what it closed with.

    A card still open when the effort ends is not work this period delivered, so
    it is left out of the report and left where it is on the board.
    """
    return [row[0] for row in conn.execute(
        "SELECT id FROM task WHERE epic_id=? AND status='done' ORDER BY id",
        (epic_id,))]


def _archive(conn: sqlite3.Connection, task_ids: list[int]) -> list[int]:
    """Move each card to the Archive, appended to the bottom of its order. The
    change log records the tab move itself, from the triggers on this
    connection."""
    moved = []
    for task_id in task_ids:
        base = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage='archive'"
        ).fetchone()[0]
        conn.execute("UPDATE task SET stage='archive', sort_order=? WHERE id=?",
                     (base + 1, task_id))
        moved.append(task_id)
    return moved


def close_epic(conn: sqlite3.Connection, epic_id: int, now=None,
               out_dir=None) -> ClosureResult:
    """Archive the epic's finished cards and write the report for that effort.

    The board write commits before the report is attempted, so an unreachable
    notebook folder costs the report and nothing else. An epic reopened and
    closed again reports what it closed with the second time, and the first
    report is never touched: a report is an artefact of the moment it was
    written.
    """
    refused = refusal(conn, epic_id)
    if refused:
        return ClosureResult(refused=refused)

    reported = _finished_cards(conn, epic_id)
    pending = [task_id for task_id in reported if conn.execute(
        "SELECT COALESCE(stage,'active') FROM task WHERE id=?",
        (task_id,)).fetchone()[0] != "archive"]
    archived = _archive(conn, pending)
    conn.commit()

    try:
        from reports.generate import generate_report_safe
    except ImportError:
        # A stripped bundle may not carry the reports package at all.
        return ClosureResult(archived=archived, reported=reported)

    report = generate_report_safe(conn, reported, now=now, out_dir=out_dir)
    return ClosureResult(archived=archived, reported=reported, report=report)
