#!/usr/bin/env python3
"""name_variants.py — one coined name spelled two ways, across a body of notes.

A wiki grows past what one session can hold, and the disagreements that follow
are rarely arguments: they are the same name written differently in two notes
written months apart. That kind a machine can find, and finding it does not
depend on being allowed to fix it.

What it finds is names, and only names. A claim two notes make differently — a
date, a count, a rule stated twice — is a reading job, and the procedure that
does that reading is `src/skills/checking-a-wiki-for-disagreements/SKILL.md`.

    python3 src/tools/wiki_tools/name_variants.py <folder> [--json] [--min 2]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# A coined name carries a capital that ordinary prose would not: inside the
# word, or after a hyphen. An all-capital token is an abbreviation rather than
# a name — CV, CVC and their kin are a phonology note's own shorthand — so a
# name is required to hold a lowercase letter as well.
COINED = re.compile(
    r"\b(?:[a-z]{1,5}-[A-Z][A-Za-z]+(?:-[A-Za-z]+)*"     # so-Varuni
    r"|[A-Z][a-z]+-[A-Z][A-Za-z]+"                        # Tel-Varuni
    r"|[A-Z][a-z]*[A-Z][A-Za-z]*)\b")                     # TelVarun

# Markdown furniture a name never hides behind: a link target, a heading mark,
# a frontmatter key. Stripped before reading, so `[[so-Varuni]]` and the word
# itself are one name rather than two.
STRIP = re.compile(r"[\[\]#*`>|]")


def names_in(text: str) -> list[str]:
    return [name for name in COINED.findall(STRIP.sub(" ", text))
            if any(letter.islower() for letter in name.replace("-", ""))]


def _variant_of(one: str, other: str) -> bool:
    """Whether two spellings are the same name written differently.

    One being the other plus a short ending is the commonest case in a
    constructed language, where a suffix marks a form rather than a new word;
    a single letter's difference in a long name is the other, and is a
    typo.
    """
    short, long = sorted((one.lower(), other.lower()), key=len)
    if short == long:
        return False
    if long.startswith(short) and len(long) - len(short) <= 3:
        return True
    if len(short) >= 6 and abs(len(long) - len(short)) <= 1:
        return _one_edit_apart(short, long)
    return False


def _one_edit_apart(short: str, long: str) -> bool:
    """One insertion, deletion or substitution between two words."""
    if len(short) == len(long):
        return sum(a != b for a, b in zip(short, long)) == 1
    for cut in range(len(long)):
        if long[:cut] + long[cut + 1:] == short:
            return True
    return False


def group(counts: dict) -> list[list[str]]:
    """Spellings gathered into the names they are spellings of."""
    spellings = sorted(counts, key=lambda name: (-counts[name], name))
    groups: list[list[str]] = []
    for name in spellings:
        for held in groups:
            if any(_variant_of(name, other) for other in held):
                held.append(name)
                break
        else:
            groups.append([name])
    return [held for held in groups if len(held) > 1]


def _archive() -> Path | None:
    """The notebook's archive folder, whose content is superseded and is never
    read (`src/skills/notebook-proposal/SKILL.md`), or None where config sets
    none."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))
        import data_paths
        import read_config
        declared = read_config.get("markdown_notebook.archive_dir", None)
        return data_paths.resolve(declared).resolve() if declared else None
    except (Exception, SystemExit):
        return None


def read(folder: Path, min_uses: int = 2) -> list[dict]:
    """Every name this folder spells more than one way, commonest first. The
    notebook's archive is skipped wherever the folder contains it."""
    counts: dict[str, int] = defaultdict(int)
    where: dict[str, set] = defaultdict(set)
    archive = _archive()
    for note in sorted(folder.rglob("*.md")):
        if archive is not None and archive in note.resolve().parents:
            continue
        try:
            text = note.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name in names_in(text):
            counts[name] += 1
            where[name].add(str(note.relative_to(folder)))
    found = []
    for held in group(counts):
        if sum(counts[name] for name in held) < min_uses:
            continue
        # A spelling used once in one note beside a name used often is a typo
        # rather than a second usage, and both are worth the same line.
        found.append({
            "name": held[0],
            "spellings": [
                {"spelling": name, "uses": counts[name],
                 "notes": sorted(where[name])}
                for name in held
            ],
        })
    found.sort(key=lambda item: -sum(s["uses"] for s in item["spellings"]))
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", help="the folder of notes to read")
    parser.add_argument("--json", action="store_true",
                        help="print the findings for a caller rather than a person")
    parser.add_argument("--min", type=int, default=2,
                        help="ignore a name used fewer times than this in all")
    args = parser.parse_args(argv)

    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        sys.exit(f"name_variants: {folder} is not a folder")
    found = read(folder, min_uses=args.min)
    if args.json:
        print(json.dumps(found, indent=2))
        return 0
    if not found:
        print("no name is spelled two ways here.")
        return 0
    print(f"{len(found)} name(s) spelled more than one way:\n")
    for item in found:
        print(f"  {item['name']}")
        for spelling in item["spellings"]:
            notes = ", ".join(spelling["notes"][:4])
            more = "" if len(spelling["notes"]) <= 4 else \
                f" and {len(spelling['notes']) - 4} more"
            print(f"    {spelling['spelling']:28s} {spelling['uses']:4d} use(s)"
                  f"  {notes}{more}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
