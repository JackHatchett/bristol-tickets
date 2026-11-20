"""smoke_targets/check_bluesky_archive.py — the `bluesky_archive` smoke target, run by smoke.py."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from qt_headless import PROJECT_ROOT
from smoke_targets.failure import SmokeFailure


def check_bluesky_archive() -> list[str]:
    """The local store keeps what the account stops serving.

    Deletion is the case the whole store exists for, and it cannot be checked
    against a live account without deleting something from one, so the account
    is stood in for by two reads: a full one, then a shorter one.
    """
    from datetime import date, datetime, timezone
    from zoneinfo import ZoneInfo

    root_dir = PROJECT_ROOT
    sys.path.insert(0, str(root_dir / "src" / "tools"))
    try:
        from bluesky import store as bs
        from bluesky import threads as bt
    finally:
        sys.path.pop(0)

    failures: list[str] = []
    zone = ZoneInfo("America/New_York")

    def record(name, moment):
        return {
            "uri": f"at://me/app.bsky.feed.post/{name}",
            "cid": name,
            "value": {"text": name, "createdAt": moment},
        }

    def node(uri, author, mine=False, children=()):
        item = bt.Node(
            uri,
            author,
            author,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            {"record": {"text": author}},
        )
        item.mine = mine
        item.children = list(children)
        return item

    with tempfile.TemporaryDirectory() as tmp:
        conn = bs.connect(Path(tmp) / "archive.db")

        # Three days of posts, one of them two posts, read in full.
        full = [
            record("a", "2026-03-01T12:00:00Z"),
            record("b", "2026-03-02T14:00:00Z"),
            record("c", "2026-03-02T23:30:00Z"),
            record("d", "2026-03-03T12:00:00Z"),
        ]
        bs.keep_posts(conn, full)
        if bs.post_count(conn) != 4:
            failures.append(f"a first read kept {bs.post_count(conn)} of 4 posts")

        # The account is read again with one post gone and one unchanged post
        # re-read. Nothing may be lost, and nothing may be counted twice.
        bs.keep_posts(conn, [full[0], full[1], full[3]])
        if bs.post_count(conn) != 4:
            failures.append(
                f"a post deleted from the account left {bs.post_count(conn)} of 4 in the store"
            )

        # A window opening partway through a day still renders that day whole.
        since = datetime(2026, 3, 2, 23, 0, tzinfo=timezone.utc)
        by_day = bs.records_by_day(conn, zone, since=since)
        opened = by_day.get(date(2026, 3, 2))
        if opened is None or len(opened) != 2:
            failures.append("a day the window opened partway through came back in part")
        if date(2026, 3, 1) in by_day:
            failures.append("a day before the window came back")

        # A conversation is kept, and is not replaced by one containing less of
        # what the account said in it.
        root = "at://them/app.bsky.feed.post/root"
        whole = node(
            root,
            "op",
            children=[node("at://me/1", "me", mine=True), node("at://me/2", "me", mine=True)],
        )
        kept = bs.keep_thread(conn, root, whole)
        if kept is None or len(bt.mine_uris(kept)) != 2:
            failures.append("a conversation was not kept as it was fetched")
        if kept is whole:
            failures.append("the page was written from the fetch rather than from the store")

        short = node(root, "op", children=[node("at://me/1", "me", mine=True)])
        kept = bs.keep_thread(conn, root, short)
        if kept is None or len(bt.mine_uris(kept)) != 2:
            failures.append("a conversation that came back short replaced the kept one")

        gone = bs.keep_thread(conn, root, None)
        if gone is None or len(bt.mine_uris(gone)) != 2:
            failures.append("a conversation that could not be fetched at all was lost")

        richer = node(
            root,
            "op",
            children=[
                node("at://me/1", "me", mine=True),
                node("at://me/2", "me", mine=True),
                node("at://me/3", "me", mine=True),
            ],
        )
        kept = bs.keep_thread(conn, root, richer)
        if kept is None or len(bt.mine_uris(kept)) != 3:
            failures.append("a conversation holding more was not taken")
        authors = sorted(n.author for n in kept.walk()) if kept is not None else []
        if authors != ["me", "me", "me", "op"]:
            failures.append(f"a conversation read back out of the store said {authors}")
        conn.close()

    if failures:
        raise SmokeFailure("; ".join(failures))
    return [
        "the store keeps a deleted post, renders a boundary day whole, and "
        "never trades a conversation for a shorter one"
    ]
