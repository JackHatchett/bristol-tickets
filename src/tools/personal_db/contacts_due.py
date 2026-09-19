#!/usr/bin/env python3
"""
contacts_due.py — who is owed something today.

Reads `v_contact_due` and nothing else. The view is where the question "is this
due" is answered — a cadence that has come round, an open ask past the date it
was given — so a second copy of that arithmetic here would be a second answer.

Silent when nothing is due: a daily program that prints a heading over an empty
list teaches the reader to skim it.

Run: PERSONAL_DB_DIR=... python3 src/tools/personal_db/contacts_due.py
         [--json] [--capture]

`--capture` writes the day's list into the notebook's capture inbox as one
dated note, which is where a contact coming due reaches the user: calling a
friend is his and not an agent's, so it is never a card.
"""

import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "src" / "tools"))
import db_common as dbc  # noqa: E402


def due_rows() -> list[dict]:
    """Every row the view returns, overdue first and today's after it."""
    conn = dbc.connect()
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT contact_id, name, reason, ask_id, kind, since, due_on "
            "FROM v_contact_due")]
    finally:
        conn.close()
    today = datetime.date.today().isoformat()
    for row in rows:
        row["overdue"] = bool(row["due_on"] and row["due_on"] < today)
    rows.sort(key=lambda r: (not r["overdue"], r["due_on"] or "", r["name"]))
    return rows


def _line(row: dict) -> str:
    when = row["due_on"] or "no date"
    if row["reason"] == "cadence":
        since = f"last contact {row['since']}" if row["since"] else "never contacted"
        return f"  {row['name']} — {since}, due {when}"
    return (f"  {row['name']} — ask #{row['ask_id']} ({row['kind']}), "
            f"opened {row['since']}, due {when}")


def capture(rows: list[dict], today: str | None = None,
            folder: Path | None = None) -> Path | None:
    """Write the day's due list into the notebook's capture inbox, and return
    the file. None where nothing is due: a capture saying nothing is due is a
    note the user has to open to learn nothing.

    One file per day, rewritten by a second run on the same day, because what is
    due is a statement about today rather than a log of when it was asked.
    """
    if not rows:
        return None
    from config_tools import data_paths, read_config

    day = today or datetime.date.today().isoformat()
    folder = (Path(folder) if folder is not None
              else data_paths.ensure_dir(read_config.get("markdown_notebook.inbox_dir")))
    folder.mkdir(parents=True, exist_ok=True)
    written = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    spoken = datetime.date.fromisoformat(day).strftime("%-d %B %Y")
    title = f"Contacts Due {spoken}"
    lines = [
        "---",
        "aliases:",
        f"  - {title}",
        "tags:",
        "  - ai/advice",
        f"created: {written}",
        "---",
        "",
        f"# {title}",
        "",
        f"{len(rows)} person or ask is owed something today."
        if len(rows) == 1 else
        f"{len(rows)} people or asks are owed something today.",
        "",
    ]
    for row in rows:
        late = "overdue" if row["overdue"] else "due today"
        if row["reason"] == "cadence":
            since = (f"last contact {row['since']}" if row["since"]
                     else "never contacted")
            lines.append(f"- **{row['name']}** — {since}, {late} "
                         f"({row['due_on'] or 'no date'}).")
        else:
            lines.append(f"- **{row['name']}** — {row['kind']} opened "
                         f"{row['since']}, {late} ({row['due_on']}).")
    lines.append("")
    target = folder / f"contacts_due_{day}.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rows = due_rows()
    if "--json" in argv:
        print(json.dumps(rows, indent=2))
        return 0
    if "--capture" in argv:
        written = capture(rows)
        if written is not None:
            print(f"wrote {written}")
        return 0
    if not rows:
        return 0
    overdue = [r for r in rows if r["overdue"]]
    today = [r for r in rows if not r["overdue"]]
    if overdue:
        print(f"Overdue ({len(overdue)}):")
        for row in overdue:
            print(_line(row))
    if today:
        print(f"Due today ({len(today)}):")
        for row in today:
            print(_line(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
