#!/usr/bin/env python3
"""locations.py — every folder and file the configuration points at, so each
can be checked and repointed without opening the file.

A location is any value in config.local.json that names a place on disk: a key
ending in _dir, _db, _path, _file or _folder, a `root`, a `path`, an
environment variable whose value is a path, an agent's folder grants and
context files, and its charter. The Markdown notebook folder and its attached
folders are not listed here; `notebook.py` owns them, because repointing the
notebook detaches its folders.

Each location is reported with where it resolves, through `data_paths.resolve`,
and whether that is on disk. Setting one stores the picked path the way
`data_paths.declare` spells it, so a path inside the project or the notebook
survives the folder moving.

CLI
---
    python3 locations.py list [--json] [--missing]
    python3 locations.py set '<pointer as a JSON list>' <picked path>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_paths  # noqa: E402
import read_config  # noqa: E402

PATH_SUFFIXES = ("_dir", "_db", "_path", "_file", "_folder")
PATH_KEYS = {"root", "path", "identity", "tickets_db", "personal_db"}
FILE_HINTS = ("_db", "_file", "identity", "key_context_files")
# Owned by notebook.py, or carrying no path at all.
SKIPPED = {("markdown_notebook", "notes_dir"), ("markdown_notebook", "folders")}
SKIPPED_TOP = {"keyword_scan", "governance", "stack", "tiers", "sizing",
               "appearance", "board", "session", "bluesky_index_related"}


def _looks_like_path(value: str) -> bool:
    v = value.strip()
    return bool(v) and (v.startswith(("/", "~", "data/", "src/"))
                        or "/" in v and not v.startswith(("http", "did:"))
                        and " " not in v.split("/")[0])


# What a step of a pointer is called on screen, where its key is not enough.
_STEP_NAMES = {"key_data_paths": "Folder", "key_context_files": "Context File",
               "identity": "Charter", "env": None, "path": None,
               "folders": None, "notebook_projects": "Notebook Project",
               "local_projects": "Local Project"}


_SMALL = {"a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "by"}


def _words(text: str) -> str:
    parts = [w for w in text.split("_") if w]
    return " ".join(w if i and w in _SMALL else w[:1].upper() + w[1:]
                    for i, w in enumerate(parts))


def _label(pointer: list) -> str:
    """A location as a person reads it: Agents › Writers Room › Folder,
    Markdown Notebook › Reports Dir, Zotero › ZOTERO_DATA_DIR."""
    words = []
    for i, part in enumerate(pointer):
        if isinstance(part, int):
            continue
        key = str(part)
        if key in _STEP_NAMES:
            if _STEP_NAMES[key]:
                words.append(_STEP_NAMES[key])
            continue
        if i and pointer[i - 1] == "env":
            words.append(key)
        else:
            words.append(_words(key))
    return " › ".join(words)


def _walk(node, pointer: list, out: list) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key.startswith("_") or key in ("notes", "tags"):
                continue
            here = pointer + [key]
            if len(here) == 1 and key in SKIPPED_TOP:
                continue
            if tuple(here[-2:]) in SKIPPED:
                continue
            if isinstance(value, str):
                named = key in PATH_KEYS or key.endswith(PATH_SUFFIXES) \
                    or "env" in pointer and _looks_like_path(value) \
                    or pointer and pointer[-1] == "folders" and isinstance(value, str)
                if named and _looks_like_path(value) or key in PATH_KEYS and value.strip():
                    out.append((here, value))
            else:
                _walk(value, here, out)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            here = pointer + [i]
            if isinstance(value, str):
                if pointer and pointer[-1] in ("key_context_files", "key_data_paths",
                                               "notebook_projects", "local_projects") \
                        and _looks_like_path(value):
                    out.append((here, value))
            else:
                _walk(value, here, out)


def locations(data: dict | None = None) -> list[dict]:
    data = read_config.load() if data is None else data
    found: list = []
    _walk(data, [], found)
    rows = []
    for pointer, value in found:
        try:
            resolved = data_paths.resolve(value)
        except (ValueError, SystemExit):
            continue
        kind = "file" if any(str(p).endswith(FILE_HINTS) or p in FILE_HINTS
                             for p in pointer if isinstance(p, str)) \
            or resolved.suffix else "dir"
        rows.append({"pointer": pointer, "label": _label(pointer),
                     "value": value, "resolved": str(resolved),
                     "exists": resolved.exists(), "kind": kind})
    return rows


def set_location(pointer: list, picked: str) -> str:
    """Store a picked path at `pointer`, declared the portable way."""
    path = read_config.config_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    node = data
    for part in pointer[:-1]:
        node = node[part]
    declared = data_paths.declare(picked)
    if declared.startswith(str(Path.home())) and not \
            str(node[pointer[-1]]).startswith("/"):
        declared = "~" + declared[len(str(Path.home())):]
    node[pointer[-1]] = declared
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return declared


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--json", action="store_true")
    ls.add_argument("--missing", action="store_true")
    st = sub.add_parser("set")
    st.add_argument("pointer")
    st.add_argument("path")
    args = p.parse_args(argv)
    if args.cmd == "list":
        rows = locations()
        if args.missing:
            rows = [r for r in rows if not r["exists"]]
        if args.json:
            print(json.dumps(rows))
        else:
            for r in rows:
                print(f"{'ok     ' if r['exists'] else 'MISSING'} {r['label']}: {r['value']}")
        return 0
    print(set_location(json.loads(args.pointer), os.path.expanduser(args.path)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
