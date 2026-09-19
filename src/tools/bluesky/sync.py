#!/usr/bin/env python3
"""Copy an account's Bluesky posts into the Markdown notebook, day by day.

The one-time copy of everything and the daily copy of what is new are the same
run with a different date window, so there is no second code path that could
drift from the first.

    python3 src/tools/bluesky/sync.py --days 7
    python3 src/tools/bluesky/sync.py --all
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve()
TOOLS = HERE.parents[1]
ROOT = HERE.parents[3]
sys.path.insert(0, str(TOOLS))

from bluesky import client, judge, render, store, threads  # noqa: E402
from config_tools import data_paths  # noqa: E402

CONFIG_READER = ROOT / "src" / "tools" / "config_tools" / "read_config.py"
JOURNAL_ANCHOR = "#### Notes Created Today"
JOURNAL_HEADING = "#### Bluesky"


def setting(key, default=None):
    """One field of the local configuration, or a default where it is unset."""
    result = subprocess.run(
        [sys.executable, str(CONFIG_READER), f"bluesky.{key}"],
        capture_output=True, text=True)
    value = result.stdout.strip()
    if result.returncode != 0 or not value or value == "None":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def required(key):
    """One field that has no sensible default, because its value names a folder
    in the user's own notebook and no guess at one belongs in this tree."""
    value = setting(key)
    if not value:
        sys.exit(f"bluesky.{key} is not set in config; nothing to write against.")
    return value


def account():
    """The account identifier and its data server, resolving them if unset."""
    handle = setting("handle")
    if not handle:
        sys.exit("bluesky.handle is not set in config; nothing to read.")
    did, pds = setting("did"), setting("pds")
    if not did or not pds:
        did, pds = client.resolve_account(handle)
        print(f"resolved {handle}: {did} at {pds}")
        print("write these into config as bluesky.did and bluesky.pds to skip "
              "this lookup next time.")
    return did, pds


def page_path(day, folder, prefix):
    """Where a day's page lives: by year, then month, the way the journal is."""
    return (data_paths.resolve(folder) / f"{day:%Y}" / f"{day:%m}"
            / f"{prefix}{day:%Y-%m-%d}.md")


def journal_path(day, folder):
    return data_paths.resolve(folder) / f"{day:%Y}" / f"{day:%m}" / f"{day:%Y-%m-%d}.md"


def link_into_journal(journal_file, page_file):
    """One line naming the day's Bluesky page, added to a file Jack authors.

    The write is insert-only: it adds a heading and a link at a fixed anchor if
    they are not already there, and rewrites, reorders and removes nothing. A
    second run finds the link and leaves the file byte-for-byte as it was.
    """
    text = journal_file.read_text(encoding="utf-8")
    target = page_file.stem
    if f"[[{target}" in text:
        return False
    block = f"{JOURNAL_HEADING}\n\n[[{target}|Bluesky]]\n\n---\n\n"
    if JOURNAL_ANCHOR in text:
        updated = text.replace(JOURNAL_ANCHOR, block + JOURNAL_ANCHOR, 1)
    else:
        updated = text.rstrip("\n") + "\n\n---\n\n" + block.rstrip("\n") + "\n"
    journal_file.write_text(updated, encoding="utf-8")
    return True


