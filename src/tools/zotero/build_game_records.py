#!/usr/bin/env python3
"""
build_game_records.py — turn reviewed game payloads into Zotero Software items.

A game has no ISBN, so Zotero's Add Item by Identifier cannot reach one and the
record has to be assembled from published sources by hand. This script is the
last step of that: it takes a payload the user has already read and writes each
entry as a `computerProgram` item in a named collection.

Re-running is safe. An entry whose title already exists as a Software item is
reused and only added to the collection; nothing is overwritten, so a payload
can be corrected and replayed.

FIELD MAP — payload key : Zotero field, and why where a choice was made.

    title              title
    short_title        shortTitle
    series             seriesTitle          the franchise, not the publisher's
    version            versionNumber        Zotero labels this field "Version"
    date               date                 YYYY, YYYY-MM or YYYY-MM-DD
    system             system               the platform this record is about
    publisher          company              company is Zotero's publisher field
    place              place                where the publisher published
    abstract           abstractNote
    url                url                  the source page the record came from
    accessed           accessDate           when that page was read
    catalog            libraryCatalog       which database supplied the record
    archive            archive              where a playable copy is preserved
    archive_location   archiveLocation      its identifier inside that archive
    call_number        callNumber
    rights             rights
    developer          creator, programmer  a studio, stored single-field
    contributors[]     creator, contributor
    extra{}            extra                one "Key: value" line each
    tags[]             item tags, manual

`programmingLanguage` is deliberately unmapped: on a Software item it means the
language a program was written in, not the language it is played in. A natural
language belongs in `extra` as `Language: en`, which is the line Zotero reads as
the citation language.

Usage:
    python3 build_game_records.py <payload.json> [more.json ...]
    python3 build_game_records.py --all
    python3 build_game_records.py --dry-run <payload.json>
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))

import data_paths as dp  # noqa: E402  (the shared declared-path resolver)
import zotero_common as zc  # noqa: E402

ITEM_TYPE = "computerProgram"
DEFAULT_COLLECTION = "Point and Click Games"

TEXT_FIELDS = {
    "title": "title",
    "short_title": "shortTitle",
    "series": "seriesTitle",
    "version": "versionNumber",
    "system": "system",
    "publisher": "company",
    "place": "place",
    "abstract": "abstractNote",
    "url": "url",
    "catalog": "libraryCatalog",
    "archive": "archive",
    "archive_location": "archiveLocation",
    "call_number": "callNumber",
    "rights": "rights",
}


def payload_dir() -> Path:
    """The git-ignored directory holding game payloads, beside the book ones."""
    root = zc._project_root()
    matches = sorted(root.glob("data/*/personal/game_records"))
    if matches:
        return matches[0]
    matches = sorted(root.glob("data/*/personal"))
    if matches:
        return matches[0] / "game_records"
    return root / "data" / dp.instance_slug() / "personal" / "game_records"


def default_collection() -> str:
    """The collection name, from config, falling back to the shipped default."""
    collections = zc._config().get("zotero", {}).get("collections", {})
    return collections.get("point_and_click") or DEFAULT_COLLECTION


# ---------------------------------------------------------------- normalising


def norm_title(text: str) -> str:
    """A comparison key for a title: case, accents and punctuation out."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_creator(name: str):
    """('First', 'Last', fieldMode) from 'Last, First' or a single-field name.

    A studio has no surname, so "Legend Entertainment" is stored whole in
    lastName with fieldMode 1 — how Zotero itself holds an institution.
    """
    name = (name or "").strip()
    if not name:
        return None
    if "," in name:
        last, first = name.split(",", 1)
        return first.strip(), last.strip(), 0
    return "", name, 1


def sql_date(value: str) -> str:
    """Zotero's stored date: '<sqldate> <what the user typed>'.

    An absent month or day is '00', which is how Zotero records a year-only
    date and how its own reader gets the year back out.
    """
    raw = str(value).strip()
    m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$", raw)
    if not m:
        return raw
    year, month, day = m.group(1), m.group(2) or "00", m.group(3) or "00"
    return f"{year}-{month}-{day} {raw}"


