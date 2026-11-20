"""smoke_targets/check_bluesky_images.py — the `bluesky_images` smoke target, run by smoke.py."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from qt_headless import PROJECT_ROOT
from smoke_targets.failure import SmokeFailure


def check_bluesky_images() -> list[str]:
    """A picture outlives the post that carried it.

    The account's own pictures are gone, so the data server is stood in for by a
    fetcher that answers once and then records whether it was asked again.
    """
    root_dir = PROJECT_ROOT
    sys.path.insert(0, str(root_dir / "src" / "tools"))
    try:
        from bluesky import render as br
        from bluesky import store as bs
    finally:
        sys.path.pop(0)

    failures: list[str] = []
    picture = b"\x89PNG\r\n\x1a\n" + b"not really a png, but bytes are bytes"

    def record(name, cid, moment, mime="image/png"):
        return {
            "uri": f"at://me/app.bsky.feed.post/{name}",
            "cid": name,
            "value": {
                "text": name,
                "createdAt": moment,
                "embed": {
                    "$type": "app.bsky.embed.images",
                    "images": [
                        {
                            "alt": "a photograph of a cat",
                            "image": {"$type": "blob", "ref": {"$link": cid}, "mimeType": mime},
                        }
                    ],
                },
            },
        }

    with tempfile.TemporaryDirectory() as tmp:
        conn = bs.connect(Path(tmp) / "archive.db")
        kept_cid, gone_cid = "bafkreiKEPT", "bafkreiGONE"
        bs.keep_posts(
            conn,
            [
                record("a", kept_cid, "2026-03-01T12:00:00Z"),
                record("b", gone_cid, "2026-03-01T13:00:00Z"),
            ],
        )

        carrying = bs.records_with_images(conn)
        if len(carrying) != 2:
            failures.append(f"{len(carrying)} of 2 records read as carrying a picture")

        asked: list[str] = []

        def fetch(cid):
            asked.append(cid)
            return picture if cid == kept_cid else None

        def pass_once():
            already = bs.image_asked(conn)
            for uri, blobs in bs.records_with_images(conn):
                for cid, mime, alt in blobs:
                    if cid in already:
                        continue
                    data = fetch(cid)
                    if data is None:
                        bs.note_image_gone(conn, cid, uri, mime, alt)
                    else:
                        bs.keep_image(conn, cid, uri, mime, alt, data)

        pass_once()
        if sorted(asked) != sorted([kept_cid, gone_cid]):
            failures.append(f"a first pass asked for {asked}")
        kept_file = bs.kept_images(conn).get(kept_cid)
        if kept_file is None or not kept_file.exists():
            failures.append("the picture's bytes were not kept beside the store")
        elif kept_file.read_bytes() != picture:
            failures.append("the kept file is not the bytes that were fetched")
        if kept_file is not None and Path(tmp) not in kept_file.parents:
            failures.append(f"the picture was kept outside the store's folder: {kept_file}")

        # A second pass asks for nothing: the store remembers the asking as
        # well as the answer, including the blob that was already gone.
        asked.clear()
        pass_once()
        if asked:
            failures.append(f"a second pass asked again for {asked}")

        kept, gone, size = bs.image_totals(conn)
        if (kept, gone, size) != (1, 1, len(picture)):
            failures.append(f"the totals read {kept} kept, {gone} gone, {size} bytes")

        # The page shows the kept copy. Nothing here reaches a network, and the
        # address the view carried is a content network's copy that no longer
        # answers.
        br.use_kept_images(bs.kept_images(conn))
        view = {
            "embed": {
                "$type": "app.bsky.embed.images#view",
                "images": [
                    {
                        "alt": "a photograph of a cat",
                        "fullsize": f"https://cdn.example/img/feed_fullsize/plain/did:plc:me/{kept_cid}@jpeg",
                    }
                ],
            }
        }
        lines = br.describe_embed(view)
        if not lines or not lines[0].startswith("!["):
            failures.append(f"the page did not embed the kept picture: {lines}")
        elif kept_file is not None and kept_file.as_uri() not in lines[0]:
            failures.append(f"the page points somewhere other than the kept file: {lines[0]}")

        # A picture the store never kept still reads as it did before.
        missing_view = {
            "embed": {
                "$type": "app.bsky.embed.images#view",
                "images": [
                    {
                        "alt": "gone",
                        "fullsize": f"https://cdn.example/img/feed_fullsize/plain/did:plc:me/{gone_cid}@jpeg",
                    }
                ],
            }
        }
        fallback = br.describe_embed(missing_view)
        if not fallback or fallback[0].startswith("!["):
            failures.append(f"a picture the store lacks should keep its address: {fallback}")
        br.use_kept_images({})

    if failures:
        raise SmokeFailure("; ".join(failures))
    return [
        "a picture is kept once, beside its store, and a page shows the "
        "kept copy while a lost one keeps its words"
    ]
