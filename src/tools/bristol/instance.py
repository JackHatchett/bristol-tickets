"""instance.py — read the per-machine instance pointer.

Bristol is self-contained: it imports nothing from the rest of ``src/tools/``,
so this is a local reader for the same file that
``config_tools/instance_pointer.py`` owns. That module holds the canonical
resolution order and the pointer's schema; this one only reads.

GitHub-safe: contains no personal path.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_DIR_NAME = "BristolTickets"
FILE_NAME = "instance.json"


def pointer_path() -> Path:
    """Where the pointer lives on this machine."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / APP_DIR_NAME / FILE_NAME


def read() -> dict:
    """The pointer's contents, or an empty dict if absent or unreadable."""
    try:
        data = json.loads(pointer_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_path(key: str) -> Path | None:
    """One of the pointer's path fields, expanded, or None."""
    value = read().get(key)
    if isinstance(value, str) and value.strip():
        return Path(os.path.expanduser(value.strip()))
    return None
