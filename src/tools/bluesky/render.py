"""Turn a day's pruned conversations into one Markdown page.

A solo post is prose, the way the notebook's other prose notes are spaced. A
conversation is a bulleted outline that follows its own branching rather than a
flat chronology, so a reader can see who answered whom.

The account owner's own posts are set apart as quotes, each carrying a block
identifier taken from the post's record key, so any one of them can be embedded
in another note as `![[bluesky_YYYY-MM-DD#^bsky-<key>]]` and the embed still
resolves after a rebuild. Nothing on a page is bold: bolding in the notebook is
the user's (`src/skills/note-formatting/SKILL.md` §Emphasis).
"""

from __future__ import annotations

import re
from pathlib import Path

UNAVAILABLE_LINE = "*[post unavailable]*"


def resolve_links(record):
    """A post's text with its links spelled out in full.

    Bluesky stores a shortened display form in the text and the address itself
    in the post's facets, so text taken alone carries links that go nowhere.
    Facet offsets count bytes, so the substitution is done on the encoded text.
    """
    text = record.get("text") or ""
    facets = record.get("facets") or []
    raw = text.encode("utf-8")
    swaps = []
    for facet in facets:
        for feature in facet.get("features") or []:
            if feature.get("$type", "").endswith("link") and feature.get("uri"):
                index = facet.get("index") or {}
                start, end = index.get("byteStart"), index.get("byteEnd")
                if start is None or end is None:
                    continue
                swaps.append((start, end, feature["uri"]))
    if not swaps:
        return text
    swaps.sort(key=lambda s: s[0], reverse=True)
    for start, end, uri in swaps:
        raw = raw[:start] + uri.encode("utf-8") + raw[end:]
    return raw.decode("utf-8", "replace")


def _one_line(text):
    """Whitespace collapsed, because a bullet that wraps onto its own line
    stops being part of the list."""
    return " ".join((text or "").split())


# The picture files the store has kept, by the blob each one is. A run sets
# this once, before any page is written, so a page shows the copy on the machine
# rather than an address on a content network that outlives nothing. Empty means
# nothing is kept, and a page falls back to the address it had.
KEPT_IMAGES: dict = {}


def use_kept_images(mapping):
    """Point the renderer at the pictures the store holds."""
    KEPT_IMAGES.clear()
    KEPT_IMAGES.update(mapping or {})


def _blob_of(address):
    """The blob an image address names, which is what the store keeps it by.

    A rendered address ends `/plain/<did>/<cid>@jpeg`, so the blob is the last
    path segment before the format.
    """
    if not address:
        return None
    tail = address.rstrip("/").rsplit("/", 1)[-1]
    return tail.split("@", 1)[0] or None


def describe_embed(post):
    """The lines an attachment adds under a post, or none where it adds nothing.

    An image shows from the copy the store kept where there is one, so the page
    renders after the account is emptied; where there is none it contributes the
    words its author wrote about it and the address it had. A quoted post
    contributes its text.
    """
    lines = []
    embed = post.get("embed") or {}
    kind = embed.get("$type", "")

    images = embed.get("images")
    if kind.endswith("recordWithMedia#view"):
        media = embed.get("media") or {}
        images = media.get("images") or images
    for image in images or []:
        alt = _one_line(image.get("alt")) or "image"
        address = image.get("fullsize") or image.get("thumb") or ""
        # A rendered view names the picture by address; the record the store
        # holds names it by the blob itself, which is the same picture.
        blob = ((image.get("image") or {}).get("ref") or {}).get("$link")
        kept = KEPT_IMAGES.get(blob or _blob_of(address))
        if kept is not None:
            lines.append(f"![{alt}]({Path(kept).as_uri()})")
        elif address:
            lines.append(f"[{alt}]({address})")
        else:
            lines.append(f"image: {alt}")

    external = embed.get("external")
    if external:
        title = _one_line(external.get("title") or external.get("uri")) or "link"
        lines.append(f"[{title}]({external.get('uri', '')})")

    quoted = embed.get("record")
    if quoted and quoted.get("$type", "").endswith("recordWithMedia#view"):
        quoted = (quoted.get("record") or {}).get("record")
    if quoted and "value" in quoted:
        author = (quoted.get("author") or {}).get("handle", "someone")
        body = _one_line(resolve_links(quoted.get("value") or {}))
        if body:
            lines.append(f"> quoting {author}: {body}")
    return lines


