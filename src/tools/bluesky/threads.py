"""Group an account's posts into conversations and cut each one back.

The rule has three clauses. Keep every post on a path from the thread's root
down to one of the account's own posts, so a conversation joined late still
arrives with the context that led to it. Drop every branch holding none of
them, so a popular thread does not bury the exchange that happened. Keep a
bounded number of posts that came after the account's last word, so a thread
that keeps growing does not grow the page with it.
"""

from __future__ import annotations

from datetime import datetime, timezone

DEFAULT_TAIL_CAP = 10
UNAVAILABLE = "unavailable"


class Node:
    """One post in a pruned conversation, or a marker where one is missing."""

    def __init__(self, uri, author, text, created, record=None, kind="post"):
        self.uri = uri
        self.author = author
        self.text = text
        self.created = created
        self.record = record or {}
        self.kind = kind
        self.mine = False
        self.children = []

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


def _moment(value):
    text = (value or "").replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def kept_record(post):
    """The parts of a fetched post a page is written from.

    A post as the app view returns it also carries avatars, counts, labels and
    viewer state that no page reads. Keeping the words and whatever the post
    carried with them, and nothing else, is what makes a stored conversation
    the size of the page it becomes.
    """
    if not post:
        return {}
    return {key: post[key] for key in ("record", "embed") if post.get(key) is not None}


def to_dict(node):
    """One pruned conversation as plain data, for keeping."""
    return {
        "uri": node.uri,
        "author": node.author,
        "text": node.text,
        "created": node.created.isoformat() if node.created else None,
        "record": kept_record(node.record),
        "kind": node.kind,
        "mine": node.mine,
        "children": [to_dict(child) for child in node.children],
    }


def from_dict(data):
    """A conversation read back from what `to_dict` wrote."""
    node = Node(
        uri=data.get("uri", ""),
        author=data.get("author"),
        text=data.get("text"),
        created=_moment(data["created"]) if data.get("created") else None,
        record=data.get("record"),
        kind=data.get("kind", "post"),
    )
    node.mine = bool(data.get("mine"))
    node.children = [from_dict(child) for child in data.get("children") or []]
    return node


def mine_uris(node):
    """The addresses of the account's own posts inside a pruned conversation."""
    return {item.uri for item in node.walk() if item.mine}


def root_uri(record):
    """The address of the thread a post record belongs to.

    A reply names its root; a post that is not a reply is its own root. Grouping
    on this is what makes several replies to several branches of one original
    post a single section rather than several.
    """
    reply = (record.get("value") or {}).get("reply")
    if reply and reply.get("root", {}).get("uri"):
        return reply["root"]["uri"]
    return record["uri"]


def group_by_thread(records):
    """Thread root address -> the account's posts in that thread, oldest first."""
    groups = {}
    for record in records:
        groups.setdefault(root_uri(record), []).append(record)
    for posts in groups.values():
        posts.sort(key=lambda r: _moment((r.get("value") or {}).get("createdAt")))
    return groups


def _build(raw):
    """One app view thread node, and everything under it, as Node objects."""
    kind = raw.get("$type", "")
    if kind.endswith("notFoundPost") or kind.endswith("blockedPost"):
        gone = Node(raw.get("uri", ""), None, None, None, kind=UNAVAILABLE)
        # The app view returns a missing post as a leaf. It gains a child only
        # where the climb below put the post underneath it back, which is how a
        # reply outlives the post it answered.
        for child in raw.get("replies") or []:
            gone.children.append(_build(child))
        return gone
    post = raw.get("post") or {}
    record = post.get("record") or {}
    node = Node(
        uri=post.get("uri", ""),
        author=(post.get("author") or {}).get("handle", ""),
        text=record.get("text", ""),
        created=_moment(record.get("createdAt")),
        record=post,
    )
    for child in raw.get("replies") or []:
        node.children.append(_build(child))
    node.children.sort(key=lambda n: n.created or datetime.min.replace(tzinfo=timezone.utc))
    return node


