#!/usr/bin/env python3
"""
build_reading_list_notes.py — one Markdown checklist note per reading list.

Every reading-list collection in Zotero becomes a note in the Markdown
notebook's inbox, so a list can be ticked off in the notebook without opening
Zotero. Each line carries the title, the author and a zotero:// link that opens
that exact item.

A book the user has already read is ticked when its line is first written.
After that the note belongs to the user: re-running keeps whatever they have
ticked or unticked and only appends lines for entries that are new to the list.
Nothing is ever deleted from a note by this script except a line whose item has
left the collection.

Which collections count as reading lists: any collection holding at least one
book, minus the read set itself and the ownership view — neither is a list to
work through. That rule keeps clipping collections (web pages, talks) out
without naming them.

Path resolution (no personal paths in /src):
  1. READING_LIST_NOTES_DIR env var        — explicit override
  2. config/config.local.json              — markdown_notebook.notes_dir, plus
                                             the inbox folder below it
  ZOTERO_DATA_DIR is resolved by zotero_common.

Usage:
    python3 build_reading_list_notes.py [--dry-run] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import zotero_common as zc  # noqa: E402

READ_COLLECTION = "Books I've Read"
OWNED_COLLECTION = "Owned"
INBOX_FOLDER = "00_inbox"
FILENAME_PREFIX = "reading_list_"

_ENV_VAR = "READING_LIST_NOTES_DIR"
_CONFIG_KEY = ("markdown_notebook", "notes_dir")

# A line this script wrote: tick state, then somewhere in it the item key.
_LINE_RE = re.compile(r"^- \[(?P<tick>[ xX])\] .*items/(?P<key>[A-Z0-9]{8})\)")


# ------------------------------------------------------------------- locations


def _notes_dir_from_config() -> Path | None:
    root = zc._project_root()
    config_path = Path(
        os.environ.get("CONFIG_LOCAL_JSON") or (root / "config" / "config.local.json")
    ).expanduser()
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for key in _CONFIG_KEY:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    if not isinstance(data, str) or not data:
        return None
    return Path(os.path.expanduser(data))


def resolve_inbox(explicit: str | os.PathLike | None = None) -> Path:
    if explicit:
        return Path(os.path.expanduser(str(explicit)))
    env = os.environ.get(_ENV_VAR)
    if env:
        return Path(os.path.expanduser(env))
    notes = _notes_dir_from_config()
    if notes is None:
        raise SystemExit(
            "Cannot resolve the notebook. Set READING_LIST_NOTES_DIR, pass "
            "--out-dir, or add markdown_notebook.notes_dir to config."
        )
    return notes / INBOX_FOLDER


def slug(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


# ---------------------------------------------------------------------- zotero


def reading_lists(conn):
    """[(collectionID, key, name)] for every collection that is a reading list."""
    rows = conn.execute(
        """
        SELECT c.collectionID, c.key, c.collectionName,
               SUM(CASE WHEN it.typeName = 'book' THEN 1 ELSE 0 END) AS books
        FROM collections c
        JOIN collectionItems ci ON ci.collectionID = c.collectionID
        JOIN items i            ON i.itemID = ci.itemID
        JOIN itemTypes it       ON it.itemTypeID = i.itemTypeID
        WHERE c.libraryID = ?
        GROUP BY c.collectionID
        HAVING books > 0
        ORDER BY c.collectionName
        """,
        (zc.USER_LIBRARY_ID,),
    ).fetchall()
    skip = {READ_COLLECTION, OWNED_COLLECTION}
    return [r for r in rows if r["collectionName"] not in skip]


def read_item_ids(conn) -> set:
    return {
        r[0]
        for r in conn.execute(
            """
            SELECT ci.itemID FROM collectionItems ci
            JOIN collections c ON c.collectionID = ci.collectionID
            WHERE c.collectionName = ? AND c.libraryID = ?
            """,
            (READ_COLLECTION, zc.USER_LIBRARY_ID),
        )
    }


def collection_entries(conn, collection_id):
    """[(itemID, key, title, author)] in the collection's own order."""
    title_fid = zc.field_id(conn, "title")
    rows = conn.execute(
        """
        SELECT i.itemID, i.key, dv.value AS title, ci.orderIndex
        FROM collectionItems ci
        JOIN items i             ON i.itemID = ci.itemID
        LEFT JOIN itemData d     ON d.itemID = i.itemID AND d.fieldID = ?
        LEFT JOIN itemDataValues dv ON dv.valueID = d.valueID
        LEFT JOIN deletedItems del  ON del.itemID = i.itemID
        WHERE ci.collectionID = ? AND del.itemID IS NULL
        ORDER BY ci.orderIndex, i.itemID
        """,
        (title_fid, collection_id),
    ).fetchall()

    creators = {}
    for r in conn.execute(
        """
        SELECT ic.itemID, c.lastName, c.firstName, c.fieldMode
        FROM itemCreators ic
        JOIN creators c ON c.creatorID = ic.creatorID
        ORDER BY ic.orderIndex
        """
    ):
        if r["itemID"] in creators:
            continue
        if r["fieldMode"] == 1 or not r["firstName"]:
            creators[r["itemID"]] = r["lastName"]
        else:
            creators[r["itemID"]] = f"{r['lastName']}, {r['firstName']}"

    return [
        (r["itemID"], r["key"], r["title"] or "(untitled)", creators.get(r["itemID"], ""))
        for r in rows
    ]