def sql_accessed(value: str) -> str:
    """Zotero's stored accessDate: a UTC 'YYYY-MM-DD HH:MM:SS'."""
    raw = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return f"{raw} 00:00:00"
    return raw


def extra_block(extra) -> str:
    """The extra field: one 'Key: value' line per entry, order preserved."""
    if not extra:
        return ""
    if isinstance(extra, str):
        return extra
    return "\n".join(f"{k}: {v}" for k, v in extra.items() if str(v).strip())


# ------------------------------------------------------------------- indexing


def load_software_index(conn):
    """Normalised title -> itemID, over Software items that are not deleted."""
    title_fid = zc.field_id(conn, "title")
    type_id = zc.item_type_id(conn, ITEM_TYPE)
    index = {}
    for r in conn.execute(
        """
        SELECT i.itemID, dv.value AS title
        FROM items i
        JOIN itemData d        ON d.itemID = i.itemID AND d.fieldID = ?
        JOIN itemDataValues dv ON dv.valueID = d.valueID
        LEFT JOIN deletedItems del ON del.itemID = i.itemID
        WHERE i.itemTypeID = ? AND del.itemID IS NULL
        """,
        (title_fid, type_id),
    ):
        index.setdefault(norm_title(r["title"]), r["itemID"])
    return index


# -------------------------------------------------------------------- writing


def get_or_create_collection(conn, name, keys):
    row = conn.execute(
        "SELECT collectionID FROM collections WHERE collectionName=? AND libraryID=?",
        (name, zc.USER_LIBRARY_ID),
    ).fetchone()
    if row:
        return row["collectionID"], False
    cur = conn.execute(
        """
        INSERT INTO collections
            (collectionName, parentCollectionID, clientDateModified, libraryID,
             key, version, synced)
        VALUES (?, NULL, ?, ?, ?, 0, 0)
        """,
        (name, zc.now_utc(), zc.USER_LIBRARY_ID, zc.new_key(conn, keys)),
    )
    return cur.lastrowid, True


def tag_id(conn, name: str) -> int:
    row = conn.execute("SELECT tagID FROM tags WHERE name=?", (name,)).fetchone()
    if row:
        return row[0]
    return conn.execute("INSERT INTO tags (name) VALUES (?)", (name,)).lastrowid


def set_field(conn, item_id, field, value):
    if value is None or not str(value).strip():
        return
    conn.execute(
        "INSERT INTO itemData (itemID, fieldID, valueID) VALUES (?,?,?)",
        (item_id, zc.field_id(conn, field), zc.value_id(conn, str(value).strip())),
    )