def build_day(day, records, get_thread, tail_cap, keep, dropped, workers=1,
              handle=""):
    """Every conversation the account took part in on one day, pruned.

    A day is a handful of independent conversations and the time is all spent
    waiting on the network, so they are fetched together. Each fetched
    conversation goes through `keep`, which answers with the one the page is
    written from, so what reaches the page comes out of the store rather than
    off the wire. The order of the finished sections still follows the order of
    the day's own posts, which is what keeps a page the same on every run.
    """
    grouped = threads.group_by_thread(records)
    work = [(root, {r["uri"] for r in mine}) for root, mine in grouped.items()]

    def one(item):
        root, mine = item
        return root, threads.conversation(root, mine, get_thread, tail_cap=tail_cap)

    if workers > 1 and len(work) > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            fetched = list(pool.map(one, work))
    else:
        fetched = [one(item) for item in work]
    kept_trees = [keep(root, tree) for root, tree in fetched]
    # The store holds every post; the page shows the ones the notebook keeps.
    shown = [threads.without(tree, dropped) for tree in kept_trees
             if tree is not None]
    shown = [tree for tree in shown if tree is not None]

    # A post whose conversation was never kept is on its day in its own right.
    # The account was emptied, so those conversations can never be fetched now,
    # and the posts' own words are what the store has.
    place = {record["uri"]: index for index, record in enumerate(records)}
    covered = {node.uri for tree in shown for node in tree.walk()}
    sections = []
    for tree in shown:
        first = min((place[node.uri] for node in tree.walk()
                     if node.uri in place), default=len(place))
        sections.append((first, render.render_section(tree)))
    for record in records:
        uri = record.get("uri")
        if uri in covered or uri in dropped:
            continue
        section = threads.solo_from_record(record, handle)
        sections.append((place[uri], render.render_section(section)))
    sections.sort(key=lambda item: item[0])
    return [section for _, section in sections]


def keep_images(conn, did, pds):
    """Every picture the store has not asked about yet, fetched and kept.

    A blob already kept, or already found gone, is not asked for twice: the
    store remembers the asking as well as the answer, which is what keeps a
    daily run from re-reading a picture corpus every morning.
    """
    asked = store.image_asked(conn)
    wanted = [(uri, blob) for uri, blobs in store.records_with_images(conn)
              for blob in blobs if blob[0] not in asked]
    if not wanted:
        kept, gone, size = store.image_totals(conn)
        print(f"{kept} pictures kept, {gone} gone, {size / 1e6:.1f} MB on disk")
        return
    fetched = missing = 0
    for uri, (cid, mime, alt) in wanted:
        data = client.fetch_blob(pds, did, cid)
        if data is None:
            store.note_image_gone(conn, cid, uri, mime, alt)
            missing += 1
            continue
        store.keep_image(conn, cid, uri, mime, alt, data)
        fetched += 1
    kept, gone, size = store.image_totals(conn)
    print(f"{fetched} pictures kept this run, {missing} the data server no "
          f"longer serves")
    print(f"{kept} pictures kept in all, {gone} gone, "
          f"{size / 1e6:.1f} MB on disk")


