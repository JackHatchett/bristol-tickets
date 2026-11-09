#!/usr/bin/env python3
"""plot_alignment.py — the plot alignment sheet, generated from a novel's
tiered outline notes, and the cell writes that bring the sheet up to date with
them without moving any beat the author has placed.

The notes are the source of every word in the sheet; the sheet's arrangement —
which row a beat sits on — is the author's. `build` gives the sheet as the
notes would generate it; `sync` reads the sheet as it stands and gives the
writes that carry the notes' changes into it.

Where everything is, is config, `agents.<agent>.plot_alignment`, the
key of whichever agent has it:

    {"sheet_url": "<the Google Sheet>",
     "plot_dir": "<folder containing the outline notes>",
     "tabs": [{"title": "<tab>", "outline": "<outline note's filename>",
               "bands": [{"label": "<divider text>", "tags": ["book 1", ...]}]}]}

CLI
---
    python3 plot_alignment.py build [--tab <title>]
    python3 plot_alignment.py sync <sheet.json>

`sheet.json` maps each tab's title to its values, row by row, as the Sheets
API returns them for the range A1 to the last used cell. `build` prints each
tab's rows; `sync` prints the writes as JSON, each with its A1 cell, in the
order they are applied.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))

NO_BAND = "No Book Given"
POINTS = ("Hook", "Plot Turn 1", "Pinch 1", "Midpoint", "Pinch 2",
          "Plot Turn 2", "Resolution")
# Column groups, left to right; a group with no column is left out, and a
# blank column parts each group from the next.
GROUPS = [("character", True, "Character Arcs with Parallels"),
          ("character_story", True, "Character Stories with Parallels"),
          ("romance", True, "Romances with Parallels"),
          ("story", True, "Stories with Parallels"),
          ("character", False, "Character Arcs"),
          ("character_story", False, "Character Stories"),
          ("romance", False, "Romances"),
          ("story", False, "Stories"),
          ("setting", None, "Setting Promises")]
HEADER_ROWS = 3

WIKILINK = re.compile(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]")
TAG = re.compile(r"\((books? \d+(?: (?:and|to) \d+)?|cycle \d+|prologue)\)\s*$")
FORMULA_LINK = re.compile(r'HYPERLINK\("([^"]+)"')


def plain(text: str) -> str:
    """Markdown text as the sheet shows it: a link by its display text."""
    text = WIKILINK.sub(lambda m: m.group(2) or m.group(1), text)
    return re.sub(r"[*_`]", "", text).strip()


def tag_of(text: str) -> str | None:
    m = TAG.search(text)
    if not m:
        return None
    tag = m.group(1)
    if tag.startswith("books"):
        tag = "book " + tag.split()[1]
    return tag


# --- reading the notes -------------------------------------------------------

def _settings() -> dict:
    """The `plot_alignment` key of whichever agent's config entry has one."""
    import read_config
    for entry in (read_config.get("agents", None) or {}).values():
        if isinstance(entry, dict) and entry.get("plot_alignment"):
            return entry["plot_alignment"]
    return {}


def _resolve(path: str) -> Path:
    import data_paths
    return data_paths.resolve(path)


def _sections(text: str) -> dict[str, list[str]]:
    out, current = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = []
        elif line.startswith("# ") and current is None:
            out["#"] = [line[2:].strip()]
        elif current:
            out[current].append(line)
    return out


class Sheet:
    """One plot sheet in the notes."""

    def __init__(self, path: Path, plot_dir: Path):
        self.path = path
        self.rel = path.relative_to(plot_dir)
        text = path.read_text(encoding="utf-8")
        sec = _sections(text)
        self.title = plain((sec.get("#") or [path.stem])[0])
        self.promise = ""
        details = sec.get("Details", [])
        for i, line in enumerate(details):
            if line.strip().startswith("- Promise to the Reader"):
                inline = line.split("Promise to the Reader", 1)[1].strip(" -")
                nxt = details[i + 1].strip() if i + 1 < len(details) else ""
                self.promise = plain(inline or nxt.lstrip("- "))
        self.points = {}
        for line in sec.get("Seven-Point Highlights", []):
            m = re.match(r"^- (.+?) - (.+)$", line.strip())
            if m and m.group(1) in POINTS:
                self.points[plain(m.group(2))] = m.group(1)
        self.beats = []
        for line in sec.get("Beats", []):
            m = re.match(r"^\d+\. (.+)$", line)
            if m:
                self.beats.append(plain(m.group(1)))
        self.links = [m.group(1) for line in sec.get("Related Notes", [])
                      for m in WIKILINK.finditer(line)]

    def labelled(self, beat: str) -> str:
        label = self.points.get(beat)
        return f"{label}: {beat}" if label else beat


