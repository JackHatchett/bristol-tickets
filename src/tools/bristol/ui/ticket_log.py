"""ui/ticket_log.py — a card's log as the views show it, and the clock it is read
against.

A card's log merges two sources: ``issue_log`` comments, written by a person or
an agent, and ``task_event`` changes, written by the database triggers. This
module reads both and renders their timestamps; it builds no widget.
"""

from __future__ import annotations

from datetime import datetime, timezone


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    """Today as the board writes a date, so a due date can be compared against
    it as plain text."""
    return datetime.now().strftime("%Y-%m-%d")


def log_lines(conn, task_id: int, comments: bool = True, changes: bool = True) -> list[str]:
    """One ticket's log as display lines, newest first.

    Two kinds share the list: `issue_log` comments, written by a person or an
    agent, and `task_event` changes, written by the database triggers. Each kind
    is toggled by its own checkbox in the views, so this returns whichever were
    asked for, merged in time order.

    A change line carries the field and its new value only; title and
    description changes arrive as '(changed)' from the trigger, so no ticket
    text is ever duplicated into the log.
    """
    entries: list[tuple[str, int, int, str]] = []
    if comments:
        try:
            for row_id, author, body, ts in conn.execute(
                "SELECT id, author, body, created_at FROM issue_log WHERE task_id=?",
                (task_id,),
            ).fetchall():
                entries.append((ts or "", 0, row_id, f"[{_fmt_dt(ts)}] {author}: {body}"))
        except Exception:
            pass
    if changes:
        try:
            for row_id, at, actor, field, to_value in conn.execute(
                "SELECT id, at, actor, field, to_value FROM task_event WHERE task_id=?",
                (task_id,),
            ).fetchall():
                entries.append(
                    (
                        at or "",
                        1,
                        row_id,
                        f"[{_fmt_dt(at)}] {actor or 'unknown'} · {field}: {to_value}",
                    )
                )
        except Exception:
            pass
    # Row id breaks ties: several fields changed by one write share a timestamp,
    # and the newest of them should still sort to the top.
    entries.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return [line for _, _, _, line in entries]


def log_entries(conn, task_id: int, comments: bool = True, changes: bool = True) -> list[dict]:
    """One ticket's log as structured entries, newest first — what the detail
    pane's timeline renders from. Same two sources and the same merge order as
    ``log_lines``; each entry is a dict:

    * a comment: ``{"kind": "comment", "author", "at", "body"}``
    * a change:  ``{"kind": "change", "author", "at", "field", "value"}``
    """
    rows: list[tuple[str, int, int, dict]] = []
    if comments:
        try:
            for row_id, author, body, ts in conn.execute(
                "SELECT id, author, body, created_at FROM issue_log WHERE task_id=?",
                (task_id,),
            ).fetchall():
                rows.append(
                    (
                        ts or "",
                        0,
                        row_id,
                        {
                            "kind": "comment",
                            "author": author or "unknown",
                            "at": ts,
                            "body": body or "",
                        },
                    )
                )
        except Exception:
            pass
    if changes:
        try:
            for row_id, at, actor, field, to_value in conn.execute(
                "SELECT id, at, actor, field, to_value FROM task_event WHERE task_id=?",
                (task_id,),
            ).fetchall():
                rows.append(
                    (
                        at or "",
                        1,
                        row_id,
                        {
                            "kind": "change",
                            "author": actor or "unknown",
                            "at": at,
                            "field": field,
                            "value": to_value,
                        },
                    )
                )
        except Exception:
            pass
    rows.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return [entry for _, _, _, entry in rows]


def relative_time(value: str | None) -> str:
    """A stored ISO timestamp as the distance back it reads from now — "just
    now", "20m ago", "3h ago", "5d ago" — falling back to the compact date once
    it is over a month old, or for a value that does not parse."""
    if not value:
        return "—"
    try:
        then = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return _fmt_dt(value)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - then).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    if seconds < 31 * 86400:
        return f"{int(seconds // 86400)}d ago"
    return _fmt_dt(value)


def _fmt_dt(value: str | None) -> str:
    """Render a stored ISO timestamp as a compact 'YYYY-MM-DD HH:MM' for the
    inspector. Falls back gracefully for missing or non-ISO values."""
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(value)[:16]
