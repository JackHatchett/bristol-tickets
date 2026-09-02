#!/usr/bin/env python3
"""
voice_lint.py : the voice blacklist linter for career_coach.

Scans a draft (.txt or .docx) against the instance's blacklist file (the
user's personal, banned-phrase checklist, kept in their own project — never
in this shared tool) and reports every banned phrase, dash construct, and
period-emphasis run. It governs everything written in the user's own voice —
a cover letter, a resume, a profile section, a post — and not only a letter.
Run it on the DRAFT TEXT before packing a docx, and again on the packed docx.
This is the mechanism that makes the voice guardrails actually enforced
instead of merely documented.

Usage:
    python3 voice_lint.py <draft.txt | draft.docx> [--fiction] [--blacklist PATH]

The blacklist is found in the instance's own career data root — the
`agents.career_coach.key_data_paths` this installation declares, then
`foundation/*_Voice_Blacklist.txt`. `--blacklist` overrides that for a one-off
file.

The two coded patterns are scoped the way the voice profile scopes them, and
--fiction is the switch. The banned phrases bind everything the user writes as
himself; the dash constraint is business writing's, and period-separated
emphasis is barred in non-fiction and is a device in fiction.

Exit codes:
    0  clean (FLAG warnings may still print)
    1  one or more HARD / DASH / PERIOD_EMPHASIS violations (do not deliver)
    2  usage / file error
"""

import sys
import re
import os
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))
import data_paths  # noqa: E402  (the shared declared-path resolver)

BLACKLIST_GLOB = "foundation/*_Voice_Blacklist.txt"


def discover_blacklist():
    """The instance's blacklist, resolved from config rather than from the
    shared tool's own folder.

    The list is the user's personal content, so it lives in their data root and
    never in tracked `/src`. Returns the path, or a message saying where it
    looked.
    """
    roots = data_paths.agent_data_paths("career_coach")
    if not roots:
        return None, ("config declares no agents.career_coach.key_data_paths, "
                      "so there is no career data root to search")
    hits = [p for root in roots for p in sorted(root.glob(BLACKLIST_GLOB))]
    if len(hits) == 1:
        return hits[0], None
    where = ", ".join(f"{root}/{BLACKLIST_GLOB}" for root in roots)
    if not hits:
        return None, f"no blacklist at {where}"
    return None, ("more than one blacklist — pass --blacklist to choose: "
                  + ", ".join(str(p) for p in hits))


def load_blacklist(path):
    hard, flag = [], []
    section = None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if stripped in ("HARD", "FLAG", "PATTERNS"):
                section = stripped
                continue
            if not stripped or stripped.startswith("#") or stripped.startswith("="):
                continue
            if section in ("HARD", "FLAG"):
                phrase = line.split("  #", 1)[0].strip().lower()
                if phrase:
                    (hard if section == "HARD" else flag).append(phrase)
    return hard, flag


def extract_text(path):
    if path.lower().endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        # paragraph and break tags become newlines so period-emphasis is detectable
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", xml)
        text = (text.replace("&#x2018;", "\u2018").replace("&#x2019;", "\u2019")
                    .replace("&#x201C;", "\u201c").replace("&#x201D;", "\u201d")
                    .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
        return text
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def find_phrase(text_lower, phrase):
    # word-ish boundary match so "as a" does not fire inside "phase" etc.
    pat = re.escape(phrase)
    if phrase[0].isalnum():
        pat = r"(?<![a-z0-9])" + pat
    if phrase[-1].isalnum():
        pat = pat + r"(?![a-z0-9])"
    return [m.start() for m in re.finditer(pat, text_lower)]


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


BULLET_MARKER = re.compile("^[ \t]*(--|[-*\u2022])[ \t]+")
DASH = re.compile("\u2014|\u2013|\u2012|--| - ")


def check_dash(text):
    """Dash constructs, ignoring a bullet marker at the head of a line.

    A resume writes its bullets as "-- Designed and built ...", which is markup
    rather than a clause break. The marker is skipped and a dash later in the
    same line is still reported."""
    hits = []
    offset = 0
    for line in text.split("\n"):
        marker = BULLET_MARKER.match(line)
        start = marker.end() if marker else 0
        for m in DASH.finditer(line[start:]):
            hits.append((line_of(text, offset + start + m.start()),
                         m.group().strip() or "space-hyphen-space"))
        offset += len(line) + 1
    return hits


def check_period_emphasis(text):
    # flag 3+ consecutive sentences of <= 3 words
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    hits, run, start = [], 0, None
    for s in sentences:
        words = re.findall(r"[A-Za-z0-9']+", s)
        if 0 < len(words) <= 3:
            run += 1
            if start is None:
                start = s
        else:
            if run >= 3:
                hits.append(start)
            run, start = 0, None
    if run >= 3:
        hits.append(start)
    return hits


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    bl_path = None
    if "--blacklist" in sys.argv:
        bl_path = sys.argv[sys.argv.index("--blacklist") + 1]
        args = [a for a in args if a != bl_path]
    fiction = "--fiction" in sys.argv
    if not args:
        print("usage: python3 voice_lint.py <draft.txt|draft.docx> [--fiction] "
              "[--blacklist PATH]\n"
              "       (the blacklist is found in the instance's career data root "
              "when --blacklist is omitted)")
        return 2
    draft = args[0]
    if bl_path is None:
        found, why = discover_blacklist()
        if found is None:
            print(f"error: {why}")
            return 2
        bl_path = str(found)
    if not os.path.exists(bl_path):
        print(f"error: blacklist not found: {bl_path}")
        return 2
    if not os.path.exists(draft):
        print(f"error: draft not found: {draft}")
        return 2

    hard, flag = load_blacklist(bl_path)
    text = extract_text(draft)
    low = text.lower()

    hard_hits, flag_hits = [], []
    for p in hard:
        for idx in find_phrase(low, p):
            hard_hits.append((line_of(text, idx), p))
    for p in flag:
        for idx in find_phrase(low, p):
            flag_hits.append((line_of(text, idx), p))

    # The phrase lists bind every form. The two coded patterns are business
    # writing's and non-fiction's respectively, so fiction is scanned for banned
    # phrases alone.
    dash_hits = [] if fiction else check_dash(text)
    pe_hits = [] if fiction else check_period_emphasis(text)

    print(f"== voice_lint: {os.path.basename(draft)}"
          f"{' (fiction)' if fiction else ''} ==")

    blocking = bool(hard_hits or dash_hits or pe_hits)

    if hard_hits:
        print("\nHARD violations (do not deliver):")
        for ln, p in sorted(hard_hits):
            print(f"  line {ln}: \"{p}\"")
    if dash_hits:
        print("\nDASH violations (zero-dash constraint):")
        for ln, d in dash_hits:
            print(f"  line {ln}: {d}")
    if pe_hits:
        print("\nPERIOD-EMPHASIS runs (rewrite as flowing prose):")
        for s in pe_hits:
            print(f"  near: \"{s}\"")
    if flag_hits:
        print("\nFLAG warnings (review; rewrite unless earned):")
        for ln, p in sorted(set(flag_hits)):
            print(f"  line {ln}: \"{p}\"")

    if not blocking and not flag_hits:
        print("clean.")
    print()
    if blocking:
        print("RESULT: BLOCKED. Fix HARD/DASH/PERIOD items before delivering.")
        return 1
    print("RESULT: PASS" + (" (review FLAG warnings)" if flag_hits else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
