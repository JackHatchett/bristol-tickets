#!/usr/bin/env python3
"""sound_check.py — how near a coined name, or a sample of a language, sounds
to every constructed language and every main character's name already given.

A language's sound is measured from the words its notes list: the share of
words ending in a vowel (a vowel and a closing y or w is a vowel ending), the
share containing a consonant cluster or closing on a consonant, its commonest
endings, its initials and its consonants, how many syllables its words run to,
its stock of syllables, and its letter patterns — how often each letter follows
each pair. Letter patterns are read as a reader sees the page: a letter carrying
an accent or a tone mark is a letter of its own, and each word of a name is read
between its own edges, so a name of short words reads unlike one long word. A
profile also prints the consonants that close a word, the letters
frequent in it and rare in the others, and a sample of its words. A name is scored
against each other language by how often that language's letter patterns
would claim it against its own language's alone; a sample
of words is scored against each language by how alike the two profiles are,
the mean of six parts — vowel-final share, closed share, endings, consonants,
word lengths and syllable stock;
the names a sample coins are each checked as names. A batch of new names is
read against the language's own names of one kind — the rows of its tables
headed `Form` whose `Kind` the command gives, or every capitalised form — for
the openings, endings and syllables that kind already over-uses, the rarer
syllables a new name shares with one or two names (a shared element), the
class prefixes and suffixes a name opens or ends as, and the comic forms
listed under the key's `comic`; each sharing name is ranked by how many notes
of `notes_dir` (else the folder above `outlines_dir`) mention it. A name given
as `Formal/Familiar` has its familiar form read against the familiar forms the
kind already has — the shorter forms a row gives beside its name — and the
batch's other familiars, for the same shape: syllable count, a cluster of
consonant letters, last vowel and closing consonant. The batch's spread of
syllable counts, formal and familiar, is printed, and read against the shares
`--formal-shares` and `--familiar-shares` give, such as `2=1/6 3=2/5`: a
count containing more names than its share of the batch rounds up to is flagged.
Two main characters' names are too near when they share both their first
letter and their last; `--character` makes that part of a name's verdict.

Where the notes are is config, `agents.<agent>.sound_check`, the
key of whichever agent has it:

    {"languages": {"<language>": ["<note>", ...], ...},
     "outlines_dir": "<folder of *_outline.md notes>"}

A note's words are the first cells of its tables whose first heading is
`Form`, `Root`, `Name` or the language's own name; a cell's first italic word
where it has one. A form opening with a hyphen is an affix and is skipped.
Main characters are the named entries under `POV` and `Secondary` in every
outline's Characters section.

CLI
---
    python3 sound_check.py name <name> [--language <its language, accents optional>] [--home-words <word> ...] [--character] [--json]
    python3 sound_check.py words <word> [<word> ...] [--language <its language>] [--json]
    python3 sound_check.py batch <name>[/<familiar>] ... --language <their language> [--kind <kind> ...]
        [--formal-shares <syllables>=<share> ...] [--familiar-shares <syllables>=<share> ...] [--json]
    python3 sound_check.py languages [--json]

Each command exits 1 when anything is too near, and 0 otherwise.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))

VOWELS = set("aeiouɛɔəæøɪʊ")
# A glide after a vowel and before no vowel closes a diphthong rather than a
# syllable: a word in -ay or -aw ends in a vowel sound.
GLIDES = set("yw")
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
# A sample of words is too near a language whose profile is this alike. Set
# just above the pairs the author has heard as distinct, the nearest of them
# 0.60 and a kin pair at 0.61.
LANGUAGE_TOO_NEAR = 0.65
# A language needs this many words for its letter patterns to be read.
MIN_WORDS = 10
# Words of this many syllables or more are counted together.
LONGEST = 4
# In a batch check, a form is over-used by a language's names of one kind when
# at least this many of them, and this share, carry it.
OVERUSE_MIN = 3
OVERUSE_SHARE = 0.05
# A run of at least ELEMENT_LETTERS letters shared with this few names of the
# kind is read as a shared element, such as one root in two founders' names.
ELEMENT_MAX = 2
ELEMENT_LETTERS = 4
SMOOTHING = 0.5


def fold(word: str) -> str:
    """Lowercase, accents dropped, letters and the ejective mark kept."""
    decomposed = unicodedata.normalize("NFD", word.lower())
    return "".join(c for c in decomposed
                   if c.isalpha() and not unicodedata.combining(c) or c == "'")


def spelled(name: str) -> list[str]:
    """The words of a name as a reader sees them: lowercase, each accented
    letter its own letter, cut at every space or hyphen."""
    composed = unicodedata.normalize("NFC", name.lower())
    kept = "".join(c if c.isalpha() or unicodedata.combining(c) or c == "'"
                   else " " for c in composed)
    return kept.split()


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


def units(segs: list[str]) -> list[tuple[str, bool]]:
    """Each sound with whether it is a vowel sound, a glide after a vowel and
    before no vowel joined to that vowel."""
    out: list[tuple[str, bool]] = []
    for i, seg in enumerate(segs):
        if (seg in GLIDES and out and out[-1][1]
                and (i + 1 == len(segs) or not is_vowel(segs[i + 1]))):
            out[-1] = (out[-1][0] + seg, True)
        else:
            out.append((seg, is_vowel(seg)))
    return out


def syllables(word: str) -> list[str]:
    """The word cut into syllables: one consonant between two vowels opens the
    second, of two or more the first closes the syllable before, and a doubled
    consonant is split between the two."""
    u = units(segments(fold(word)))
    nuclei = [i for i, (_, v) in enumerate(u) if v]
    if not nuclei:
        return ["".join(seg for seg, _ in u)]
    out, start = [], 0
    for a, b in zip(nuclei, nuclei[1:]):
        between = b - a - 1
        cut = b if between == 0 else b - 1 if between == 1 else a + 2
        syl = "".join(seg for seg, _ in u[start:cut])
        if between == 1 and len(u[b - 1][0]) == 2 \
                and u[b - 1][0][0] == u[b - 1][0][1]:
            syl += u[b - 1][0][0]
        out.append(syl)
        start = cut
    out.append("".join(seg for seg, _ in u[start:]))
    return [x[1:] if i and len(x) > 2 and x[0] == x[1] and not is_vowel(x[0])
            else x for i, x in enumerate(out)]


def features(word: str) -> dict | None:
    w = fold(word)
    segs = segments(w)
    if len(segs) < 2:
        return None
    u = units(segs)
    cons = [seg for seg, v in u if not v]
    cluster = any(not a[1] and not b[1] for a, b in zip(u, u[1:]))
    vowel_final = u[-1][1]
    final = "" if vowel_final else u[-1][0]
    return {"word": word, "vowel_final": vowel_final,
            "closed": cluster or not vowel_final,
            "ending": w[-2:], "initial": segs[0], "consonants": cons,
            "final": final, "syllables": syllables(word)}


def profile(words: list[str]) -> dict:
    feats = [f for f in (features(w) for w in words) if f]
    n = len(feats) or 1
    cons = Counter(c for f in feats for c in f["consonants"])
    return {"count": len(feats),
            "vowel_final": sum(f["vowel_final"] for f in feats) / n,
            "closed": sum(f["closed"] for f in feats) / n,
            "endings": Counter(f["ending"] for f in feats),
            "initials": Counter(f["initial"] for f in feats),
            "consonants": cons,
            "finals": Counter(f["final"] for f in feats if f["final"]),
            "syllables": Counter(x for f in feats for x in f["syllables"]),
            "lengths": Counter(min(len(f["syllables"]), LONGEST)
                               for f in feats),
            "letters": Counter(c for f in feats for c in fold(f["word"])),
            "words": [f["word"] for f in feats]}


def _trigrams(word: str) -> list[str]:
    out = []
    for part in spelled(word):
        w = "^^" + part + "$"
        out += [w[i:i + 3] for i in range(len(w) - 2)]
    return out


class Patterns:
    """Each language's letter patterns: how often each letter follows each
    pair of letters, each word's edges included, accented letters as their own
    letters. Smoothing counts the letters with their accents dropped, the
    alphabet NAME_TOO_NEAR was calibrated on."""

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


def similarity_parts(p: dict, q: dict) -> dict:
    """The six measures two sound profiles are compared on, each 0 to 1."""
    return {"vowel_final": 1 - abs(p["vowel_final"] - q["vowel_final"]),
            "closed": 1 - abs(p["closed"] - q["closed"]),
            "endings": _overlap(p["endings"], q["endings"]),
            "consonants": _overlap(p["consonants"], q["consonants"]),
            "lengths": _overlap(p["lengths"], q["lengths"]),
            "syllables": _overlap(p["syllables"], q["syllables"])}


def language_similarity(p: dict, q: dict) -> float:
    """How alike two sound profiles are, 0 to 1: the mean of their parts."""
    parts = similarity_parts(p, q)
    return round(sum(parts.values()) / len(parts), 2)


def signature_letters(prof: dict, others: list[dict], n: int = 5) -> list[str]:
    """The letters most frequent here against their rate in the others."""
    total = sum(prof["letters"].values()) or 1
    rest = Counter()
    for o in others:
        t = sum(o["letters"].values()) or 1
        for k, v in o["letters"].items():
            rest[k] += v / t / max(len(others), 1)
    lift = {k: (v / total) / (rest[k] + 0.005) for k, v in prof["letters"].items()
            if v / total >= 0.01}
    return [k for k, _ in sorted(lift.items(), key=lambda kv: -kv[1])[:n]]


def describe(prof: dict, others: list[dict] | None = None) -> dict:
    n = sum(prof["lengths"].values()) or 1
    out = {"words": prof["count"],
           "vowel_final": round(prof["vowel_final"], 2),
           "cluster_or_closing": round(prof["closed"], 2),
           "endings": [e for e, _ in prof["endings"].most_common(5)],
           "initials": [e for e, _ in prof["initials"].most_common(5)],
           "consonants": [e for e, _ in prof["consonants"].most_common(6)],
           "final_consonants": sorted(prof["finals"]),
           "syllables_per_word": round(sum(k * v for k, v in prof["lengths"].items()) / n, 2),
           "lengths": {f"{k}{'+' if k == LONGEST else ''}": round(v / n, 2)
                       for k, v in sorted(prof["lengths"].items())},
           "commonest_syllables": [e for e, _ in prof["syllables"].most_common(8)],
           "sample": prof["words"][:: max(1, len(prof["words"]) // 10)][:10]}
    if others is not None:
        out["signature_letters"] = signature_letters(prof, others)
    return out


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


def rows_in_note(text: str) -> list[tuple[str, str, str]]:
    """(form, kind, the row's text) for each row of the note's tables headed `Form` with a
    `Kind` column; affixes keep their hyphens."""
    out, cols = [], None
    for line in text.splitlines():
        if not line.startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cols is None:
            heads = [c.lower() for c in cells]
            cols = (heads.index("kind")
                    if heads and heads[0] == "form" and "kind" in heads else -1)
            continue
        if cols < 0 or re.match(r"^-+$", cells[0] or "-") or len(cells) <= cols:
            continue
        m = ITALIC.search(cells[0])
        form = (m.group(1) if m else cells[0]).split(",")[0].strip()
        if form:
            out.append((form, cells[cols].lower(), line))
    return out


def _settings() -> dict:
    """The `sound_check` key of whichever agent's config entry has one."""
    import read_config
    for entry in (read_config.get("agents", None) or {}).values():
        if isinstance(entry, dict) and entry.get("sound_check"):
            return entry["sound_check"]
    return {}


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


def language_notes(language: str) -> list[str]:
    out = []
    for note in (_settings().get("languages") or {}).get(language, []):
        p = _resolve(note)
        if p.exists():
            out.append(p.read_text(encoding="utf-8"))
    return out


def language_rows(language: str) -> list[tuple[str, str, str]]:
    return [r for text in language_notes(language) for r in rows_in_note(text)]


def plain(text: str) -> str:
    """Lowercase with accents dropped, spacing kept."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def opening(word: str) -> str:
    """The sounds up to and including the first vowel."""
    out = ""
    for seg, v in units(segments(fold(word))):
        out += seg
        if v:
            break
    return out


def notes_dir() -> Path | None:
    """The novel's notes: `notes_dir`, else the folder above `outlines_dir`."""
    st = _settings()
    if st.get("notes_dir"):
        return _resolve(st["notes_dir"])
    if st.get("outlines_dir"):
        return _resolve(st["outlines_dir"]).parent
    return None


def degrees(names: list[str]) -> dict[str, int]:
    """How many notes mention each name: its links in the body of notes."""
    root = notes_dir()
    out = {n: 0 for n in names}
    if not root or not root.exists():
        return out
    pats = {n: re.compile(r"(?<![a-z])" + re.escape(fold(n)) + r"(?![a-z])")
            for n in names}
    for note in root.rglob("*.md"):
        text = plain(note.read_text(encoding="utf-8", errors="ignore"))
        for n, pat in pats.items():
            if pat.search(text):
                out[n] += 1
    return out


def familiar_shape(word: str) -> tuple:
    """What a familiar form's shape is on the page: its syllable count,
    whether two consonant letters stand together, its last vowel and the
    consonant that closes it."""
    w = fold(word)
    u = units(segments(w))
    cluster = any(a not in VOWELS and b not in VOWELS and a != "'" and b != "'"
                  for a, b in zip(w, w[1:]))
    last_vowel = next((seg for seg, v in reversed(u) if v), "")
    final = "" if not u or u[-1][1] else u[-1][0]
    return (len(syllables(word)), cluster, last_vowel, final)


def describe_shape(shape: tuple) -> str:
    n, cluster, vowel, final = shape
    return (f"{n} syllable{'s' if n != 1 else ''}, "
            f"{'a cluster' if cluster else 'no cluster'}, last vowel {vowel}"
            f"{', closed by ' + final if final else ''}")


def parse_shares(items: list[str] | None) -> dict[int, Fraction]:
    out = {}
    for item in items or []:
        k, _, v = item.partition("=")
        out[int(k)] = Fraction(v)
    return out


def spread(names: list[str], shares: dict[int, Fraction]) -> dict:
    """How many of the names run to each syllable count, and the counts
    containing more than their share of the batch rounds up to."""
    counts = Counter(len(syllables(n)) for n in names)
    n = len(names)
    crowded = {}
    if shares:
        for k, c in counts.items():
            allowed = math.ceil(shares.get(k, 0) * n)
            if c > allowed:
                crowded[k] = {"names": c, "allowed": allowed}
    return {"counts": dict(sorted(counts.items())),
            "shares": {k: str(v) for k, v in sorted(shares.items())},
            "crowded": crowded}


def check_batch(new: list[str], language: str, kinds: list[str] | None,
                familiars: dict[str, str] | None = None,
                formal_shares: dict[int, Fraction] | None = None,
                familiar_shares: dict[int, Fraction] | None = None) -> dict:
    """New names against the language's own names of the same kind: the
    openings, endings and syllables the kind already over-uses, the names each
    new one shares a form with, ranked by how linked they are, the affixes a
    name opens or ends as, and the comic forms config lists."""
    rows = language_rows(language)
    kinds = [k.lower() for k in kinds] if kinds else None
    picked = [(f, line) for f, k, line in rows
              if (k in kinds if kinds else f[:1].isupper())
              and not f.startswith("-") and not f.endswith("-")]
    pool = sorted({f for f, _ in picked}, key=fold)
    # A name is also known by the longer or shorter forms its row gives that
    # open as it does: a founder's full name beside a familiar one.
    known = {f: {fold(f)} for f in pool}
    # The shorter of those forms are the kind's familiar forms.
    familiar_pool: dict[str, str] = {}
    for f, line in picked:
        for w in re.findall(r"[A-ZÀ-ÖØ-Þ][^\s|,.;:()*'’]+", line):
            if fold(w)[:2] == fold(f)[:2] and fold(w) != fold(f):
                known[f].add(fold(w))
                if len(fold(w)) < len(fold(f)):
                    familiar_pool.setdefault(w, f)
    italics = [m.group(1).strip() for text in language_notes(language)
               for m in ITALIC.finditer(text)]
    prefixes = {fold(x.rstrip("-")) for x in italics
                if x.endswith("-") and not x.startswith("-")}
    suffixes = {fold(x.lstrip("-")) for x in italics
                if x.startswith("-") and not x.endswith("-")}
    comic = [fold(c) for c in _settings().get("comic") or []]

    def forms(name):
        sy = syllables(name)
        return {"opening": opening(name),
                "ending": sy[-1] if len(sy) > 1 else "",
                "syllables": set(sy)}

    def shared_run(a: str, bs: set[str]) -> str:
        """The longest run of ELEMENT_LETTERS or more letters a shares with
        any of bs."""
        best = ""
        for b in bs:
            for i in range(len(a)):
                for j in range(i + ELEMENT_LETTERS, len(a) + 1):
                    if a[i:j] in b and j - i > len(best):
                        best = a[i:j]
        return best

    pf = {n: forms(n) for n in pool}
    n = len(pool) or 1
    use = {"opening": Counter(f["opening"] for f in pf.values()),
           "ending": Counter(f["ending"] for f in pf.values() if f["ending"]),
           "syllables": Counter(x for f in pf.values() for x in f["syllables"])}
    over = {k: {x: c for x, c in cnt.items()
                if c >= OVERUSE_MIN and c / n >= OVERUSE_SHARE}
            for k, cnt in use.items()}
    report, sharers_all = [], set()
    for name in new:
        f = forms(name)
        shared = []
        others = {p: g for p, g in pf.items() if fold(p) != fold(name)}
        for kind in ("opening", "ending"):
            x = f[kind]
            hits = [p for p, g in others.items() if x and g[kind] == x]
            if hits:
                shared.append({"form": x, "as": kind, "uses": len(hits),
                               "over_used": x in over[kind], "names": hits})
        for x in sorted(f["syllables"] - {f["opening"], f["ending"]}):
            hits = [p for p, g in others.items() if x in g["syllables"]]
            if hits and x in over["syllables"]:
                shared.append({"form": x, "as": "syllable", "uses": len(hits),
                               "over_used": True, "names": hits})
        runs = {}
        for p in others:
            run = shared_run(fold(name), known[p])
            if run:
                runs.setdefault(run, []).append(p)
        for run, hits in sorted(runs.items(), key=lambda kv: -len(kv[0])):
            if len(hits) <= ELEMENT_MAX:
                shared.append({"form": run, "as": "element", "uses": len(hits),
                               "over_used": False, "names": hits})
        for d in shared:
            sharers_all.update(d["names"])
        report.append({"name": name, "shared": shared,
                       "opens_as_prefix": max((p for p in prefixes
                                               if fold(name).startswith(p)
                                               and len(p) >= 3),
                                              key=len, default=None),
                       "ends_as_suffix": max((x for x in suffixes
                                              if fold(name).endswith(x)
                                              and len(x) >= 3),
                                             key=len, default=None),
                       "comic": [c for c in comic if c in fold(name)]})
    familiars = familiars or {}
    new_folded = {fold(x) for x in new}
    existing = {w: f for w, f in familiar_pool.items()
                if fold(f) not in new_folded}
    for r in report:
        fam = familiars.get(r["name"])
        if not fam:
            continue
        shape = familiar_shape(fam)
        echoes = [w for w in existing if fold(w) != fold(fam)
                  and familiar_shape(w) == shape]
        echoes += [familiars[o] for o in new if o != r["name"]
                   and familiars.get(o) and familiar_shape(familiars[o]) == shape]
        r["familiar"] = {"form": fam, "shape": describe_shape(shape),
                         "echoes": echoes}
    deg = degrees(sorted(sharers_all | set(new)))
    for r in report:
        r["degree"] = deg.get(r["name"], 0)
        for d in r["shared"]:
            d["names"] = sorted(d["names"], key=lambda x: -deg.get(x, 0))
            d["degrees"] = {x: deg.get(x, 0) for x in d["names"]}
        r["flag"] = bool(r["comic"] or r["opens_as_prefix"]
                         or any(d["over_used"] for d in r["shared"])
                         or any(d["as"] == "element" for d in r["shared"])
                         or r.get("familiar", {}).get("echoes"))
    shape_spread = {"formal": spread(new, formal_shares or {})}
    fams = [familiars[x] for x in new if familiars.get(x)]
    if fams:
        shape_spread["familiar"] = spread(fams, familiar_shares or {})
    crowded = any(v["crowded"] for v in shape_spread.values())
    return {"language": language, "kinds": kinds, "pool": len(pool),
            "familiar_pool": len(existing),
            "over_used": {k: sorted(v, key=lambda x: -v[x])
                          for k, v in over.items()},
            "names": report, "spread": shape_spread,
            "too_near": any(r["flag"] for r in report) or crowded}


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

def check_name(name: str, home: str | None, character: bool = False,
               home_words: list[str] | None = None) -> dict:
    langs = load_languages()
    if home_words:
        # A language whose sound is being rebuilt is read from its new forms,
        # so the forms its notes still record do not count against it.
        home = home or "sample"
        langs[home] = list(home_words)
    patterns = Patterns(langs)
    home = next((lang for lang in patterns.models
                 if home and fold(lang) == fold(home)), None) \
        or patterns.likeliest(name)
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
    others = {lang: profile(ws) for lang, ws in langs.items()
              if ws and lang != home}
    scores = {lang: language_similarity(sample, prof)
              for lang, prof in others.items()}
    near = [lang for lang, sc in scores.items() if sc >= LANGUAGE_TOO_NEAR]
    return {"sample": describe(sample, list(others.values())),
            "language": home, "scores": scores,
            "too_near_languages": near, "too_near": bool(near)}


def check_languages() -> dict:
    langs = {k: profile(v) for k, v in load_languages().items() if v}
    pairs = []
    names = sorted(langs)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            parts = similarity_parts(langs[a], langs[b])
            s = round(sum(parts.values()) / len(parts), 2)
            pairs.append({"pair": [a, b], "similarity": s,
                          "parts": {k: round(v, 2) for k, v in parts.items()},
                          "too_near": s >= LANGUAGE_TOO_NEAR})
    return {"profiles": {k: describe(v, [langs[o] for o in names if o != k])
                         for k, v in langs.items()},
            "pairs": sorted(pairs, key=lambda p: -p["similarity"]),
            "too_near": any(p["too_near"] for p in pairs)}


def _print_batch(result: dict) -> None:
    print(f"{result['language']}, against its {result['pool']} names"
          f"{' of kind ' + ', '.join(result['kinds']) if result['kinds'] else ''}")
    for k, v in result["over_used"].items():
        print(f"  over-used {k}: {', '.join(v[:12]) or '-'}")
    for r in result["names"]:
        mark = "FLAG    " if r["flag"] else "clear   "
        print(f"{mark}{r['name']} (in {r['degree']} notes)")
        if r["comic"]:
            print(f"    comic: {', '.join(r['comic'])}")
        if r["opens_as_prefix"]:
            print(f"    opens as the prefix {r['opens_as_prefix']}-")
        if r["ends_as_suffix"]:
            print(f"    ends as the suffix -{r['ends_as_suffix']}")
        for d in r["shared"]:
            if not (d["over_used"] or d["as"] == "element"):
                continue
            tag = "over-used" if d["over_used"] else "shared"
            names = ", ".join(f"{x} ({d['degrees'][x]})" for x in d["names"][:8])
            print(f"    {tag} {d['as']} {d['form']} ({d['uses']}): {names}")
        fam = r.get("familiar")
        if fam:
            echo = (f"echoes {', '.join(fam['echoes'])}" if fam["echoes"]
                    else "apart")
            print(f"    familiar {fam['form']} ({fam['shape']}): {echo}")
    if result.get("familiar_pool"):
        print(f"  familiar forms read against: {result['familiar_pool']}")
    for which, sp in result.get("spread", {}).items():
        counts = ", ".join(f"{k} syllables {c}" for k, c in sp["counts"].items())
        line = f"  {which} spread: {counts}"
        if sp["shares"]:
            line += "  (shares " + ", ".join(f"{k}={v}" for k, v in sp["shares"].items()) + ")"
        print(line)
        for k, c in sp["crowded"].items():
            print(f"    CROWDED {k} syllables: {c['names']} names, "
                  f"{c['allowed']} by the shares")
    print(f"batch: {'flagged' if result['too_near'] else 'clear'}")


def _print(result: dict) -> None:
    if "pool" in result:
        _print_batch(result)
        return
    if "pairs" in result:
        for k, d in result["profiles"].items():
            print(f"{k}: {d}")
        for p in result["pairs"]:
            mark = "TOO NEAR" if p["too_near"] else "apart   "
            parts = " ".join(f"{k} {v:.2f}" for k, v in p["parts"].items())
            print(f"{mark} {p['similarity']:.2f}  {p['pair'][0]} / {p['pair'][1]}"
                  f"   ({parts})")
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
    n.add_argument("--home-words", nargs="+", metavar="WORD",
                   help="read the name's own language from these words "
                        "rather than from its notes")
    n.add_argument("--json", action="store_true")
    w = sub.add_parser("words")
    w.add_argument("words", nargs="+")
    w.add_argument("--language")
    w.add_argument("--json", action="store_true")
    b = sub.add_parser("batch")
    b.add_argument("names", nargs="+",
                   help="each name, or Formal/Familiar")
    b.add_argument("--language", required=True)
    b.add_argument("--formal-shares", nargs="+", metavar="N=SHARE",
                   help="the share of formal names of N syllables, as 3=2/5")
    b.add_argument("--familiar-shares", nargs="+", metavar="N=SHARE",
                   help="the share of familiar forms of N syllables")
    b.add_argument("--kind", nargs="+",
                   help="the Kind column values that make the names' category")
    b.add_argument("--json", action="store_true")
    lg = sub.add_parser("languages")
    lg.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "name":
        result = check_name(args.name, args.language, args.character,
                            args.home_words)
    elif args.cmd == "batch":
        pairs = [a.partition("/") for a in args.names]
        new = [f.strip() for f, _, _ in pairs]
        fams = {f.strip(): fam.strip() for f, _, fam in pairs if fam.strip()}
        result = check_batch(new, args.language, args.kind, fams,
                             parse_shares(args.formal_shares),
                             parse_shares(args.familiar_shares))
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
