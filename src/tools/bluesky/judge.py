#!/usr/bin/env python3
"""Sort every post the account made into what the notebook keeps.

The account is emptied online, so there is one threshold left and it is the
notebook's: a private record kept for a later think. This program does not
judge. It hands a reader the posts in a stable order with the conversation each
one sat in, takes back a verdict per post, and keeps the verdicts where a
second run will not ask for them again.

    python3 src/tools/bluesky/judge.py status
    python3 src/tools/bluesky/judge.py batch --from 0 --count 150
    python3 src/tools/bluesky/judge.py record --file verdicts.txt
    python3 src/tools/bluesky/judge.py sample --count 100 --seed 7
    python3 src/tools/bluesky/judge.py compare --file review.txt
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bluesky import render, store, threads  # noqa: E402
from config_tools import data_paths  # noqa: E402

VERDICTS = ("keep", "prune", "unsure")

STANDARD = """\
One verdict per post, for the notebook alone. Nothing here is about what the
account shows the world: the account is empty, and no post is being judged for
whether it should have been public. The only question is whether a private
record of this author's thinking is better for holding it.

keep    The post made something - an argument, a parody, a joke with a shape, a
        recommendation, an observation worth meeting again. A subject the
        author would not defend in public is not a reason to lose it; that
        class is what this archive exists to hold. Most posts are keeps.
prune   The post made nothing. Anger with no idea in it. A take whose content
        is an insult rather than a thought. A reply that adds nothing of its
        own even with the post it answers in view - a bare agreement, a
        one-word answer, a reaction.
unsure  A joke about the author's own death or harm, which reads identically to
        outward-aimed dark humour and completely differently to a person. Also
        any post a reader would want a second opinion on. unsure is a verdict,
        not a failure to reach one.

