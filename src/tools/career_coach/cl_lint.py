#!/usr/bin/env python3
"""
cl_lint.py : Cover-letter blacklist linter for career_coach.

Scans a draft (.txt or .docx) against the instance's blacklist file (the
user's personal, banned-phrase checklist, kept in their own project — never
in this shared tool) and reports every banned phrase, dash construct, and
period-emphasis run. Run it on the DRAFT TEXT before packing the docx, and
again on the packed docx. This is the mechanism that makes the voice
guardrails actually enforced instead of merely documented.

Usage:
    python3 cl_lint.py <draft.txt | letter.docx> --blacklist PATH
    (or place a file named cl_blacklist.txt next to this script / in the CWD
    to skip passing --blacklist explicitly)

Exit codes:
    0  clean (FLAG warnings may still print)
    1  one or more HARD / DASH / PERIOD_EMPHASIS violations (do not deliver)
    2  usage / file error
"""

import sys
import re
import os
import zipfile


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


def check_dash(text):
    hits = []
    for m in re.finditer(r"\u2014|\u2013|\u2012|--| - ", text):
        hits.append((line_of(text, m.start()), m.group().strip() or "space-hyphen-space"))
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
    if not args:
        print("usage: python3 cl_lint.py <draft.txt|letter.docx> [--blacklist PATH]")
        return 2
    draft = args[0]
    if bl_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        for cand in (os.path.join(here, "cl_blacklist.txt"),
                     "cl_blacklist.txt"):
            if os.path.exists(cand):
                bl_path = cand
                break
    if not bl_path or not os.path.exists(bl_path):
        print("error: blacklist not found; pass --blacklist PATH")
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

    dash_hits = check_dash(text)
    pe_hits = check_period_emphasis(text)

    print(f"== cl_lint: {os.path.basename(draft)} ==")

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
