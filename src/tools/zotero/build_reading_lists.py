#!/usr/bin/env python3
"""
build_reading_lists.py — turn reading-list payloads into Zotero collections.

Each payload is one JSON file describing one published list. The script creates
a Zotero collection of that name and fills it, reusing an item the library
already holds whenever the entry matches one, and creating a book item only when
it does not. Nothing is ever added to "Books I've Read": an aspirational list is
its own collection, and membership of the read collection is a fact about the
user, not about the list.

Payload shape:
    {
      "collection": "Modern Library 100 Best Novels",
      "source": "https://...",              # authoritative source, recorded
      "stated_count": 100,                  # what the source says it holds
      "entries": [
        {"title": "Ulysses", "author": "Joyce, James"},
        {"title": "The Arabian Nights", "author": "", "note": "..."}
      ]
    }

Re-running is safe: a collection that already exists is reused and only missing
entries are added, so a payload can be corrected and replayed.

Usage:
    python3 build_reading_lists.py <payload.json> [more.json ...]
    python3 build_reading_lists.py --all            # every payload in the data dir
    python3 build_reading_lists.py --dry-run <payload.json>
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))

import data_paths as dp  # noqa: E402  (the shared declared-path resolver)
import zotero_common as zc  # noqa: E402

READ_COLLECTION = "Books I've Read"

# Payload directory lives in the git-ignored data tree, resolved the same way
# the personal_db tools resolve theirs. A directory that does not exist yet is
# not an error: --all simply finds no payloads.
def payload_dir() -> Path:
    root = zc._project_root()
    matches = sorted(root.glob("data/*/personal/reading_lists"))
    if matches:
        return matches[0]
    matches = sorted(root.glob("data/*/personal"))
    if matches:
        return matches[0] / "reading_lists"
    return root / "data" / dp.instance_slug() / "personal" / "reading_lists"


# ---------------------------------------------------------------- normalising

_ARTICLES = ("the ", "a ", "an ")


def norm_title(text: str) -> str:
    """A comparison key for a title: case, accents, punctuation and articles out."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for art in _ARTICLES:
        if text.startswith(art):
            text = text[len(art):]
            break
    return text


def title_stem(text: str) -> str:
    """Normalised title with any subtitle or edition tag removed.

    Catches the shapes a real library uses that a published list does not:
    "Slaughterhouse-Five or The Children's Crusade", "All the King's Men
    [2006 Movie Tie-In Edition]", "Emma: An Annotated Edition".
    """
    head = re.split(r"[:;(\[]|\s+or\s+the\s+", text or "", maxsplit=1)[0]
    return norm_title(head)


def split_author(author: str):
    """('First', 'Last', fieldMode) from 'Last, First' or a single-field name."""
    author = (author or "").strip()
    if not author:
        return None
    if "," in author:
        last, first = author.split(",", 1)
        return first.strip(), last.strip(), 0
    # No comma: a mononym or an institution. Zotero's fieldMode 1 stores it whole
    # in lastName, which is how Zotero itself represents "Anonymous" or "Ovid".
    return "", author, 1


def norm_surname(author: str) -> str:
    parts = split_author(author)
    if not parts:
        return ""
    return norm_title(parts[1])


# ------------------------------------------------------------------- indexing


def load_library_index(conn):
    """Map normalised title keys to itemIDs for every top-level regular item."""
    title_fid = zc.field_id(conn, "title")
    rows = conn.execute(
        """
        SELECT i.itemID, dv.value AS title
        FROM items i
        JOIN itemData d      ON d.itemID = i.itemID AND d.fieldID = ?
        JOIN itemDataValues dv ON dv.valueID = d.valueID
        LEFT JOIN deletedItems del ON del.itemID = i.itemID
        WHERE del.itemID IS NULL
        """,
        (title_fid,),
    ).fetchall()

    creators = {}
    for r in conn.execute(
        """
        SELECT ic.itemID, c.lastName
        FROM itemCreators ic
        JOIN creators c ON c.creatorID = ic.creatorID
        """
    ):
        creators.setdefault(r["itemID"], set()).add(norm_title(r["lastName"]))

    exact, stem = {}, {}
    by_author = {}
    for r in rows:
        surnames = creators.get(r["itemID"], set())
        for surname in surnames or {""}:
            exact.setdefault((norm_title(r["title"]), surname), r["itemID"])
            stem.setdefault((title_stem(r["title"]), surname), r["itemID"])
            if surname:
                by_author.setdefault(surname, []).append(
                    (norm_title(r["title"]), r["itemID"])
                )
    return exact, stem, by_author


