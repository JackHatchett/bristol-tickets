"""clear_done.py — clearing the Done column: every finished card on the board
moves to the Archive, and one report covers them, from the earliest of their
creations to now.

A project card otherwise leaves Done only when its epic closes
(`epic_closure.py`). Clearing Done is the user's second period boundary, for an
effort still open or never closed. An epic closed afterwards still reports
every finished card it contains, archived here or not, because its closure reads
the epic's done cards whatever their tab.

Each card keeps its own `closed_at`; the Archive orders by the change log's
record of the tab move. Settings' Clear Done button calls in here, and nothing
here imports Qt.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from epic_closure import _archive


class ClearResult:
    """What the sweep did, in a form a front end can act on."""

    def __init__(self, archived=(), report=None):
        self.archived = list(archived)   # cards moved to the Archive
        self.report = report             # the reports package's own result

    def __str__(self):
        said = f"archived {len(self.archived)} card(s)"
        if self.report is not None:
            said += f"; {self.report}"
        return said


def done_cards(conn: sqlite3.Connection) -> list[int]:
    """The cards in the Done column: on the board, and finished."""
    return [row[0] for row in conn.execute(
        "SELECT id FROM task WHERE COALESCE(stage,'active')='active' "
        "AND status='done' ORDER BY id")]


def clear_done(conn: sqlite3.Connection, now=None, out_dir=None) -> ClearResult:
    """Archive every card in the Done column and write the report for them.

    The board write commits before the report is attempted, so an unreachable
    notebook folder costs the report and nothing else.
    """
    ids = done_cards(conn)
    if not ids:
        return ClearResult()

    marks = ",".join("?" * len(ids))
    start = conn.execute(
        f"SELECT MIN(created_at) FROM task WHERE id IN ({marks})", ids
    ).fetchone()[0]
    now = now or datetime.now(timezone.utc).isoformat()

    archived = _archive(conn, ids)
    conn.commit()

    try:
        from reports.generate import generate_report_safe
    except ImportError:
        # A stripped bundle may not carry the reports package at all.
        return ClearResult(archived=archived)

    report = generate_report_safe(conn, archived, now=now, out_dir=out_dir,
                                  period_start=start, period_end=now)
    return ClearResult(archived=archived, report=report)
