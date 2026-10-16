#!/usr/bin/env python3
"""sound_check.py — how near a coined name, or a sample of a language, sounds
to every constructed language and every main character's name already given.

A language's sound is measured from the words its notes list: the share of
words ending in a vowel, the share holding a consonant cluster or closing on a
consonant, its commonest endings, its initials and its consonants, and its
letter patterns — how often each letter follows each pair. A name is scored
against each other language by how often that language's letter patterns
would claim it against its own language's alone; a sample
of words is scored against each language by how alike the two profiles are;
the names a sample coins are each checked as names.
Two main characters' names are too near when they share both their first
letter and their last; `--character` makes that part of a name's verdict.

Where the notes are is config, `agents.writers_room.sound_check`:

    {"languages": {"<language>": ["<note>", ...], ...},
     "outlines_dir": "<folder of *_outline.md notes>"}

A note's words are the first cells of its tables whose first heading is
`Form`, `Root`, `Name` or the language's own name; a cell's first italic word
where it has one. A form opening with a hyphen is an affix and is skipped.
Main characters are the named entries under `POV` and `Secondary` in every
outline's Characters section.

CLI
---
    python3 sound_check.py name <name> [--language <its language>] [--character] [--json]
    python3 sound_check.py words <word> [<word> ...] [--language <its language>] [--json]
    python3 sound_check.py languages [--json]

Each command exits 1 when anything is too near, and 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))

VOWELS = set("aeiouɛɔəæøɪʊ")
# Two letters spelling one consonant in the languages this reads, so that a
# digraph is never counted as a cluster.
DIGRAPHS = ("ng", "ny", "ts", "tz", "kh", "gh", "sh", "ch", "th", "zh", "dh",
            "ph", "bh", "lh", "rh", "hl", "kw", "qw", "gw")
WORD_HEADINGS = {"form", "root", "name"}

# A name is too near another language when, set against its own language
# alone, that language's letter patterns would claim it at least this often.
# Calibrated on the first notebook it read: a name its author heard as
# another language's was claimed by that language about a third of the time,
# and names he heard as their own language's almost never.
NAME_TOO_NEAR = 0.25
# A sample of words is too near a language whose profile is this alike. The
# languages in the notes when the check was built all scored under it, the
# nearest pairs about 0.69.
LANGUAGE_TOO_NEAR = 0.7
# A language needs this many words for its letter patterns to be read.
MIN_WORDS = 10
SMOOTHING = 0.5


def fold(word: str) -> str:
    """Lowercase, accents dropped, letters and the ejective mark kept."""
    decomposed = unicodedata.normalize("NFD", word.lower())
    return "".join(c for c in decomposed
                   if c.isalpha() and not unicodedata.combining(c) or c == "'")


def segments(word: str) -> list[str]:
    """The word cut into sounds: a digraph, a doubled letter or a letter with
    its ejective mark is one sound."""
    out, i = [], 0
    while i < len(word):
        two = word[i:i + 2]
        if two in DIGRAPHS or (len(two) == 2 and two[0] == two[1]):
            seg, i = two, i + 2
        else:
            seg, i = word[i], i + 1
        if i < len(word) and word[i] == "'":
            seg, i = seg + "'", i + 1
        if seg == "'":
            continue
        out.append(seg)
    return out


def is_vowel(seg: str) -> bool:
    return seg[0] in VOWELS


def features(word: str) -> dict | None:
    w = fold(word)
    segs = segments(w)
    if len(segs) < 2:
        return None
    cons = [s for s in segs if not is_vowel(s)]
    cluster = any(not is_vowel(a) and not is_vowel(b)
                  for a, b in zip(segs, segs[1:]))
    return {"word": word, "vowel_final": is_vowel(segs[-1]),
            "closed": cluster or not is_vowel(segs[-1]),
            "ending": w[-2:], "initial": segs[0], "consonants": cons}


def profile(words: list[str]) -> dict:
    feats = [f for f in (features(w) for w in words) if f]
    n = len(feats) or 1
    cons = Counter(c for f in feats for c in f["consonants"])
    return {"count": len(feats),
            "vowel_final": sum(f["vowel_final"] for f in feats) / n,
            "closed": sum(f["closed"] for f in feats) / n,
            "endings": Counter(f["ending"] for f in feats),
            "initials": Counter(f["initial"] for f in feats),
            "consonants": cons}


def _trigrams(word: str) -> list[str]:
    w = "^^" + fold(word) + "$"
    return [w[i:i + 3] for i in range(len(w) - 2)]


class Patterns:
    """Each language's letter patterns: how often each letter follows each
    pair of letters, the word's edges included."""

    def __init__(self, langs: dict[str, list[str]]):
        self.models = {}
        letters = {"$"}
        for lang, words in langs.items():
            if len(words) < MIN_WORDS:
                continue
            grams = [g for w in words for g in _trigrams(w)]
            self.models[lang] = (Counter(grams), Counter(g[:2] for g in grams))
            letters |= {c for w in words for c in fold(w)}
        self.size = len(letters)

    def log_prob(self, word: str, lang: str) -> float:
        tri, bi = self.models[lang]
        return sum(math.log((tri[g] + SMOOTHING) /
                            (bi[g[:2]] + SMOOTHING * self.size))
                   for g in _trigrams(word))

    def contest(self, word: str, home: str, other: str) -> float:
        """How often `other` would claim the word against `home` alone."""
        diff = self.log_prob(word, home) - self.log_prob(word, other)
        return round(1 / (1 + math.exp(max(-50, min(50, diff)))), 2)

    def likeliest(self, word: str) -> str:
        return max(self.models, key=lambda lang: self.log_prob(word, lang))