def find_match(entry, exact, stem, by_author):
    """An existing itemID for this entry, or None. Title AND author must agree."""
    surname = norm_surname(entry.get("author", ""))
    if not surname:
        # A title with no author is too weak a key to merge on; a new item is
        # the honest outcome and the duplicate pane can catch it later.
        return None
    title = entry.get("title", "")
    key = (norm_title(title), surname)
    if key in exact:
        return exact[key]
    key = (title_stem(title), surname)
    if key in stem:
        return stem[key]
    # Same author, and the library's title begins with the list's title on a
    # word boundary — the library copy carries a subtitle or edition tag the
    # list omits. Short titles are excluded: "Loving" would swallow too much.
    want = norm_title(title)
    if len(want) >= 12:
        for have, item_id in by_author.get(surname, ()):
            if have.startswith(want + " "):
                return item_id
    return None


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


def create_book(conn, entry, keys, ids):
    now = zc.now_utc()
    cur = conn.execute(
        """
        INSERT INTO items
            (itemTypeID, dateAdded, dateModified, clientDateModified, libraryID,
             key, version, synced)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (ids["book"], now, now, now, zc.USER_LIBRARY_ID, zc.new_key(conn, keys)),
    )
    item_id = cur.lastrowid

    conn.execute(
        "INSERT INTO itemData (itemID, fieldID, valueID) VALUES (?,?,?)",
        (item_id, ids["title"], zc.value_id(conn, entry["title"])),
    )
    if entry.get("date"):
        conn.execute(
            "INSERT INTO itemData (itemID, fieldID, valueID) VALUES (?,?,?)",
            (item_id, ids["date"], zc.value_id(conn, str(entry["date"]))),
        )
    if entry.get("note"):
        conn.execute(
            "INSERT INTO itemData (itemID, fieldID, valueID) VALUES (?,?,?)",
            (item_id, ids["extra"], zc.value_id(conn, entry["note"])),
        )

    parts = split_author(entry.get("author", ""))
    if parts:
        first, last, mode = parts
        conn.execute(
            """
            INSERT INTO itemCreators (itemID, creatorID, creatorTypeID, orderIndex)
            VALUES (?,?,?,0)
            """,
            (item_id, zc.creator_id(conn, first, last, mode), ids["author"]),
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


def build_one(conn, payload, ids, keys, exact, stem, by_author, dry_run):
    name = payload["collection"]
    entries = payload["entries"]
    stated = payload.get("stated_count")

    collection_id, created = (None, True)
    if not dry_run:
        collection_id, created = get_or_create_collection(conn, name, keys)
        start = conn.execute(
            "SELECT COALESCE(MAX(orderIndex), -1) FROM collectionItems WHERE collectionID=?",
            (collection_id,),
        ).fetchone()[0] + 1
    else:
        start = 0

    reused = made = 0
    for offset, entry in enumerate(entries):
        item_id = find_match(entry, exact, stem, by_author)
        if item_id is not None:
            reused += 1
        else:
            made += 1
            if dry_run:
                continue
            item_id = create_book(conn, entry, keys, ids)
            surname = norm_surname(entry.get("author", ""))
            exact.setdefault((norm_title(entry["title"]), surname), item_id)
            stem.setdefault((title_stem(entry["title"]), surname), item_id)
            if surname:
                by_author.setdefault(surname, []).append(
                    (norm_title(entry["title"]), item_id)
                )
        if not dry_run:
            add_to_collection(conn, collection_id, item_id, start + offset)

    return {
        "collection": name,
        "new_collection": created,
        "entries": len(entries),
        "reused": reused,
        "created": made,
        "stated_count": stated,
        "shortfall": None if stated is None else stated - len(entries),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("payloads", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true", help="every payload in the data dir")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    args = ap.parse_args()

    paths = list(args.payloads)
    if args.all:
        paths += sorted(payload_dir().glob("*.json"))
    if not paths:
        ap.error("give one or more payload files, or --all")

    conn = zc.connect(read_only=args.dry_run)
    ids = {
        "book": zc.item_type_id(conn, "book"),
        "author": zc.creator_type_id(conn, "author"),
        "title": zc.field_id(conn, "title"),
        "date": zc.field_id(conn, "date"),
        "extra": zc.field_id(conn, "extra"),
    }
    keys = zc.existing_keys(conn)
    exact, stem, by_author = load_library_index(conn)

    reports = []
    try:
        for path in paths:
            payload = json.loads(Path(path).read_text())
            if payload["collection"] == READ_COLLECTION:
                raise SystemExit(
                    f"{path}: refusing to write into {READ_COLLECTION!r}."
                )
            reports.append(build_one(conn, payload, ids, keys, exact, stem, by_author, args.dry_run))
        if not args.dry_run:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    width = max(len(r["collection"]) for r in reports)
    for r in reports:
        short = "" if not r["shortfall"] else f"  SHORT {r['shortfall']}"
        print(
            f"{r['collection']:<{width}}  {r['entries']:>5} entries  "
            f"{r['reused']:>5} reused  {r['created']:>5} new{short}"
        )
    if args.dry_run:
        print("\n(dry run — nothing written)")


if __name__ == "__main__":
    main()
