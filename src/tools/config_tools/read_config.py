#!/usr/bin/env python3
"""read_config.py — the one place anything reads config.local.json.

`config.local.json` is the single structured source of truth for this system's
routing (drives, runtime/data folders, the agent registry, important paths,
governance). This helper lets every "head" of the application read *exactly the
field it needs* without loading the whole document — which is the entire reason
the config lives in JSON rather than being mirrored into Markdown prose.

GitHub-safe: contains no personal data or absolute user paths. It resolves the
git-ignored config file at runtime.

CLI
---
    python3 read_config.py drives.external1.path
        -> /Volumes/<ExternalDrive>
    python3 read_config.py important_paths.tickets_db
        -> data/<instance>/tickets/tickets.db
    python3 read_config.py agents.career_coach.notebook_access.write_zones
        -> []
    python3 read_config.py agents.teaching_assistant.key_data_paths.0
        -> data/<instance>/teaching
    python3 read_config.py agents                 # whole subtree, pretty JSON
    python3 read_config.py --keys agents          # list child keys of a subtree
    python3 read_config.py --expanduser drives.icloud.path   # ~ expanded

Exit status is non-zero if the key path is missing, so it composes in shells:
    DB=$(python3 read_config.py important_paths.tickets_db) || exit 1

Import
------
    from read_config import get, load
    db = get("important_paths.tickets_db")
    everything = load()
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instance_pointer  # noqa: E402  (runs as a script as well as a module)


def _project_root() -> Path:
    """The project root: the nearest ancestor holding src/app.md.

    Located by marker rather than by folder name, so the install works whatever
    the user named the folder they cloned into.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "app.md").is_file():
            return parent
    raise SystemExit(
        "no project root above this file (no ancestor holds src/app.md)"
    )


_ENV_OVERRIDE = "CONFIG_LOCAL_JSON"
_MISSING = object()


def _config_path() -> Path:
    """Locate config/config.local.json.

    Canonical resolution order (see instance_pointer.py): the
    CONFIG_LOCAL_JSON env override, then the per-machine instance pointer,
    then the project root found by marker.
    """
    override = os.environ.get(_ENV_OVERRIDE)
    if override:
        return Path(os.path.expanduser(override))
    pointed = instance_pointer.get_path("config_path")
    if pointed and pointed.exists():
        return pointed
    return _project_root() / "config" / "config.local.json"


def config_path() -> Path:
    """Where this installation's configuration lives."""
    return _config_path()


def load() -> dict:
    """Return the entire parsed config as a dict."""
    path = _config_path()
    if not path.exists():
        raise SystemExit(f"read_config: config not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get(dotted: str, default=_MISSING, *, data: dict | None = None):
    """Return the value at a dotted key path, e.g. 'drives.external1.path'.

    Integer segments index into lists (e.g. 'agents.x.key_data_paths.0').
    Raises KeyError if the path is missing and no default is given.
    """
    node = load() if data is None else data
    for seg in dotted.split("."):
        if isinstance(node, list):
            try:
                node = node[int(seg)]
            except (ValueError, IndexError):
                if default is not _MISSING:
                    return default
                raise KeyError(dotted)
        elif isinstance(node, dict) and seg in node:
            node = node[seg]
        else:
            if default is not _MISSING:
                return default
            raise KeyError(dotted)
    return node


def _render(value, expanduser: bool) -> str:
    if isinstance(value, str):
        return os.path.expanduser(value) if expanduser else value
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, indent=2, ensure_ascii=False)


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("-")]
    expanduser = "--expanduser" in argv
    keys_only = "--keys" in argv

    if not args:
        # No key → dump everything (or top-level keys with --keys).
        data = load()
        print("\n".join(data) if keys_only else json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    dotted = args[0]
    try:
        value = get(dotted)
    except KeyError:
        sys.stderr.write(f"read_config: no such key path: {dotted}\n")
        return 1

    if keys_only:
        if isinstance(value, dict):
            print("\n".join(value.keys()))
        elif isinstance(value, list):
            print("\n".join(str(i) for i in range(len(value))))
        else:
            sys.stderr.write(f"read_config: --keys needs a dict/list, got {type(value).__name__}\n")
            return 1
        return 0

    print(_render(value, expanduser))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