# ----------------------------------------------------------------------- notes


def existing_ticks(path: Path) -> dict:
    """{item key: True/False} for lines already in the note, so edits survive."""
    if not path.exists():
        return {}
    ticks = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _LINE_RE.match(line.strip())
        if m:
            ticks[m.group("key")] = m.group("tick").lower() == "x"
    return ticks


def render(name, coll_key, entries, read_ids, ticks) -> str:
    lines = [
        f"# {name}",
        "",
        f"[Open the collection in Zotero](zotero://select/library/collections/{coll_key})",
        "",
        f"{len(entries)} titles. Ticks are yours — regenerating this note keeps them.",
        "",
    ]
    for item_id, key, title, author in entries:
        # A line already in the note keeps the user's tick. A line that is new
        # starts ticked when the book is in the read set.
        done = ticks[key] if key in ticks else item_id in read_ids
        box = "x" if done else " "
        who = f" — {author}" if author else ""
        lines.append(
            f"- [{box}] **{title}**{who} · [Zotero](zotero://select/library/items/{key})"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    ap.add_argument("--out-dir", help="write the notes here instead of the inbox")
    args = ap.parse_args()

    inbox = resolve_inbox(args.out_dir)
    if not args.dry_run:
        if not inbox.parent.is_dir():
            raise SystemExit(f"Notebook not present at {inbox.parent} — nothing written.")
        inbox.mkdir(parents=True, exist_ok=True)

    conn = zc.connect(read_only=True)
    try:
        read_ids = read_item_ids(conn)
        lists = reading_lists(conn)
        reports = []
        for row in lists:
            entries = collection_entries(conn, row["collectionID"])
            path = inbox / f"{FILENAME_PREFIX}{slug(row['collectionName'])}.md"
            ticks = existing_ticks(path)
            body = render(row["collectionName"], row["key"], entries, read_ids, ticks)
            ticked = body.count("- [x]")
            if not args.dry_run:
                path.write_text(body, encoding="utf-8")
            reports.append((row["collectionName"], len(entries), ticked, path.name,
                            "updated" if ticks else "new"))
    finally:
        conn.close()

    width = max(len(r[0]) for r in reports)
    for name, n, ticked, fname, state in reports:
        print(f"{name:<{width}}  {n:>5} titles  {ticked:>5} ticked  {state:<7} {fname}")
    print(f"\n{len(reports)} notes in {inbox}")
    if args.dry_run:
        print("(dry run — nothing written)")


if __name__ == "__main__":
    main()