def create_game(conn, entry, keys):
    now = zc.now_utc()
    cur = conn.execute(
        """
        INSERT INTO items
            (itemTypeID, dateAdded, dateModified, clientDateModified, libraryID,
             key, version, synced)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (
            zc.item_type_id(conn, ITEM_TYPE),
            now, now, now, zc.USER_LIBRARY_ID, zc.new_key(conn, keys),
        ),
    )
    item_id = cur.lastrowid

    for key, field in TEXT_FIELDS.items():
        set_field(conn, item_id, field, entry.get(key))
    if entry.get("date"):
        set_field(conn, item_id, "date", sql_date(entry["date"]))
    if entry.get("accessed"):
        set_field(conn, item_id, "accessDate", sql_accessed(entry["accessed"]))
    set_field(conn, item_id, "extra", extra_block(entry.get("extra")))

    order = 0
    for name, creator_type in (
        [(entry.get("developer"), "programmer")]
        + [(c, "contributor") for c in entry.get("contributors", [])]
    ):
        parts = split_creator(name)
        if not parts:
            continue
        first, last, mode = parts
        conn.execute(
            """
            INSERT INTO itemCreators (itemID, creatorID, creatorTypeID, orderIndex)
            VALUES (?,?,?,?)
            """,
            (
                item_id,
                zc.creator_id(conn, first, last, mode),
                zc.creator_type_id(conn, creator_type),
                order,
            ),
        )
        order += 1

    for tag in entry.get("tags", []):
        if not str(tag).strip():
            continue
        conn.execute(
            "INSERT OR IGNORE INTO itemTags (itemID, tagID, type) VALUES (?,?,0)",
            (item_id, tag_id(conn, str(tag).strip())),
        )
    return item_id


def add_to_collection(conn, collection_id, item_id, order_index):
    row = conn.execute(
        "SELECT 1 FROM collectionItems WHERE collectionID=? AND itemID=?",
        (collection_id, item_id),
    ).fetchone()
    if row:
        return False
    conn.execute(
        "INSERT INTO collectionItems (collectionID, itemID, orderIndex) VALUES (?,?,?)",
        (collection_id, item_id, order_index),
    )
    return True


# ---------------------------------------------------------------- the payload


REQUIRED = ("title", "developer", "date", "system", "url", "catalog")


def check(payload, path):
    """Refuse a payload that would write a record nobody could check."""
    problems = []
    games = payload.get("games")
    if not isinstance(games, list) or not games:
        problems.append(f"{path.name}: no 'games' list")
        return problems
    for n, entry in enumerate(games, 1):
        for key in REQUIRED:
            if not str(entry.get(key, "")).strip():
                problems.append(
                    f"{path.name}: entry {n} ({entry.get('title', 'untitled')}) "
                    f"has no {key}"
                )
    return problems


def build_one(conn, payload, keys, index, dry_run):
    name = payload.get("collection") or default_collection()
    games = payload["games"]

    if dry_run:
        collection_id, created, start = None, True, 0
    else:
        collection_id, created = get_or_create_collection(conn, name, keys)
        start = conn.execute(
            "SELECT COALESCE(MAX(orderIndex), -1) FROM collectionItems WHERE collectionID=?",
            (collection_id,),
        ).fetchone()[0] + 1

    reused = made = 0
    for offset, entry in enumerate(games):
        item_id = index.get(norm_title(entry["title"]))
        if item_id is not None:
            reused += 1
        else:
            made += 1
            if dry_run:
                continue
            item_id = create_game(conn, entry, keys)
            index.setdefault(norm_title(entry["title"]), item_id)
        if not dry_run:
            add_to_collection(conn, collection_id, item_id, start + offset)

    return {"collection": name, "created": created, "reused": reused, "made": made}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("payloads", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true", help="every payload in the data dir")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="read-only: report what would be created and reused, safe with Zotero open",
    )
    args = ap.parse_args()

    paths = list(args.payloads)
    if args.all:
        paths += sorted(payload_dir().glob("*.json"))
    if not paths:
        sys.exit(f"No payloads given. Payloads live in {payload_dir()}")

    loaded = []
    problems = []
    for path in paths:
        if not path.exists():
            problems.append(f"{path}: not found")
            continue
        with path.open() as fh:
            payload = json.load(fh)
        problems += check(payload, path)
        loaded.append((path, payload))
    if problems:
        sys.exit("Payload refused:\n  " + "\n  ".join(problems))

    conn = zc.connect(read_only=args.dry_run)
    try:
        keys = set() if args.dry_run else zc.existing_keys(conn)
        index = load_software_index(conn)
        for path, payload in loaded:
            result = build_one(conn, payload, keys, index, args.dry_run)
            verb = "would create" if args.dry_run else "created"
            print(
                f"{path.name}: {result['collection']} — {verb} {result['made']}, "
                f"reused {result['reused']}"
            )
        if not args.dry_run:
            conn.commit()
    finally:
        conn.close()

    if not args.dry_run:
        print("Written. Reopen Zotero to see the items.")


if __name__ == "__main__":
    main()
