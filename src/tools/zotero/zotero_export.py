#!/usr/bin/env python3
"""
zotero_export.py — read book data out of Zotero, safely, while Zotero is open.

Zotero is the source of truth for books. Everything downstream — the
library.xlsx snapshot, the archival citation file — reads through here.

WHY A COPY.
// Zotero holds zotero.sqlite open and keeps state in memory. Reading the live
// file behind a running Zotero can return a torn page mid-transaction, and any
// *write* is silently lost or corrupts the database.
The writers in this folder refuse to run while Zotero is open
(`require_zotero_closed`).
A reader has no such excuse to be unavailable: this module copies the database
to a scratch file, opens the copy read-only, and never touches the original.
That is what makes `library.xlsx` regenerable at any time.

The copy lands in the system temp dir and is deleted on the way out, including
on error. It is never written anywhere that persists.

FIELD MAP — Zotero back to the columns the library snapshot has always had:
    author      creators on the item, "Last, First", in Zotero's order
    title       title
    publisher   publisher
    edition     extra "Copy: …"  (which physical copy), else the edition field
    signed      tag "Signed copy"           -> Y / N
    genre       extra "Genre: …" if present, else the item's genre tags joined
    pub_date    date (year)
    page_count  numPages, or `pages` for magazineArticle (which has no numPages)
    price_paid  extra "Price paid: …"
    read        membership of the "Books I've Read" collection -> Y / N
    shelved     tag "Shelved" (ownership) -> Y / N

`extra` is Zotero's escape hatch for fields its schema has no home for, one
"Key: value" per line. The book import put the library's non-bibliographic
columns there rather than inventing item types.

Usage:
    python3 zotero_export.py                 # TSV to stdout
    python3 zotero_export.py --json          # JSON records
    python3 zotero_export.py --stats         # the library metrics, computed
    import zotero_export; rows = zotero_export.read_books()
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zotero_common as zc  # noqa: E402

READ_COLLECTION = "Books I've Read"
SHELVED_TAG = "Shelved"
UNSHELVED_TAG = "Not shelved"
SIGNED_TAG = "Signed copy"

# The library is not "every book item in Zotero". Zotero also holds the
# aspirational reading-list collections — ~1,700 titles the user has not read
# and does not own — and counting those as "unread library" would redefine
# every metric the snapshot has ever reported. An item belongs to the LIBRARY
# iff it is in the read collection or carries an ownership tag; a list-only
# title has neither.
#
# Item types: the library is not all `book` either. 89 magazines were imported
# as `magazineArticle`, 82 of them shelved. Filtering on typeName='book' alone
# silently dropped them and under-reported the shelved count by 82.
LIBRARY_TYPES = ("book", "magazineArticle")

# Tags that say something other than genre, so the genre fallback does not
# report "Shelved" as a literary category.
NON_GENRE_TAGS = {SHELVED_TAG, "Not shelved", SIGNED_TAG, "unverified-metadata"}

COLUMNS = ["author", "title", "publisher", "edition", "signed", "genre",
           "pub_date", "page_count", "price_paid", "read", "shelved"]


@contextmanager
def open_snapshot():
    """Yield a read-only connection to a throwaway COPY of zotero.sqlite.

    Safe to call with Zotero running — which is the point. The copy is removed
    on the way out whether or not the body raised."""
    src = zc.db_path()
    if not src.exists():
        sys.exit(f"No Zotero database at {src}. Set ZOTERO_DATA_DIR.")
    tmp_dir = tempfile.mkdtemp(prefix="zotero_export_")
    tmp = Path(tmp_dir) / "zotero.sqlite"
    try:
        shutil.copy2(src, tmp)
        conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _parse_extra(extra: str | None) -> dict:
    """Zotero's `extra` field as a dict. One 'Key: value' per line; lines
    without a colon are ignored rather than guessed at."""
    out = {}
    for line in (extra or "").splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip().lower()] = v.strip()
    return out


def read_books(conn=None) -> list[dict]:
    """Every book Zotero holds, as snapshot rows. Pass a connection to reuse
    one; otherwise a private copy is made and cleaned up."""
    if conn is None:
        with open_snapshot() as c:
            return read_books(c)

    ph = ",".join("?" * len(LIBRARY_TYPES))
    items = {
        r["itemID"]: {"author": [], "tags": set(), "fields": {}, "read": "N"}
        for r in conn.execute(
            f"SELECT i.itemID FROM items i JOIN itemTypes t USING (itemTypeID) "
            f"WHERE t.typeName IN ({ph}) "
            f"AND i.itemID NOT IN (SELECT itemID FROM deletedItems)",
            LIBRARY_TYPES)
    }

    for r in conn.execute(
            "SELECT d.itemID, f.fieldName, v.value FROM itemData d "
            "JOIN fields f USING (fieldID) JOIN itemDataValues v USING (valueID)"):
        if r["itemID"] in items:
            items[r["itemID"]]["fields"][r["fieldName"]] = r["value"]

    # Zotero stores a name either split (lastName/firstName) or as a single
    # field — "Ovid", "Anonymous". fieldMode=1 marks the single-field form,
    # which must not be rendered as "Ovid, ".
    for r in conn.execute(
            "SELECT ic.itemID, c.lastName, c.firstName, c.fieldMode "
            "FROM itemCreators ic JOIN creators c USING (creatorID) "
            "ORDER BY ic.itemID, ic.orderIndex"):
        if r["itemID"] not in items:
            continue
        name = (r["lastName"] or "") if r["fieldMode"] == 1 else \
            ", ".join(p for p in (r["lastName"], r["firstName"]) if p)
        if name:
            items[r["itemID"]]["author"].append(name)

    for r in conn.execute(
            "SELECT it.itemID, t.name FROM itemTags it JOIN tags t USING (tagID)"):
        if r["itemID"] in items:
            items[r["itemID"]]["tags"].add(r["name"])

    for r in conn.execute(
            "SELECT ci.itemID FROM collectionItems ci JOIN collections co "
            "USING (collectionID) WHERE co.collectionName=?", (READ_COLLECTION,)):
        if r["itemID"] in items:
            items[r["itemID"]]["read"] = "Y"

    rows = []
    for it in items.values():
        # Aspirational list titles are not the library — see LIBRARY_TYPES.
        if it["read"] != "Y" and not (it["tags"] & {SHELVED_TAG, UNSHELVED_TAG}):
            continue
        f = it["fields"]
        extra = _parse_extra(f.get("extra"))
        genre = extra.get("genre") or ", ".join(
            sorted(it["tags"] - NON_GENRE_TAGS)) or None
        # A magazineArticle has no numPages — Zotero gives that type `pages`
        # instead. Reading only numPages dropped 92 magazines' page counts.
        pages = f.get("numPages") or f.get("pages")
        rows.append({
            "author": "; ".join(it["author"]) or None,
            "title": f.get("title"),
            "publisher": f.get("publisher"),
            "edition": extra.get("copy") or f.get("edition"),
            "signed": "Y" if SIGNED_TAG in it["tags"] else "N",
            "genre": genre,
            "pub_date": (f.get("date") or "")[:4] or None,
            "page_count": int(pages) if (pages or "").isdigit() else None,
            "price_paid": extra.get("price paid"),
            "read": it["read"],
            "shelved": "Y" if SHELVED_TAG in it["tags"] else "N",
        })

    rows.sort(key=lambda r: ((r["author"] or "").lower(), (r["title"] or "").lower()))
    return rows


def library_stats(rows: list[dict]) -> dict:
    """The library metrics, over the READ set — the same scope personal.db's
    books table always had (every row in it was read='Y'). Aspirational reading
    lists live in their own Zotero collections and are deliberately NOT counted
    here: they are books to read, not a library of unread books, and folding
    them in would silently redefine every metric below."""
    def pages(rs):
        return sum(r["page_count"] or 0 for r in rs) or None

    def avg(rs):
        vals = [r["page_count"] for r in rs if r["page_count"]]
        return round(sum(vals) / len(vals)) if vals else None

    read = [r for r in rows if r["read"] == "Y"]
    unread = [r for r in rows if r["read"] == "N"]
    shelved = [r for r in rows if r["shelved"] == "Y"]
    rs = [r for r in read if r["shelved"] == "Y"]
    ru = [r for r in read if r["shelved"] == "N"]
    sn = [r for r in shelved if r["read"] == "N"]
    logged = len(read) + len(unread)
    return {
        "total_pages_read": pages(read),
        "total_titles_read": len(read),
        "total_titles_unread": len(unread),
        "pct_logged_read": round(len(read) / logged, 4) if logged else None,
        "avg_len_read": avg(read),
        "avg_len_read_shelved": avg(rs),
        "avg_len_unread": avg(unread),
        "shelved_pages_read": pages(rs),
        "shelved_titles_read": len(rs),
        "unshelved_pages_read": pages(ru),
        "unshelved_titles_read": len(ru),
        "total_shelved_pages": pages(shelved),
        "total_shelved_titles": len(shelved),
        "shelved_pages_not_read": pages(sn),
        "shelved_titles_not_read": len(sn),
    }


def main() -> None:
    rows = read_books()
    if "--stats" in sys.argv:
        for k, v in library_stats(rows).items():
            print(f"{k:28s} {v}")
    elif "--json" in sys.argv:
        json.dump(rows, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print("\t".join(COLUMNS))
        for r in rows:
            print("\t".join("" if r[c] is None else str(r[c]) for c in COLUMNS))
    print(f"[zotero_export] {len(rows)} book items", file=sys.stderr)


if __name__ == "__main__":
    main()