def plot_sheets(plot_dir: Path) -> dict[str, Sheet]:
    sheets = {}
    for p in plot_dir.rglob("*.md"):
        if p.parent == plot_dir:
            continue
        sheets[p.stem] = Sheet(p, plot_dir)
    return sheets


def outline_columns(outline: Path, sheets: dict[str, Sheet], tier: str):
    """(sheet, kind) for every plot sheet the outline links, in link order."""
    sec = _sections(outline.read_text(encoding="utf-8"))
    seen, cols = set(), []
    for name, kind_default in (("Characters", "character_story"),
                               ("Plot", "story"), ("Setting", "setting")):
        for line in sec.get(name, []):
            for m in WIKILINK.finditer(line):
                stem = m.group(1)
                sheet = sheets.get(stem)
                if not sheet or stem in seen or sheet.rel.parts[0] != tier:
                    continue
                seen.add(stem)
                folder = sheet.rel.parts[1] if len(sheet.rel.parts) > 2 else ""
                if folder in ("character", "romance"):
                    kind = folder
                else:
                    kind = kind_default
                cols.append((sheet, kind))
    return cols


def has_parallel(sheet: Sheet, sheets: dict[str, Sheet]) -> bool:
    """Whether the plot has a parallel: a sheet of the same kind at another
    tier, linked from either sheet's Related Notes."""
    def kind(sh):
        return sh.rel.parts[1] if len(sh.rel.parts) > 2 else ""
    stem = sheet.path.stem
    for other in sheets.values():
        if other.rel.parts[0] == sheet.rel.parts[0] or kind(other) != kind(sheet):
            continue
        if other.path.stem in sheet.links or stem in other.links:
            return True
    return False


def obsidian_link(path: Path) -> str:
    import read_config
    root = _resolve(read_config.get("markdown_notebook.notes_dir"))
    rel = path.resolve().relative_to(root.resolve()).with_suffix("")
    return (f"obsidian://open?vault={quote(root.name)}"
            f"&file={quote(rel.as_posix(), safe='')}")


# --- generating a tab --------------------------------------------------------

def _band_of(tag: str | None, bands: list[dict]) -> str | None:
    for band in bands:
        if tag in band["tags"]:
            return band["label"]
    return None


def column_beats(sheet: Sheet, sheets: dict[str, Sheet], tab: dict,
                 tier: str) -> list[tuple[str, str | None]]:
    """(text, band) for each beat the column contains, in order."""
    bands = tab.get("bands") or []
    beats = [(sheet.labelled(b), b) for b in sheet.beats]
    if not beats and tier.startswith("book_"):
        book = "book " + tier.split("_")[1]
        for stem in sheet.links:
            parent = sheets.get(stem)
            if not parent or parent.rel.parts[0] == tier:
                continue
            got = [(f"{TAG.sub('', parent.labelled(b)).rstrip()}  "
                    f"[{parent.title}]", b)
                   for b in parent.beats if tag_of(b) == book]
            if got:
                beats = got
                break
    if not bands:
        return [(text, None) for text, _ in beats]
    out, current = [], None
    for text, raw in beats:
        band = _band_of(tag_of(raw), bands) or current
        current = band
        out.append((text, band))
    return [(t, b or NO_BAND) for t, b in out]


def build_tab(tab: dict) -> dict:
    s = _settings()
    plot_dir = _resolve(s["plot_dir"])
    sheets = plot_sheets(plot_dir)
    outline = plot_dir / tab["outline"]
    tier = outline.stem.replace("_outline", "").lstrip("_")
    cols = outline_columns(outline, sheets, tier)
    groups = []
    for kind, parallel, label in GROUPS:
        members = [sh for sh, k in cols if k == kind and
                   (parallel is None or has_parallel(sh, sheets) == parallel)]
        if members:
            groups.append({"label": label, "columns": [
                {"title": sh.title, "link": obsidian_link(sh.path),
                 "note": sh.rel.as_posix(), "promise": sh.promise,
                 "beats": column_beats(sh, sheets, tab, tier)}
                for sh in members]})
    band_labels = [b["label"] for b in tab.get("bands") or []]
    if band_labels:
        band_labels.append(NO_BAND)
    return {"title": tab["title"], "groups": groups, "bands": band_labels}


