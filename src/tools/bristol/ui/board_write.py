"""ui/board_write.py — one write the app makes to tickets.db, all or nothing.

A control that changes the board runs its statements through ``write``. They
are committed together, or, when any of them fails (the board is locked while
an agent's ``ticket_write.py`` holds it, say), the connection rolls back, so no
half-made change is left open for a later commit to carry in, and the user is
told in a notice what was not saved. The caller then shows what is stored.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from .dialogs import notify


def write(conn: sqlite3.Connection, parent, what: str, work: Callable[[], object]) -> bool:
    """Run ``work`` and commit it. On a database error, roll back, say in a
    notice that ``what`` was not saved and why, and return False."""
    try:
        work()
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        notify(
            parent,
            "Change Not Saved",
            f"{what} was not saved: {exc}. The board shows what is stored.",
        )
        return False
    return True
