#!/usr/bin/env python3
"""Empty the account: remove every post and repost, and leave everything else.

    python3 src/tools/bluesky/purge.py           # say what would go, remove nothing
    python3 src/tools/bluesky/purge.py --delete  # remove it

A follow is a record in the follower's own repository pointing at this account,
so nothing here can reach one: the handle, the profile and the followers are
the same afterwards as before. What goes is what the account itself holds.

Nothing leaves the account that the store does not already hold. The pass reads
the account, keeps what it read, writes down the moment each delete is sent,
and only then sends it, so a pass cut off partway says what is already gone and
starts again from there.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve()
TOOLS = HERE.parents[1]
sys.path.insert(0, str(TOOLS))

from bluesky import client, store, sync  # noqa: E402

PURGED = ("app.bsky.feed.post", "app.bsky.feed.repost")
BATCH = 100
ROUNDS = 3


class WriteBudget:
    """The account's write allowance, spent a point at a time.

    A delete costs one point, and an account may spend 5,000 points in an hour
    and 35,000 in a day. Holding to the hourly figure holds to both, because an
    hour's spending repeated all day comes to less than the day's.
    """

    HOURLY_POINTS = 5000
    MARGIN = 50
    HOUR = 3600.0

    def __init__(self):
        self.spent = deque()

    def take(self, points):
        while True:
            now = time.monotonic()
            while self.spent and now - self.spent[0] > self.HOUR:
                self.spent.popleft()
            if len(self.spent) + points <= self.HOURLY_POINTS - self.MARGIN:
                break
            wait = self.HOUR - (now - self.spent[0]) + 1
            print(f"  waiting {int(wait)}s to stay inside the hour's write budget")
            time.sleep(wait)
        stamp = time.monotonic()
        self.spent.extend([stamp] * points)


def _post(url, body, token=None):
    """One authenticated call, returning parsed JSON."""
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json",
               "User-Agent": client.USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:300]
        raise client.BlueskyError(f"{error.code} from {url}: {detail}") from error


def sign_in(pds, identifier, password):
    """A session on the account's own data server, from an app password."""
    payload = _post(f"{pds}/xrpc/com.atproto.server.createSession",
                    {"identifier": identifier, "password": password})
    token = payload.get("accessJwt")
    if not token:
        raise client.BlueskyError("the data server returned no session")
    return token


def rkey(uri):
    """The record's own key, which is the last part of its address."""
    return uri.rsplit("/", 1)[-1]


def send_deletes(pds, token, did, collection, uris):
    """One batch of deletes, as one call."""
    writes = [{"$type": "com.atproto.repo.applyWrites#delete",
               "collection": collection, "rkey": rkey(uri)} for uri in uris]
    _post(f"{pds}/xrpc/com.atproto.repo.applyWrites",
          {"repo": did, "writes": writes}, token=token)


def gather(conn, did, pds):
    """What the account still holds, kept, and all of it still to remove.

    What the account returns is what is left, so a record read here is a record
    to remove whatever an earlier pass wrote down about it. A delete written
    down before it was sent, and refused by the server, would otherwise exempt
    the record from every later pass and leave it on the account for good.
    """
    plan = []
    for collection in PURGED:
        records = client.read_records(did, pds, collection)
        if collection == client.POST_COLLECTION:
            store.keep_posts(conn, records)
        else:
            store.keep_other_records(conn, collection, records)
        waiting = [r["uri"] for r in records]
        print(f"{collection}: {len(records)} on the account, "
              f"{len(waiting)} still to remove")
        plan.append((collection, waiting))
    return plan


def run(delete=False, budget=None):
    handle = sync.setting("handle")
    if not handle:
        sys.exit("bluesky.handle is not set in config; nothing to empty.")
    did, pds = sync.account()
    conn = store.connect()

    before = client.profile(did)
    print(f"{handle}: {before.get('followersCount')} followers, "
          f"{before.get('postsCount')} posts on the profile")
    print(f"the store holds {store.post_count(conn)} posts and "
          f"{store.thread_count(conn)} conversations")

    plan = gather(conn, did, pds)
    waiting = sum(len(uris) for _, uris in plan)
    if not delete:
        print(f"would remove {waiting} records, and remove nothing else")
        print("run it again with --delete to empty the account")
        return 0
    if not waiting:
        print("nothing left to remove")
        return verify(did, pds, before)

    password = sync.setting("app_password")
    if not password:
        sys.exit("bluesky.app_password is not set in config. Make an app "
                 "password in the account's settings, write it into config as "
                 "bluesky.app_password, and run this again. An app password is "
                 "revocable on its own and is never the account password.")
    token = sign_in(pds, handle, password)
    allowance = WriteBudget()
    started = time.monotonic()
    removed = 0
    stopped_at = None

    for collection, uris in plan:
        for index in range(0, len(uris), BATCH):
            if budget is not None and time.monotonic() - started > budget:
                stopped_at = f"{collection} with {len(uris) - index} left"
                break
            batch = uris[index:index + BATCH]
            allowance.take(len(batch))
            # Written down before it is sent, so an interrupted pass knows.
            store.mark_delete_sent(conn, batch)
            send_deletes(pds, token, did, collection, batch)
            removed += len(batch)
            if removed % 1000 < BATCH:
                print(f"  {removed} of {waiting} removed")
        if stopped_at:
            break

    print(f"{removed} records removed")
    if stopped_at:
        print(f"stopping at {stopped_at}; run it again to carry on")
        return 0
    return verify(did, pds, before)


def verify(did, pds, before):
    """What the account holds, what anyone else can still read, and who follows.

    A data server that has accepted a delete and an app view that has not yet
    seen it disagree, and the reader believes the app view, so what is still
    served is asked for again rather than taken on the delete's own word.
    """
    for attempt in range(ROUNDS):
        held = {c: len(client.read_records(did, pds, c)) for c in PURGED}
        feed = client.author_feed(did, limit=25)
        print(f"the account holds {held}; the public view serves {len(feed)}")
        if not any(held.values()) and not feed:
            break
        if attempt < ROUNDS - 1:
            time.sleep(20)
    after = client.profile(did)
    print(f"followers: {before.get('followersCount')} before, "
          f"{after.get('followersCount')} after")
    if feed:
        print("the public view is still serving posts the account no longer "
              "holds; it catches up on its own, and a later run says whether "
              "it has.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delete", action="store_true",
                        help="remove the records rather than listing them")
    parser.add_argument("--budget", type=float,
                        help="stop after this many seconds and say what is left")
    args = parser.parse_args()
    sys.exit(run(delete=args.delete, budget=args.budget))


if __name__ == "__main__":
    main()