def _overlap(a: Counter, b: Counter) -> float:
    ta, tb = sum(a.values()), sum(b.values())
    if not ta or not tb:
        return 0.0
    return sum(min(a[k] / ta, b[k] / tb) for k in set(a) | set(b))


def language_similarity(p: dict, q: dict) -> float:
    """How alike two sound profiles are, 0 to 1."""
    parts = [1 - abs(p["vowel_final"] - q["vowel_final"]),
             1 - abs(p["closed"] - q["closed"]),
             _overlap(p["endings"], q["endings"]),
             _overlap(p["consonants"], q["consonants"])]
    return round(sum(parts) / len(parts), 2)


def describe(prof: dict) -> dict:
    return {"words": prof["count"],
            "vowel_final": round(prof["vowel_final"], 2),
            "cluster_or_closing": round(prof["closed"], 2),
            "endings": [e for e, _ in prof["endings"].most_common(5)],
            "initials": [e for e, _ in prof["initials"].most_common(5)],
            "consonants": [e for e, _ in prof["consonants"].most_common(6)]}


# --- reading the notes -------------------------------------------------------

ITALIC = re.compile(r"\*([^*]+)\*")


def words_in_note(text: str, language: str) -> list[str]:
    own = fold(language)
    lines = text.splitlines()
    words, take = [], False
    for i, line in enumerate(lines):
        if not line.startswith("|"):
            take = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if re.match(r"^-+$", cells[0] or "-") and i:
            continue
        prev = lines[i - 1] if i else ""
        if not prev.startswith("|"):
            take = cells[0].lower() in WORD_HEADINGS or fold(cells[0]) == own
            continue
        if not take:
            continue
        m = ITALIC.search(cells[0])
        form = (m.group(1) if m else cells[0]).strip()
        form = form.split(",")[0].strip()
        if not form or form.startswith("-"):
            continue
        for part in form.split():
            part = part.rstrip("-")
            if part and not part.startswith("-"):
                words.append(part)
    return words


def _settings() -> dict:
    import read_config
    return read_config.get("agents.writers_room.sound_check", None) or {}


def _resolve(path: str) -> Path:
    import data_paths
    return data_paths.resolve(path)


def load_languages() -> dict[str, list[str]]:
    langs = {}
    for name, notes in (_settings().get("languages") or {}).items():
        words = []
        for note in notes:
            p = _resolve(note)
            if p.exists():
                words += words_in_note(p.read_text(encoding="utf-8"), name)
        langs[name] = words
    return langs


WIKILINK = re.compile(r"\[\[[^|\]]*\|([^\]]+)\]\]|\[\[([^\]]+)\]\]")