def layout(built: dict) -> list[list[str]]:
    """The tab as rows of cell text, the way a fresh build writes it."""
    columns, row1 = [], []
    for gi, group in enumerate(built["groups"]):
        if gi:
            columns.append(None)
            row1.append("")
        for ci, col in enumerate(group["columns"]):
            columns.append(col)
            row1.append(group["label"] if ci == 0 else "")
    rows = [row1, [c["title"] if c else "" for c in columns],
            [c["promise"] if c else "" for c in columns]]
    bands = built["bands"] or [None]
    for band in bands:
        depth = max([sum(1 for _, b in c["beats"] if b == band)
                     for c in columns if c] + [0])
        if band is not None:
            if not depth:
                if band == NO_BAND:
                    continue
            rows.append([band] + [""] * (len(columns) - 1))
        for i in range(depth):
            row = []
            for c in columns:
                mine = [t for t, b in c["beats"] if b == band] if c else []
                row.append(mine[i] if i < len(mine) else "")
            rows.append(row)
    return rows


def tabs() -> list[dict]:
    return _settings().get("tabs") or []


# --- syncing -----------------------------------------------------------------

def col_letter(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def a1(row: int, col: int) -> str:
    return f"{col_letter(col)}{row + 1}"


def _cell(grid, r, c) -> str:
    return grid[r][c] if r < len(grid) and c < len(grid[r]) else ""


def sync_tab(built: dict, grid: list[list[str]]) -> tuple[list[dict], list[str]]:
    ops, report = [], []
    title = built["title"]
    band_set = set(built["bands"])
    grid = [list(r) for r in grid]
    width = max((len(r) for r in grid), default=0)

    def is_band_row(r):
        first = _cell(grid, r, 0)
        return first in band_set and not any(_cell(grid, r, c)
                                              for c in range(1, width))

    def band_at(r):
        current = None
        for rr in range(HEADER_ROWS, r + 1):
            if is_band_row(rr):
                current = _cell(grid, rr, 0)
        return current

    def link_of(c):
        m = FORMULA_LINK.search(_cell(grid, 1, c))
        return unquote(m.group(1)) if m else None

    sheet_cols = [c for c in range(width) if _cell(grid, 1, c)]
    wanted = [col for g in built["groups"] for col in g["columns"]]
    by_link = {unquote(col["link"]): col for col in wanted}
    by_title = {col["title"]: col for col in wanted}
    matched, used = {}, set()
    for c in sheet_cols:
        col = by_link.get(link_of(c)) or by_title.get(_cell(grid, 1, c))
        if col and id(col) not in used:
            matched[c] = col
            used.add(id(col))
    loose_sheet = [c for c in sheet_cols if c not in matched]
    loose_notes = [col for col in wanted if id(col) not in used]
    if len(loose_sheet) == 1 and len(loose_notes) == 1:
        matched[loose_sheet[0]] = loose_notes[0]
        used.add(id(loose_notes[0]))
        loose_sheet, loose_notes = [], []
    for c in loose_sheet:
        ops.append({"tab": title, "op": "remove_column", "column": col_letter(c),
                    "title": _cell(grid, 1, c)})
        report.append(f"{title}: {_cell(grid, 1, c)} is in no outline link; "
                      "its column is removed")
    for col in loose_notes:
        group = next(g["label"] for g in built["groups"] if col in g["columns"])
        ops.append({"tab": title, "op": "add_column", "group": group,
                    "title": col["title"], "link": col["link"],
                    "promise": col["promise"], "beats": col["beats"]})
        report.append(f"{title}: {col['title']} is new; its column goes at the "
                      f"end of {group}, its beats packed from the top of each band")

    for c, col in sorted(matched.items()):
        formula = f'=HYPERLINK("{col["link"]}","{col["title"]}")'
        if _cell(grid, 1, c) != col["title"] and _cell(grid, 1, c) != formula:
            ops.append({"tab": title, "op": "set", "cell": a1(1, c),
                        "value": formula})
        if _cell(grid, 2, c) != col["promise"]:
            ops.append({"tab": title, "op": "set", "cell": a1(2, c),
                        "value": col["promise"]})
        placed = [r for r in range(HEADER_ROWS, len(grid))
                  if _cell(grid, r, c) and not is_band_row(r)]
        have = [_cell(grid, r, c) for r in placed]
        want = [t for t, _ in col["beats"]]
        bands = [b for _, b in col["beats"]]
        sm = difflib.SequenceMatcher(a=have, b=want, autojunk=False)
        new_rows = list(placed)
        shift_ops = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            pairs = min(i2 - i1, j2 - j1) if tag == "replace" else 0
            for k in range(pairs):
                r = placed[i1 + k]
                shift_ops.append(("set", r, want[j1 + k]))
            for k in range(i1 + pairs, i2):
                shift_ops.append(("clear", placed[k], None))
            for k in range(j1 + pairs, j2):
                before = placed[i1 + pairs - 1] if i1 + pairs > 0 else None
                if before is None and i1 > 0:
                    before = placed[i1 - 1]
                after = placed[i2] if i2 < len(placed) else None
                shift_ops.append(("insert", before, (want[k], bands[k], after)))
        offset = 0
        last_insert = {}
        for kind, r, payload in shift_ops:
            if kind == "set":
                ops.append({"tab": title, "op": "set", "cell": a1(r + offset, c),
                            "value": payload})
                grid[r + offset][c] = payload
            elif kind == "clear":
                ops.append({"tab": title, "op": "clear", "cell": a1(r + offset, c),
                            "was": _cell(grid, r + offset, c)})
                grid[r + offset][c] = ""
            else:
                text, band, after = payload
                start = (last_insert.get(r, r + offset if r is not None
                                         else HEADER_ROWS - 1)) + 1
                stop = after + offset if after is not None else len(grid)
                spot = None
                for rr in range(start, stop):
                    if not is_band_row(rr) and not _cell(grid, rr, c) \
                            and (band is None or band_at(rr) == band):
                        spot = rr
                        break
                if spot is None:
                    spot = start
                    if band is not None:
                        while spot < len(grid) and band_at(spot) != band:
                            spot += 1
                        if spot < len(grid) and is_band_row(spot):
                            spot += 1
                    ops.append({"tab": title, "op": "insert_row",
                                "row": spot + 1})
                    grid.insert(spot, [""] * width)
                    offset += 1
                    report.append(f"{title}: a row is inserted at {spot + 1} for "
                                  f"a new beat of {col['title']}; every column "
                                  "moves down together")
                while len(grid[spot]) < width:
                    grid[spot].append("")
                grid[spot][c] = text
                ops.append({"tab": title, "op": "set", "cell": a1(spot, c),
                            "value": text})
                last_insert[r] = spot
        for r in range(HEADER_ROWS, len(grid)):
            text = _cell(grid, r, c)
            if text and not is_band_row(r) and text in want:
                b = bands[want.index(text)]
                if b is not None and band_at(r) != b:
                    report.append(f"{title}: {col['title']} - '{text[:50]}' sits "
                                  f"under {band_at(r)} and is tagged for {b}")
    return ops, report


def sync(sheet_values: dict) -> dict:
    ops, report = [], []
    for tab in tabs():
        grid = sheet_values.get(tab["title"])
        if grid is None:
            report.append(f"{tab['title']}: not in the sheet read")
            continue
        o, r = sync_tab(build_tab(tab), grid)
        ops += o
        report += r
    return {"writes": ops, "report": report}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--tab")
    s = sub.add_parser("sync")
    s.add_argument("sheet_json")
    args = p.parse_args(argv)
    if args.cmd == "build":
        out = {}
        for tab in tabs():
            if args.tab and tab["title"] != args.tab:
                continue
            built = build_tab(tab)
            out[tab["title"]] = {"rows": layout(built),
                                 "groups": [{"label": g["label"], "columns":
                                             [c["title"] for c in g["columns"]]}
                                            for g in built["groups"]],
                                 "links": [c["link"] for g in built["groups"]
                                           for c in g["columns"]]}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    data = json.loads(Path(args.sheet_json).read_text(encoding="utf-8"))
    print(json.dumps(sync(data), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
