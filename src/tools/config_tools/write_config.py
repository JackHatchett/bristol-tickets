#!/usr/bin/env python3
"""write_config.py — the one place anything writes config.local.json.

`read_config.py` owns finding and reading the file; this owns changing it. A
write round-trips the whole document and replaces one dotted key, so a key this
build knows nothing about survives untouched.

GitHub-safe: contains no personal data or absolute user paths.

CLI
---
    python3 write_config.py agents.librarian.skills '["add-book"]'
    python3 write_config.py session.work_whole_queue false

The value is parsed as JSON, and falls back to the literal string when it is
not valid JSON, so a bare word needs no quoting.

Import
------
    from write_config import set_key
    set_key("agents.librarian.skills", ["add-book"])
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import read_config  # noqa: E402  (runs as a script as well as a module)


def set_key(dotted: str, value) -> Path:
    """Set one dotted key, leaving every other key as it was.

    Missing intermediate dictionaries are created. Returns the path written.
    """
    path = read_config.config_path()
    if not path.exists():
        raise SystemExit(f"write_config: config not found at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    node = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def parse_value(raw: str):
    """The argument as JSON, or as the literal string when it is not JSON."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: write_config.py <dotted.key> <json-value>", file=sys.stderr)
        return 2
    dotted, raw = argv
    written = set_key(dotted, parse_value(raw))
    print(f"{dotted} written to {written.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