Read the conversation above a post before judging it: a reply read alone is not
the thing that was said. Judge only the numbered posts.
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS verdict (
    uri        TEXT PRIMARY KEY,
    verdict    TEXT NOT NULL,
    reason     TEXT,
    decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review (
    uri        TEXT PRIMARY KEY,
    verdict    TEXT NOT NULL,
    reason     TEXT,
    decided_at TEXT NOT NULL
);
"""


def verdict_path():
    """The verdicts' own file, beside the store, inside the git-ignored tree."""
    folder = data_paths.ensure_dir(f"data/{data_paths.instance_slug()}/bluesky")
    return folder / "verdicts.db"


def connect(path=None):
    target = data_paths.ensure_db(Path(path) if path else verdict_path(), SCHEMA)
    conn = sqlite3.connect(str(target), timeout=30)
    conn.execute("PRAGMA busy_timeout=20000")
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.row_factory = sqlite3.Row
    return conn


# --- the corpus, in one fixed order ------------------------------------------

def corpus(archive):
    """Every post the account made, oldest first, each with its conversation.

    The order is the whole addressing scheme: a post's number is its position
    here, so two runs hand the same reader the same numbers.
    """
    posts = []
    for row in archive.execute(
            "SELECT uri, created_at, record FROM post ORDER BY created_at, uri"):
        posts.append({"uri": row["uri"], "created": row["created_at"],
                      "record": json.loads(row["record"])})
    for index, post in enumerate(posts):
        post["n"] = index
    return posts


def own_uris(archive):
    """Every address the account's own posts have, for spotting them in a tree.

    A stored conversation's `mine` flag marks the posts the day it was written
    for, so a conversation spanning two days carries the flag on one day's
    posts alone. The addresses are the account's whole record and do not move.
    """
    return {row[0] for row in archive.execute("SELECT uri FROM post")}


def thread_lines(archive, root, own):
    """One stored conversation as speaker-and-words lines, or none where it is
    not kept. The account's own posts come back keyed by their address."""
    row = archive.execute("SELECT tree FROM thread WHERE root_uri = ?",
                          (root,)).fetchone()
    if not row:
        return None
    node = threads.from_dict(json.loads(row["tree"]))
    lines = []
    for item in node.walk():
        if item.kind != "post":
            lines.append(("", None))
            continue
        text = render._one_line(render.resolve_links(
            (item.record or {}).get("record") or {}))
        extra = attachments(item.record or {})
        if extra:
            text = f"{text} {extra}".strip()
        who = item.uri if item.uri in own else (item.author or "someone")
        lines.append((who, text))
    return lines


def attachments(post):
    """What a post carried, in the words a reader needs and no address.

    A page links an image so it can be looked at; a judgment reads the words
    around it, so the address is weight without meaning here.
    """
    out = []
    for line in render.describe_embed(post):
        line = re.sub(r"\[([^\]]*)\]\(([^)]*)\)", r"\1", line)
        out.append(line)
    return " ".join(out)


def own_lines(post):
    """A post standing alone: its words and whatever it carried."""
    value = post["record"].get("value") or {}
    text = render._one_line(render.resolve_links(value))
    extra = attachments({"record": value, "embed": value.get("embed")})
    return f"{text} {extra}".strip()


def block(archive, posts, own):
    """The reader's view of one conversation and the posts being judged in it.

    A reply read alone is not the thing that was said, so where the thread is
    kept the whole path down to the account's posts comes with it. Several of
    the account's posts in one conversation are numbered inside one copy of it
    rather than repeating the conversation once per post.
    """
    wanted = {post["uri"]: post["n"] for post in posts}
    first = posts[0]
    lines = thread_lines(archive, threads.root_uri(first["record"]), own)
    out = []
    if lines:
        out.append(f"--- {first['created'][:10]}")
        for who, text in lines:
            if who == "":
                out.append("    (a post that is gone)")
            elif who in wanted:
                out.append(f"  [{wanted.pop(who)}] ME: {text}")
            elif who in own:
                out.append(f"    ME: {text}")
            else:
                out.append(f"    {who}: {text}")
    for post in posts:
        if post["uri"] in wanted:
            out.append(f"[{post['n']}] {post['created'][:10]} ME: {own_lines(post)}")
    return "\n".join(out)


def whole_conversations(pool, count):
    """The first `count` posts, plus any that follow in a conversation already
    open, so a conversation is read once rather than split across two batches."""
    window = pool[:count]
    roots = {threads.root_uri(post["record"]) for post in window}
    for post in pool[count:]:
        if threads.root_uri(post["record"]) not in roots:
            break
        window.append(post)
    return window


def grouped(archive, posts):
    """The window's posts, gathered into the conversations they sat in."""
    order, groups = [], {}
    for post in posts:
        root = threads.root_uri(post["record"])
        if root not in groups:
            order.append(root)
            groups[root] = []
        groups[root].append(post)
    return [groups[root] for root in order]


# --- commands ----------------------------------------------------------------

def cmd_status(args):
    archive = store.connect()
    conn = connect(args.verdicts)
    total = len(corpus(archive))
    judged = conn.execute("SELECT COUNT(*) FROM verdict").fetchone()[0]
    print(f"posts    {total}")
    print(f"judged   {judged}")
    print(f"left     {total - judged}")
    for name in VERDICTS:
        count = conn.execute("SELECT COUNT(*) FROM verdict WHERE verdict = ?",
                             (name,)).fetchone()[0]
        print(f"  {name:<7}{count}")
    reviewed = conn.execute("SELECT COUNT(*) FROM review").fetchone()[0]
    if reviewed:
        print(f"reviewed {reviewed}")


def cmd_batch(args):
    archive = store.connect()
    conn = connect(args.verdicts)
    posts = corpus(archive)
    judged = {row[0] for row in conn.execute("SELECT uri FROM verdict")}
    pool = posts[args.start:] if not args.unjudged else \
        [p for p in posts[args.start:] if p["uri"] not in judged]
    window = whole_conversations(pool, args.count)
    if not window:
        print("nothing left in that window")
        return
    if not args.bare:
        print(STANDARD)
        print(f"Answer one line per numbered post: <number> <{'|'.join(VERDICTS)}>"
              " [a few words, for prune and unsure]\n")
    own = own_uris(archive)
    for group in grouped(archive, window):
        print(block(archive, group, own))
        print()
    print(f"# {len(window)} posts, numbers {window[0]['n']}-{window[-1]['n']}")


def _read_verdicts(handle, posts):
    """Lines of `<number> <verdict> [reason]` as (uri, verdict, reason)."""
    by_number = {post["n"]: post for post in posts}
    out = []
    for line in handle:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        number = int(parts[0].strip("[]"))
        name = parts[1].lower()
        if name not in VERDICTS:
            raise SystemExit(f"line {line!r}: {name} is not one of {VERDICTS}")
        if number not in by_number:
            raise SystemExit(f"line {line!r}: no post numbered {number}")
        out.append((by_number[number]["uri"], name,
                    parts[2].strip() if len(parts) > 2 else None))
    return out


def _write(conn, table, rows):
    from datetime import datetime, timezone
    moment = datetime.now(timezone.utc).isoformat()
    written = 0
    for uri, name, reason in rows:
        conn.execute(
            f"INSERT INTO {table} (uri, verdict, reason, decided_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(uri) DO UPDATE SET "
            "verdict = excluded.verdict, reason = excluded.reason, "
            "decided_at = excluded.decided_at",
            (uri, name, reason, moment))
        written += 1
    conn.commit()
    return written


def cmd_record(args):
    archive = store.connect()
    conn = connect(args.verdicts)
    posts = corpus(archive)
    handle = open(args.file) if args.file else sys.stdin
    rows = _read_verdicts(handle, posts)
    print(f"recorded {_write(conn, args.table, rows)}")


def cmd_sample(args):
    """Posts already judged, handed over without their verdicts.

    A check on a judgment shown the judgment is not a check, so the reader
    sampled here judges blind and `compare` counts where the two differ.
    """
    archive = store.connect()
    conn = connect(args.verdicts)
    posts = corpus(archive)
    judged = {row[0] for row in conn.execute("SELECT uri FROM verdict")}
    pool = [p for p in posts if p["uri"] in judged]
    if len(pool) < args.count:
        raise SystemExit(f"only {len(pool)} posts are judged")
    picked = sorted(random.Random(args.seed).sample(pool, args.count),
                    key=lambda p: p["n"])
    print(STANDARD)
    print(f"Answer one line per numbered post: <number> <{'|'.join(VERDICTS)}>"
          " [a few words, for prune and unsure]\n")
    own = own_uris(archive)
    for group in grouped(archive, picked):
        print(block(archive, group, own))
        print()
    print(f"# {len(picked)} posts, seed {args.seed}")


def cmd_compare(args):
    archive = store.connect()
    conn = connect(args.verdicts)
    posts = corpus(archive)
    by_uri = {post["uri"]: post for post in posts}
    first = {row["uri"]: row["verdict"] for row in
             conn.execute("SELECT uri, verdict FROM verdict")}
    second = {row["uri"]: row["verdict"] for row in
              conn.execute("SELECT uri, verdict FROM review")}
    shared = [uri for uri in second if uri in first]
    disagreed = [uri for uri in shared if first[uri] != second[uri]]
    print(f"compared   {len(shared)}")
    print(f"agreed     {len(shared) - len(disagreed)}")
    print(f"disagreed  {len(disagreed)}")
    for uri in sorted(disagreed, key=lambda u: by_uri[u]["n"]):
        print(f"\n[{by_uri[uri]['n']}] judged {first[uri]}, reviewed {second[uri]}")
        print(f"    {own_lines(by_uri[uri])}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verdicts", help="a verdict file other than the real one")
    subs = parser.add_subparsers(dest="command", required=True)

    subs.add_parser("status").set_defaults(run=cmd_status)

    batch = subs.add_parser("batch")
    batch.add_argument("--from", dest="start", type=int, default=0)
    batch.add_argument("--count", type=int, default=100)
    batch.add_argument("--unjudged", action="store_true",
                       help="skip posts already judged, keeping their numbers")
    batch.add_argument("--bare", action="store_true",
                       help="leave out the standard and the instruction")
    batch.set_defaults(run=cmd_batch)

    record = subs.add_parser("record")
    record.add_argument("--file")
    record.add_argument("--table", choices=("verdict", "review"), default="verdict")
    record.set_defaults(run=cmd_record)

    sample = subs.add_parser("sample")
    sample.add_argument("--count", type=int, default=100)
    sample.add_argument("--seed", type=int, default=1)
    sample.set_defaults(run=cmd_sample)

    subs.add_parser("compare").set_defaults(run=cmd_compare)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