def block_id(node):
    """The block identifier an owner's post carries: its record key, which is
    the last segment of its address and never changes, in the letters, digits
    and dashes a block identifier may hold."""
    key = (node.uri or "").rstrip("/").rsplit("/", 1)[-1]
    key = re.sub(r"[^A-Za-z0-9-]", "-", key).strip("-")
    return f"bsky-{key}" if key else None


def _post_lines(node):
    """A post's own words plus whatever it carried, as separate lines.

    The owner's post is one line, a quote ending in its block identifier, so
    the whole post is the one bullet an embed pulls; its own line breaks are
    kept as breaks inside it.
    """
    if node.kind != "post":
        return [UNAVAILABLE_LINE]
    text = resolve_links(node.record.get("record") or {}).strip()
    lines = [line for line in text.split("\n") if line.strip()] or ["*[no text]*"]
    if node.mine:
        ident = block_id(node)
        quote = "> " + "<br>".join(lines)
        lines = [f"{quote} ^{ident}" if ident else quote]
    return lines + describe_embed(node.record)


def render_outline(node, depth=0, lines=None, last_author=None):
    """A conversation as nested bullets: a handle, then what that person said.

    A run of posts by one person sits under one handle bullet rather than
    repeating it, which is what makes a long back-and-forth readable.
    """
    lines = [] if lines is None else lines
    indent = "\t" * depth
    author = node.author or "unknown"
    if author != last_author:
        lines.append(f"{indent}- {author}")
        depth += 1
        indent = "\t" * depth
    for line in _post_lines(node):
        lines.append(f"{indent}- {line}")
    for child in node.children:
        render_outline(child, depth + 1, lines, last_author=author)
    return lines


def render_solo(node):
    """A post with no conversation under it, as spaced prose.

    The owner's post is one quote, its paragraphs kept apart inside it, with
    the block identifier on its own line after it, which is where a quote's
    identifier goes.
    """
    blocks = []
    text = resolve_links(node.record.get("record") or {}).strip()
    paragraphs = [p for p in text.split("\n") if p.strip()]
    if node.mine and paragraphs:
        blocks.append("\n>\n".join(f"> {p}" for p in paragraphs))
        ident = block_id(node)
        if ident:
            blocks.append(f"^{ident}")
    else:
        blocks.extend(paragraphs)
    blocks.extend(describe_embed(node.record))
    return blocks


def render_section(node):
    """One conversation, headed by whoever started it.

    The heading is a handle, spelled as its owner spells it. It is never a
    topic, and never rewritten into Title Case: the notebook's own rule already
    leaves a name as its owner writes it.
    """
    heading = f"## {_opening_author(node)}"
    if not node.children and node.kind == "post":
        return [heading, ""] + _spaced(render_solo(node))
    return [heading, ""] + render_outline(node)


def _opening_author(node):
    """Whoever started the conversation.

    Where that post has been deleted the tree still opens on a placeholder, so
    the heading falls to the first person in it who can still be named, and the
    lost post shows as a placeholder in the body.
    """
    for candidate in node.walk():
        if candidate.author:
            return candidate.author
    return "unknown"


def _spaced(blocks):
    out = []
    for block in blocks:
        out.append(block)
        out.append("")
    return out[:-1] if out else out


def render_page(day, sections, journal_link=None, created=None):
    """The whole page for one day, frontmatter and all."""
    title = day.strftime("Bluesky, %A, %B %d, %Y")
    lines = [
        "---",
        "aliases:",
        f"  - {title}",
        "tags:",
        "  - bluesky/daily",
        f"created: {(created or day).strftime('%Y-%m-%d %H:%M')}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    if journal_link:
        lines += [journal_link, ""]
    for section in sections:
        lines += section + [""]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"