def main_characters() -> list[str]:
    folder = _settings().get("outlines_dir")
    if not folder:
        return []
    names = []
    for note in sorted(_resolve(folder).glob("*_outline.md")):
        heading = None
        in_characters = False
        for line in note.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                in_characters = line.strip() == "## Characters"
                continue
            if not in_characters:
                continue
            if line.startswith("- "):
                heading = line[2:].strip()
                continue
            if heading in ("POV", "Secondary") and line.startswith("\t- ") \
                    and not line.startswith("\t\t"):
                text = WIKILINK.sub(lambda m: m.group(1) or m.group(2), line[3:])
                words = text.split(",")[0].split()
                if not words or not words[0][0].isupper() \
                        or words[0] in ("The", "A", "An") \
                        or words[0].endswith("'s") \
                        or len(words) > 1 and words[1][0].islower() \
                        and words[1] != "the":
                    continue
                names.append(words[0])
    return sorted(set(names))


def characters_too_near(name: str, others: list[str]) -> list[str]:
    f = fold(name)
    return [o for o in others if fold(o) != f and fold(o)[:1] == f[:1]
            and fold(o)[-1:] == f[-1:]]


# --- commands ----------------------------------------------------------------

def check_name(name: str, home: str | None, character: bool = False) -> dict:
    langs = load_languages()
    patterns = Patterns(langs)
    home = home if home in patterns.models else patterns.likeliest(name)
    scores = {lang: patterns.contest(name, home, lang)
              for lang in patterns.models if lang != home}
    near = [lang for lang, sc in scores.items() if sc >= NAME_TOO_NEAR]
    chars = characters_too_near(name, main_characters())
    f = features(name) or {}
    shape = {k: f[k] for k in ("vowel_final", "closed", "ending", "initial")
             if k in f}
    return {"name": name, "language": home, "shape": shape, "scores": scores,
            "too_near_languages": near, "too_near_characters": chars,
            "character": character,
            "too_near": bool(near or character and chars)}


def check_words(words: list[str], home: str | None) -> dict:
    langs = load_languages()
    sample = profile(words)
    scores = {lang: language_similarity(sample, profile(ws))
              for lang, ws in langs.items() if ws and lang != home}
    near = [lang for lang, sc in scores.items() if sc >= LANGUAGE_TOO_NEAR]
    return {"sample": describe(sample), "language": home, "scores": scores,
            "too_near_languages": near, "too_near": bool(near)}


def check_languages() -> dict:
    langs = {k: profile(v) for k, v in load_languages().items() if v}
    pairs = []
    names = sorted(langs)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            s = language_similarity(langs[a], langs[b])
            pairs.append({"pair": [a, b], "similarity": s,
                          "too_near": s >= LANGUAGE_TOO_NEAR})
    return {"profiles": {k: describe(v) for k, v in langs.items()},
            "pairs": sorted(pairs, key=lambda p: -p["similarity"]),
            "too_near": any(p["too_near"] for p in pairs)}


def _print(result: dict) -> None:
    if "pairs" in result:
        for k, d in result["profiles"].items():
            print(f"{k}: {d}")
        for p in result["pairs"]:
            mark = "TOO NEAR" if p["too_near"] else "apart   "
            print(f"{mark} {p['similarity']:.2f}  {p['pair'][0]} / {p['pair'][1]}")
        return
    subject = result.get("name") or "sample"
    print(f"{subject}, read as {result['language'] or 'no one language'}")
    if "sample" in result:
        print(f"  profile: {result['sample']}")
    if result.get("shape"):
        print(f"  shape: {result['shape']}")
    for lang, sc in sorted(result["scores"].items(), key=lambda kv: -kv[1]):
        mark = "TOO NEAR" if lang in result["too_near_languages"] else "        "
        print(f"{mark} {sc:.2f}  {lang}")
    for c in result.get("too_near_characters", []):
        mark = "TOO NEAR" if result.get("character") else "shares  "
        print(f"{mark} main character {c}: same first and last letter")
    print(f"{subject}: {'too near' if result['too_near'] else 'apart'}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("name")
    n.add_argument("name")
    n.add_argument("--language")
    n.add_argument("--character", action="store_true",
                   help="the name is a main character's")
    n.add_argument("--json", action="store_true")
    w = sub.add_parser("words")
    w.add_argument("words", nargs="+")
    w.add_argument("--language")
    w.add_argument("--json", action="store_true")
    lg = sub.add_parser("languages")
    lg.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "name":
        result = check_name(args.name, args.language, args.character)
    elif args.cmd == "words":
        result = check_words(args.words, args.language)
    else:
        result = check_languages()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, default=list))
    else:
        _print(result)
    return 1 if result["too_near"] else 0


if __name__ == "__main__":
    sys.exit(main())
