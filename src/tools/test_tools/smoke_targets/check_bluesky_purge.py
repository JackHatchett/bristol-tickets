"""smoke_targets/check_bluesky_purge.py — the `bluesky_purge` smoke target, run by smoke.py."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

from qt_headless import PROJECT_ROOT
from smoke_targets.failure import SmokeFailure


def check_bluesky_purge() -> list[str]:
    """Emptying the account paces itself, and writes down what it sent.

    Nothing here reaches the account. What is checked is the arithmetic that
    decides how fast a pass may go and the record that lets a cut-off pass
    resume, both of which are wrong only once and expensively.
    """
    root_dir = PROJECT_ROOT
    sys.path.insert(0, str(root_dir / "src" / "tools"))
    try:
        from bluesky import purge as bp
        from bluesky import store as bs
    finally:
        sys.path.pop(0)

    failures: list[str] = []

    if bp.rkey("at://did:plc:abc/app.bsky.feed.post/3kzz") != "3kzz":
        failures.append("a record's own key was not read off its address")

    # The whole hour's allowance is spent without waiting; the point after it
    # has to wait, and the wait is most of an hour.
    allowance = bp.WriteBudget()
    started = time.monotonic()
    allowance.take(bp.WriteBudget.HOURLY_POINTS - bp.WriteBudget.MARGIN)
    if time.monotonic() - started > 1:
        failures.append("spending the hour's allowance waited")
    waits: list[float] = []
    original = time.sleep

    def instead(seconds):
        """The wait, taken rather than served: the hour is emptied by hand so
        the pass goes on, and the length it asked for is what is checked."""
        waits.append(seconds)
        allowance.spent.clear()

    time.sleep = instead
    try:
        allowance.take(1)
    finally:
        time.sleep = original
    if not waits or waits[0] < 3500:
        failures.append(f"a point past the hour's allowance waited {waits}")

    with tempfile.TemporaryDirectory() as tmp:
        conn = bs.connect(Path(tmp) / "archive.db")
        posts = [
            {
                "uri": "at://me/app.bsky.feed.post/1",
                "value": {"text": "one", "createdAt": "2026-03-01T12:00:00Z"},
            },
            {
                "uri": "at://me/app.bsky.feed.post/2",
                "value": {"text": "two", "createdAt": "2026-03-01T13:00:00Z"},
            },
        ]
        reposts = [
            {
                "uri": "at://me/app.bsky.feed.repost/1",
                "value": {"createdAt": "2026-03-01T14:00:00Z"},
            }
        ]
        bs.keep_posts(conn, posts)
        bs.keep_other_records(conn, "app.bsky.feed.repost", reposts)
        if bs.delete_sent(conn):
            failures.append("a pass that has sent nothing said it had")
        bs.mark_delete_sent(conn, [posts[0]["uri"], reposts[0]["uri"]])
        sent = bs.delete_sent(conn)
        if sent != {posts[0]["uri"], reposts[0]["uri"]}:
            failures.append(f"what a cut-off pass had sent read back as {sorted(sent)}")
        if bs.post_count(conn) != 2:
            failures.append("a post the account no longer has left the store")
        conn.close()

    if failures:
        raise SmokeFailure("; ".join(failures))
    return [
        "emptying the account keeps to the hour's write budget and says what it had already sent"
    ]
