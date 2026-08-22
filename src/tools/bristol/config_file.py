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

# Whether a session that halts for room ends with a commit block for what it
# wrote. Read by the agent at the moment the offer would fire, never by the app.
SUGGESTED_COMMIT = "session.suggested_commit"
SUGGESTED_COMMIT_DEFAULT = True

# Which colour scheme the app draws with. The value is a scheme name or a family
# name from ``ui/theme.py``; a family means "follow the OS within it".
APPEARANCE_SCHEME = "appearance.scheme"
APPEARANCE_SCHEME_DEFAULT = "warm"

# Where the detail pane sits: its width in device-independent pixels, and
# whether it is collapsed to the window edge. The main window writes these as
# the user moves the splitter or toggles the pane, so both survive a restart.
DETAIL_WIDTH = "appearance.detail_width"
DETAIL_COLLAPSED = "appearance.detail_collapsed"


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
    """Where this installation's configuration lives, or None if unplaced.

    The instance pointer answers first, and only while it names a file that is
    there. A pointer left behind by an installation that has since been removed
    otherwise hides the configuration sitting beside the tree in use, and every
    field reads as absent.
    """
    pointed = instance.get_path("config_path")
    if pointed is not None and pointed.is_file():
        return pointed
    root = project_root()
    if root is not None:
        return root / "config" / "config.local.json"
    return pointed


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