def _climb_to_root(raw):
    """The topmost node of a fetched thread, however far up the account sits."""
    seen = raw
    while isinstance(seen, dict) and isinstance(seen.get("parent"), dict):
        parent = dict(seen["parent"])
        parent["replies"] = [{k: v for k, v in seen.items() if k != "parent"}]
        seen = parent
        if parent.get("$type", "").endswith(("notFoundPost", "blockedPost")):
            break
    return seen


def build_tree(raw_thread, mine_uris):
    """A fetched thread as a tree, with the account's own posts marked."""
    root = _build(_climb_to_root(raw_thread))
    for node in root.walk():
        node.mine = node.uri in mine_uris
    return root


def prune(root, tail_cap=DEFAULT_TAIL_CAP):
    """The tree cut back to the conversation the account was part of.

    Returns a new tree, or None when the account appears nowhere in it.
    """
    def mark(node):
        found = node.mine
        for child in node.children:
            if mark(child):
                found = True
        node.reaches_me = found
        return found

    if not mark(root):
        return None

    copies = {}

    def copy_kept(node):
        """node and every branch under it that reaches one of my posts."""
        copy = Node(node.uri, node.author, node.text, node.created, node.record, node.kind)
        copy.mine = node.mine
        copies[node.uri] = copy
        for child in node.children:
            if child.reaches_me:
                copy.children.append(copy_kept(child))
        return copy

    kept = copy_kept(root)

    # Everything written after my last word in this conversation: any descendant
    # of one of my posts that the pass above dropped. They are admitted oldest
    # first, and only once their own parent is in, so the result is a connected
    # subtree. A reply is always written after the post it answers, so
    # chronological order already respects that.
    candidates = []
    for node in root.walk():
        if not node.mine:
            continue
        for child in node.children:
            for descendant in child.walk():
                if descendant.uri not in copies:
                    candidates.append(descendant)
    seen = set()
    unique = []
    for node in candidates:
        if node.uri in seen:
            continue
        seen.add(node.uri)
        unique.append(node)
    unique.sort(key=lambda n: n.created or datetime.min.replace(tzinfo=timezone.utc))

    parents = {}
    for node in root.walk():
        for child in node.children:
            parents[child.uri] = node.uri

    admitted = 0
    for node in unique:
        if admitted >= tail_cap:
            break
        parent_uri = parents.get(node.uri)
        holder = copies.get(parent_uri)
        if holder is None:
            continue
        copy = Node(node.uri, node.author, node.text, node.created, node.record, node.kind)
        copies[node.uri] = copy
        holder.children.append(copy)
        admitted += 1

    def sort_children(node):
        node.children.sort(key=lambda n: n.created or datetime.min.replace(tzinfo=timezone.utc))
        for child in node.children:
            sort_children(child)

    sort_children(kept)
    return kept


def conversation(root, my_uris, fetch, tail_cap=DEFAULT_TAIL_CAP):
    """One thread, fetched and cut back, or None where nothing survives.

    The root is asked for first, because it returns the whole tree in one call.
    Two things can make that tree useless: the root has been deleted, so there
    is no tree; or the tree comes back without the account's own post in it,
    which is what happens when a reply has been hidden or detached from the
    conversation by whoever started it. Both are answered the same way — ask
    for the account's own newest post in that thread and climb the replies
    above it, which is the same conversation seen from lower down.
    """
    my_uris = set(my_uris)

    def usable(raw):
        return raw is not None and not raw.get("$type", "").endswith(
            ("notFoundPost", "blockedPost"))

    raw = fetch(root, 100, 1)
    if usable(raw):
        kept = prune(build_tree(raw, my_uris), tail_cap=tail_cap)
        if kept is not None:
            return kept

    for uri in sorted(my_uris, reverse=True):
        raw = fetch(uri, 100, 100)
        if not usable(raw):
            continue
        kept = prune(build_tree(raw, my_uris), tail_cap=tail_cap)
        if kept is not None:
            return kept
    return None
