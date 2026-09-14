"""Turn a day's pruned conversations into one Markdown page.

A solo post is prose, the way the notebook's other prose notes are spaced. A
conversation is a bulleted outline that follows its own branching rather than a
flat chronology, so a reader can see who answered whom.
"""

from __future__ import annotations

ME_MARK = "**"
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


def describe_embed(post):
    """The lines an attachment adds under a post, or none where it adds nothing.

    No media is downloaded. An image contributes the words its author wrote
    about it and an address; a quoted post contributes its text.
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
        lines.append(f"[{alt}]({address})" if address else f"image: {alt}")

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


def _post_lines(node):
    """A post's own words plus whatever it carried, as separate lines."""
    if node.kind != "post":
        return [UNAVAILABLE_LINE]
    text = resolve_links(node.record.get("record") or {}).strip()
    lines = [line for line in text.split("\n") if line.strip()] or ["*[no text]*"]
    if node.mine:
        lines = [f"{ME_MARK}{line}{ME_MARK}" for line in lines]
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
    """A post with no conversation under it, as spaced prose."""
    blocks = []
    text = resolve_links(node.record.get("record") or {}).strip()
    for paragraph in [p for p in text.split("\n") if p.strip()]:
        blocks.append(paragraph)
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
