"""config_file.py — this installation's configuration, as Bristol Tickets
reads it.

Bristol Tickets is self-contained: it imports nothing from the rest of
``src/tools/``, so this is a local reader and writer for the same ``config/config.local.json``
that ``config_tools/read_config.py`` owns. There is one file; the setup wizard,
the Settings tab and the agents all read and write these fields in it.

A save round-trips the whole document and replaces only the keys it is handed,
so a key this build knows nothing about survives untouched.

GitHub-safe: contains no personal path.
"""

from __future__ import annotations

import json
from pathlib import Path

import instance

# The board's own settings, named once so the UI, the CLI and the governing
# docs all say the same thing.
CROSS_AGENT_STAGE = "board.cross_agent_stage"
CROSS_AGENT_STAGE_DEFAULT = "active"


def project_root() -> Path | None:
    """The cloned folder: the nearest ancestor holding ``src/app.md``.

    Falls back to the instance pointer's ``repo_root``, which is what a
    relocated ``.app`` bundle has instead of an ancestor.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "app.md").is_file():
            return parent
    pointed = instance.get_path("repo_root")
    if pointed is not None and (pointed / "src" / "app.md").is_file():
        return pointed
    return None


def path() -> Path | None:
    """Where this installation's configuration lives, or None if unplaced."""
    pointed = instance.get_path("config_path")
    if pointed is not None:
        return pointed
    root = project_root()
    return None if root is None else root / "config" / "config.local.json"


def read() -> dict:
    """The configuration, or an empty dict when it is absent or unreadable."""
    target = path()
    if target is None:
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get(dotted: str, default=None):
    """One dotted key out of the configuration."""
    node = read()
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def write(data: dict, target: Path | None = None) -> Path:
    """Replace the configuration with `data`. Returns the path written."""
    destination = target or path()
    if destination is None:
        raise OSError("no configuration file to write (this clone is unplaced)")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return destination


def update(changes: dict) -> Path:
    """Set each dotted key to its value, leaving every other key as it was."""
    data = read()
    for dotted, value in changes.items():
        node = data
        parts = dotted.split(".")
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = value
    return write(data)


def agent_slugs() -> list[str]:
    """Every agent this installation configures, in configured order."""
    agents = read().get("agents")
    if not isinstance(agents, dict):
        return []
    return [slug for slug in agents if slug != "_notes"]
