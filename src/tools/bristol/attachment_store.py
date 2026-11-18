"""attachment_store.py — where a card's images live, and the row that names each.

An attachment is an image pinned to a task. Its bytes live in a git-ignored
images directory beside the tickets database (``data/<instance>/tickets/
images/``), resolved from the connection's own file; the database stores only
the filename, never an absolute path.

Removal moves the file into ``images/_trash/`` and drops the row either way, so
no view shows a row whose file is gone.

This module imports no Qt. Bristol Tickets' attachment bar
(``ui/attachments.py``) and ``src/tools/ticket_tools/ticket_write.py``'s
``add-attachment`` both call it, so the viewer and the command line store an
image the same way. Each write commits.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def images_dir(conn: sqlite3.Connection) -> Path | None:
    """The per-instance images directory (created on demand), resolved from the
    connection's own database file so nothing is hardcoded. Returns None for an
    in-memory / pathless DB."""
    try:
        row = conn.execute("PRAGMA database_list").fetchone()
        db_file = row[2] if row else None
    except sqlite3.OperationalError:
        db_file = None
    if not db_file:
        return None
    d = Path(db_file).resolve().parent / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def attachment_path(conn: sqlite3.Connection, filename: str) -> Path | None:
    """Resolve a stored attachment filename to its on-disk path (or None if the
    images dir can't be resolved). The file may not exist — the caller checks."""
    d = images_dir(conn)
    if d is None:
        return None
    return d / filename


def _safe_name(name: str) -> str:
    keep = "-_.() "
    cleaned = "".join(c if (c.isalnum() or c in keep) else "_" for c in name).strip()
    return cleaned or "image"


def list_attachments(conn: sqlite3.Connection, task_id: int | None):
    if task_id is None:
        return []
    try:
        return conn.execute(
            "SELECT id, filename, original_name FROM attachment "
            "WHERE task_id=? ORDER BY id",
            (task_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def add_attachment(conn: sqlite3.Connection, task_id: int | None, source_path: str):
    """Copy ``source_path`` into the images dir under a unique, predictable name
    and record it. Returns the stored filename, or None on failure."""
    if task_id is None:
        return None
    d = images_dir(conn)
    if d is None:
        return None
    src = Path(source_path)
    if not src.is_file():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    base = _safe_name(src.name)
    dest = d / f"task{task_id}_{stamp}_{base}"
    i = 1
    while dest.exists():  # rare same-second collision
        dest = d / f"task{task_id}_{stamp}_{i}_{base}"
        i += 1
    try:
        shutil.copy2(src, dest)
    except OSError:
        return None
    conn.execute(
        "INSERT INTO attachment (task_id, filename, original_name, created_at) "
        "VALUES (?,?,?,?)",
        (task_id, dest.name, src.name, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return dest.name


def remove_attachment(conn: sqlite3.Connection, attachment_id: int) -> None:
    """Drop the attachment record and move its file into ``images/_trash/`` (a
    recoverable soft-delete). If the move fails, the DB link is still removed so
    the UI never shows a dangling entry."""
    row = conn.execute(
        "SELECT filename FROM attachment WHERE id=?", (attachment_id,)
    ).fetchone()
    if row:
        d = images_dir(conn)
        if d is not None:
            src = d / row[0]
            if src.exists():
                trash = d / "_trash"
                trash.mkdir(parents=True, exist_ok=True)
                target = trash / src.name
                n = 1
                while target.exists():
                    target = trash / f"{src.stem}_{n}{src.suffix}"
                    n += 1
                try:
                    shutil.move(str(src), str(target))
                except OSError:
                    pass
    conn.execute("DELETE FROM attachment WHERE id=?", (attachment_id,))
    conn.commit()
