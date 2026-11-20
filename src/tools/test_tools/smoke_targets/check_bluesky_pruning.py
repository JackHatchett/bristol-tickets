"""smoke_targets/check_bluesky_pruning.py — the `bluesky_pruning` smoke target, run by smoke.py."""

from __future__ import annotations

import sys

from qt_headless import PROJECT_ROOT
from smoke_targets.failure import SmokeFailure


def check_bluesky_pruning() -> list[str]:
    """The thread pruner keeps what it should and drops what it should.

    These cases are built by hand rather than fetched, because the guardrails
    they check — the cap on what is kept after the account's last word, the
    placeholder where a post is gone — fire rarely in real data and would
    otherwise be checked only by whichever conversation happened to be busy
    that week.
    """
    root_dir = PROJECT_ROOT
    sys.path.insert(0, str(root_dir / "src" / "tools"))
    try:
        from bluesky import threads as bt
    finally:
        sys.path.pop(0)

    stamp = 0

    def node(author, text, mine=False, kind="post", children=()):
        nonlocal stamp
        stamp += 1
        return {
            "$type": (
                "app.bsky.feed.defs#notFoundPost"
                if kind != "post"
                else "app.bsky.feed.defs#threadViewPost"
            ),
            "uri": f"at://x/{author}/{stamp}",
            "post": {
                "uri": f"at://x/{author}/{stamp}",
                "author": {"handle": author},
                "record": {"text": text, "createdAt": f"2026-01-01T00:{stamp:02d}:00Z"},
            },
            "replies": list(children),
            "_mine": mine,
        }

    def uris_of(tree, only_mine=True):
        found = []
        stack = [tree]
        while stack:
            item = stack.pop()
            if only_mine and not item.get("_mine"):
                pass
            elif item.get("uri"):
                found.append(item["uri"])
            stack.extend(item.get("replies") or [])
        return found

    failures: list[str] = []

    def _kept(tree):
        if tree is None:
            raise SmokeFailure("pruning dropped a whole conversation it should keep")
        return tree

    # A branch with none of my posts goes; the one containing them stays, with
    # every post above it.
    mine_leaf = node("me", "my reply", mine=True)
    tree = node(
        "op",
        "the original",
        children=[
            node("stranger", "a branch I never touched", children=[node("other", "and its reply")]),
            node("friend", "a branch I answered", children=[mine_leaf]),
        ],
    )
    kept = _kept(bt.prune(bt.build_tree(tree, set(uris_of(tree)))))
    authors = sorted(n.author for n in kept.walk())
    if authors != ["friend", "me", "op"]:
        failures.append(f"branch pruning kept {authors}")

    # Two branches of one original post that I answered stay one conversation.
    a = node("me", "first branch", mine=True)
    b = node("me", "second branch", mine=True)
    tree = node(
        "op",
        "the original",
        children=[
            node("friend", "one", children=[a]),
            node("other", "two", children=[b]),
            node("stranger", "three"),
        ],
    )
    kept = _kept(bt.prune(bt.build_tree(tree, set(uris_of(tree)))))
    if len(kept.children) != 2 or sum(1 for n in kept.walk() if n.mine) != 2:
        failures.append("two answered branches did not come back as one tree")

    # What came after my last word is capped, and the cap is the whole section.
    tail = [node("fan", f"reply {i}") for i in range(25)]
    mine = node("me", "my post", mine=True, children=tail)
    kept = _kept(bt.prune(bt.build_tree(mine, set(uris_of(mine))), tail_cap=10))
    after = sum(1 for n in kept.walk() if not n.mine)
    if after != 10:
        failures.append(f"tail cap of 10 kept {after}")
    kept = _kept(bt.prune(bt.build_tree(mine, set(uris_of(mine))), tail_cap=3))
    after = sum(1 for n in kept.walk() if not n.mine)
    if after != 3:
        failures.append(f"tail cap of 3 kept {after}")

    # A post on a kept path that is gone is shown, not skipped, so two posts
    # that were never adjacent are not joined.
    mine = node("me", "my reply under a deleted post", mine=True)
    mine["parent"] = {"$type": "app.bsky.feed.defs#notFoundPost", "uri": "at://x/gone/0"}
    kept = _kept(bt.prune(bt.build_tree(mine, {mine["uri"]})))
    kinds = [n.kind for n in kept.walk()]
    if bt.UNAVAILABLE not in kinds:
        failures.append("a deleted post on a kept path was dropped rather than marked")

    # A thread I am not in produces nothing at all.
    tree = node("op", "the original", children=[node("stranger", "a reply")])
    if bt.prune(bt.build_tree(tree, set())) is not None:
        failures.append("a thread containing none of my posts was not dropped")

    # A deleted root falls back to my own post and still returns the thread.
    asked: list[str] = []
    survivor = node("me", "my post", mine=True)

    def fetch(uri, depth, parent_height):
        asked.append(uri)
        if len(asked) == 1:
            return {"$type": "app.bsky.feed.defs#notFoundPost", "uri": uri}
        return survivor

    got = bt.conversation("at://x/op/0", [survivor["uri"]], fetch)
    if got is None or len(asked) != 2:
        failures.append("a deleted root did not fall back to my own post")

    if failures:
        raise SmokeFailure("; ".join(failures))
    return [
        "thread pruning keeps the branches I am in, caps what follows me, "
        "marks what is gone, and survives a deleted root"
    ]