def run(window_days=None, dry_run=False, skip_existing=False, budget=None,
        start_from=None, from_store=False):
    zone = ZoneInfo(setting("timezone", "UTC"))
    folder = required("notes_folder")
    journal_folder = required("journal_folder")
    prefix = setting("filename_prefix", "bluesky_")
    tail_cap = int(setting("thread_tail_cap", threads.DEFAULT_TAIL_CAP))
    link_window = int(setting("link_window_days", 30))
    do_link = bool(setting("link_into_journal", True))
    workers = int(setting("fetch_workers", 6))

    since = None
    if window_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
    conn = store.connect()
    account_handle = setting("handle", "")
    if from_store:
        posts = []
        get_thread = lambda *_args, **_kwargs: None  # noqa: E731
        print("writing from the store; reaching no account")
    else:
        did, pds = account()
        get_thread = client.get_thread
        posts = client.read_posts(did, pds, since=since)
        print(f"{len(posts)} post records read")
    if not dry_run:
        added = store.keep_posts(conn, posts)
        print(f"{added} of them the store had not seen; it holds "
              f"{store.post_count(conn)} posts and "
              f"{store.thread_count(conn)} conversations")

    if not dry_run and not from_store:
        keep_images(conn, did, pds)

    # Every page written this run shows the pictures the store holds.
    render.use_kept_images(store.kept_images(conn))

    # The pages are written from the store, so a post deleted from the account
    # keeps its place on the day it belongs to.
    by_day = store.records_by_day(conn, zone, since=since)
    if dry_run:
        known = {r.get("uri") for day in by_day.values() for r in day}
        for record in posts:
            if record.get("uri") not in known:
                by_day[client.created_at(record).astimezone(zone).date()].append(record)
        for day in by_day:
            by_day[day].sort(key=client.created_at)
    print(f"{len(by_day)} days with posts")
    dropped = judge.pruned_uris()
    if dropped:
        print(f"{len(dropped)} posts the notebook does not keep")

    def keep(root, tree):
        """The conversation a page is written from, kept where it may be."""
        if dry_run:
            return tree if tree is not None else store.load_thread(conn, root)
        return store.keep_thread(conn, root, tree)

    written = 0
    skipped = 0
    started = time.monotonic()
    days = [d for d in sorted(by_day) if start_from is None or d >= start_from]
    if skip_existing:
        keep = []
        for day in days:
            if page_path(day, folder, prefix).exists():
                skipped += 1
            else:
                keep.append(day)
        days = keep

    stopped_at = None

    def handle(day):
        """One day, from its posts to its page. Safe to run beside others,
        because every day writes its own file and its own journal page."""
        sections = build_day(day, by_day[day], get_thread, tail_cap,
                             keep, dropped, workers=1, handle=account_handle)
        if not sections:
            return None
        destination = page_path(day, folder, prefix)
        first = client.created_at(by_day[day][0]).astimezone(zone)
        journal_file = journal_path(day, journal_folder)
        link = f"[[{journal_file.stem}|Journal]]" if journal_file.exists() else None
        page = render.render_page(
            datetime.combine(day, datetime.min.time()), sections,
            journal_link=link, created=first)
        if dry_run:
            print(f"would write {destination}")
            return None
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Written whole and only when it changes, so a re-run leaves the
        # notebook's modification times alone.
        changed = (not destination.exists()
                   or destination.read_text(encoding="utf-8") != page)
        if changed:
            destination.write_text(page, encoding="utf-8")
        if link and do_link:
            link_into_journal(journal_file, destination)
        return changed

    # A day is independent of every other day and the time is all spent waiting
    # on the network, so several are worked at once.
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        pending = list(days)
        while pending or futures:
            while pending and len(futures) < workers:
                day = pending.pop(0)
                futures[pool.submit(handle, day)] = day
            if budget is not None and time.monotonic() - started > budget and pending:
                stopped_at = pending[0]
                pending = []
            for future in list(futures):
                if not future.done():
                    continue
                day = futures.pop(future)
                done += 1
                if future.result():
                    written += 1
                if done % 50 == 0:
                    print(f"  {done} of {len(days)} days seen, {written} written")
            time.sleep(0.05)

    if stopped_at is not None:
        print(f"stopping at {stopped_at} to stay inside the time budget")

    print(f"{written} pages written or updated"
          + (f", {skipped} already there" if skipped else ""))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--days", type=int, help="copy this many days back")
    group.add_argument("--all", action="store_true", help="copy the whole history")
    parser.add_argument("--dry-run", action="store_true",
                        help="say what would be written and write nothing")
    parser.add_argument("--skip-existing", action="store_true",
                        help="leave a day alone where its page is already there")
    parser.add_argument("--from", dest="start_from",
                        help="begin at this date (YYYY-MM-DD) rather than the first")
    parser.add_argument("--budget", type=float,
                        help="stop after this many seconds and say what is left")
    parser.add_argument("--from-store", dest="from_store", action="store_true",
                        help="write the pages from what the store already "
                             "holds, reaching no account")
    args = parser.parse_args()
    start = (datetime.strptime(args.start_from, "%Y-%m-%d").date()
             if args.start_from else None)
    sys.exit(run(window_days=None if args.all else args.days, dry_run=args.dry_run,
                 skip_existing=args.skip_existing, budget=args.budget,
                 start_from=start, from_store=args.from_store))


if __name__ == "__main__":
    main()
