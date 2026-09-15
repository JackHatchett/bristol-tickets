"""The account's own copy of what it posted, and of the conversations it sat in.

Bluesky serves what an account holds now. A page rebuilt from it after a post
has been deleted loses that post, and loses the conversation around it as well,
because a thread is fetched through the post that anchors it. This keeps both
halves on the machine — every post record the account has ever been seen to
hold, and each pruned conversation as it was last seen whole — and the
notebook's pages are written from here rather than from the network.

The store only ever gains. A post already kept is refreshed in place and never
removed. A conversation is replaced only by a newly fetched one holding every
one of the account's posts the kept copy held, so a thread that comes back
short leaves what is kept alone, whatever made it short.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading as _threading
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
TOOLS = HERE.parents[1]
sys.path.insert(0, str(TOOLS))

from bluesky import client, threads  # noqa: E402
from config_tools import data_paths  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS post (
    uri        TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    record     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS post_created_at ON post (created_at);
CREATE TABLE IF NOT EXISTS thread (
    root_uri TEXT PRIMARY KEY,
    covers   TEXT NOT NULL,
    tree     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS other_record (
    uri             TEXT PRIMARY KEY,
    collection      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    record          TEXT NOT NULL,
    delete_sent_at  TEXT
);
"""

# A column added to a table a database already holds, which a schema of
# CREATE TABLE IF NOT EXISTS cannot reach.
ADDED_COLUMNS = {"post": {"delete_sent_at": "TEXT"}}

# Days are worked several at a time, so every call here takes the same lock and
# the connection is shared rather than opened per thread.
_LOCK = _threading.Lock()


def archive_path():
    """The store's own file, inside the git-ignored data tree."""
    folder = data_paths.ensure_dir(f"data/{data_paths.instance_slug()}/bluesky")
    return folder / "archive.db"


def connect(path=None):
    """The store, created with its schema where it is not there yet.

    `path` names a file other than the account's own store, which is what lets
    the store be exercised without a real one to write into.
    """
    target = data_paths.ensure_db(Path(path) if path else archive_path(), SCHEMA)
    conn = sqlite3.connect(str(target), timeout=10, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.row_factory = sqlite3.Row
    for table, columns in ADDED_COLUMNS.items():
        held = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, kind in columns.items():
            if name not in held:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")
    conn.commit()
    return conn


def keep_posts(conn, records):
    """Every record just read from the account, added or refreshed.

    Returns how many of them the store had never seen. Nothing is removed: a
    post the account no longer serves is still a post the account made.
    """
    added = 0
    with _LOCK:
        for record in records:
            uri = record.get("uri")
            if not uri:
                continue
            if conn.execute("SELECT 1 FROM post WHERE uri = ?", (uri,)).fetchone() is None:
                added += 1
            conn.execute(
                "INSERT INTO post (uri, created_at, record) VALUES (?, ?, ?) "
                "ON CONFLICT(uri) DO UPDATE SET created_at = excluded.created_at, "
                "record = excluded.record",
                (uri, client.created_at(record).isoformat(),
                 json.dumps(record, sort_keys=True)))
        conn.commit()
    return added


def post_count(conn):
    """How many post records the store holds."""
    with _LOCK:
        return conn.execute("SELECT COUNT(*) FROM post").fetchone()[0]


def thread_count(conn):
    """How many conversations the store holds."""
    with _LOCK:
        return conn.execute("SELECT COUNT(*) FROM thread").fetchone()[0]


def records_by_day(conn, zone, since=None):
    """Every kept post record, grouped by the day it belongs to in `zone`.

    `since` names a moment rather than a day, and a day is taken whole: a day
    the window opens partway through is rendered from all of its posts rather
    than from the tail the window happens to reach.
    """
    floor = None
    if since is not None:
        opening = datetime.combine(since.astimezone(zone).date(), time.min, tzinfo=zone)
        floor = opening.astimezone(timezone.utc).isoformat()
    sql = "SELECT created_at, record FROM post"
    params = ()
    if floor is not None:
        sql += " WHERE created_at >= ?"
        params = (floor,)
    sql += " ORDER BY created_at"
    by_day = defaultdict(list)
    with _LOCK:
        rows = conn.execute(sql, params).fetchall()
    for row in rows:
        moment = datetime.fromisoformat(row["created_at"])
        by_day[moment.astimezone(zone).date()].append(json.loads(row["record"]))
    return by_day


def load_thread(conn, root_uri):
    """One kept conversation, or None where the store has never held it."""
    with _LOCK:
        row = conn.execute("SELECT tree FROM thread WHERE root_uri = ?",
                           (root_uri,)).fetchone()
    if row is None:
        return None
    return threads.from_dict(json.loads(row["tree"]))


def keep_thread(conn, root_uri, tree):
    """One conversation as just fetched, and the one the page is written from.

    A fetched conversation replaces what is kept only where it still holds
    every one of the account's posts the kept copy held. The answer is then
    read back out of the store, so what reaches the page is always what the
    store holds rather than what the network returned.
    """
    with _LOCK:
        row = conn.execute("SELECT covers FROM thread WHERE root_uri = ?",
                           (root_uri,)).fetchone()
        held = set(json.loads(row["covers"])) if row is not None else set()
        if tree is not None:
            covers = threads.mine_uris(tree)
            if covers >= held:
                conn.execute(
                    "INSERT INTO thread (root_uri, covers, tree) VALUES (?, ?, ?) "
                    "ON CONFLICT(root_uri) DO UPDATE SET covers = excluded.covers, "
                    "tree = excluded.tree",
                    (root_uri, json.dumps(sorted(covers)),
                     json.dumps(threads.to_dict(tree))))
                conn.commit()
    return load_thread(conn, root_uri)


def keep_other_records(conn, collection, records):
    """Records from a collection other than the account's posts.

    A repost carries none of the account's words, so it is no part of a page,
    but it is still the account's own record and nothing leaves the account
    without a copy here first.
    """
    added = 0
    with _LOCK:
        for record in records:
            uri = record.get("uri")
            if not uri:
                continue
            if conn.execute("SELECT 1 FROM other_record WHERE uri = ?",
                            (uri,)).fetchone() is None:
                added += 1
            conn.execute(
                "INSERT INTO other_record (uri, collection, created_at, record) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(uri) DO UPDATE SET "
                "collection = excluded.collection, created_at = excluded.created_at, "
                "record = excluded.record",
                (uri, collection, client.created_at(record).isoformat(),
                 json.dumps(record, sort_keys=True)))
        conn.commit()
    return added


def mark_delete_sent(conn, uris, moment=None):
    """The moment a delete was sent for each of these, written before it is.

    A pass cut off partway can then say what it had already asked to have
    removed, which is the difference between resuming and starting again.
    """
    stamp = (moment or datetime.now(timezone.utc)).isoformat()
    with _LOCK:
        for uri in uris:
            conn.execute("UPDATE post SET delete_sent_at = ? WHERE uri = ?", (stamp, uri))
            conn.execute("UPDATE other_record SET delete_sent_at = ? WHERE uri = ?",
                         (stamp, uri))
        conn.commit()


def delete_sent(conn):
    """Every address a delete has already been sent for."""
    with _LOCK:
        sent = {row[0] for row in
                conn.execute("SELECT uri FROM post WHERE delete_sent_at IS NOT NULL")}
        sent |= {row[0] for row in
                 conn.execute("SELECT uri FROM other_record "
                              "WHERE delete_sent_at IS NOT NULL")}
    return sent
