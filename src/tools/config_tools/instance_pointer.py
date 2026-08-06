"""instance_pointer.py — the per-machine pointer to this installation.

THE CANONICAL RESOLUTION ORDER. Every resolver in this repo — the tickets DB
(``bristol/app.py``), the reports directory (``bristol/reports/paths.py``) and
the config file (``read_config.py``) — follows this order and no other:

    1. An explicit env override (``TICKETS_DB``, ``BRISTOL_REPORTS_DIR``,
       ``CONFIG_LOCAL_JSON``). First so a test run or a one-off can always win.
    2. The instance pointer described here.
    3. A legacy one-line ``.local`` file next to the resolver.
    4. Relative discovery from the source tree — walk up to the marker
       ``src/app.md``, then look under ``data/``.

Step 4 only works when the code is still sitting above the repo's ``data/``
folder, which a relocated ``.app`` bundle is not. That is what the pointer is
for: one small JSON file, per machine, outside the repo, so it can never be
committed and never needs to be bundled into the app.

The file::

    ~/Library/Application Support/BristolTickets/instance.json   (macOS)
    $XDG_CONFIG_HOME/BristolTickets/instance.json                (elsewhere,
                                                 default ~/.config/...)

Its shape::

    {
      "repo_root":     "/absolute/path/to/the/clone",
      "data_root":     "/absolute/path/to/the/clone/data",
      "instance_slug": "your-instance",
      "config_path":   "/absolute/path/to/the/clone/config/config.local.json"
    }

``data_root`` is the folder the installations sit in, never one installation's
own folder: the board is ``data_root/instance_slug/tickets/tickets.db``, and
every writer of this file writes that shape.

Every field is optional to a reader: a caller asks for the one it needs and
falls through to the next step when it is absent. A malformed or unreadable
file resolves to nothing rather than raising — a bad pointer must never stop
the repo-run path from working.

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
    """The pointer's contents, or an empty dict if it is absent or unreadable."""
    path = pointer_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_path(key: str) -> Path | None:
    """One of the pointer's path fields, expanded, or None."""
    value = read().get(key)
    if isinstance(value, str) and value.strip():
        return Path(os.path.expanduser(value.strip()))
    return None


def write(repo_root, data_root, instance_slug: str, config_path) -> Path:
    """Create or replace the pointer. Returns the path written."""
    path = pointer_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "repo_root": str(repo_root),
                "data_root": str(data_root),
                "instance_slug": instance_slug,
                "config_path": str(config_path),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _default_repo_root() -> Path:
    """The nearest ancestor of this file holding src/app.md."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "app.md").is_file():
            return parent
    raise SystemExit("no project root above this file (no ancestor holds src/app.md)")


def _default_data_root(root: Path) -> Path:
    """The folder this clone's installations sit in.

    ``important_paths.tickets_db`` names the board, so its board and instance
    folders strip back to the data root. A clone with no configuration, or one
    whose board sits under the clone, resolves to ``<root>/data``. Read here
    rather than through ``read_config``, which imports this module.
    """
    try:
        config = json.loads(
            (root / "config" / "config.local.json").read_text(encoding="utf-8")
        )
        declared = config["important_paths"]["tickets_db"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return root / "data"
    if not isinstance(declared, str) or not declared.strip():
        return root / "data"
    board = Path(os.path.expanduser(declared.strip()))
    if not board.is_absolute():
        board = root / board
    parents = board.parents
    return parents[2] if len(parents) > 2 else root / "data"


def _main(argv: list[str]) -> int:
    """Print the pointer, or write one for the clone this file lives in."""
    if "--write" not in argv:
        p = pointer_path()
        print(f"pointer: {p}")
        print(json.dumps(read(), indent=2) if p.exists() else "(not present)")
        return 0

    root = _default_repo_root()
    data_root = _default_data_root(root)
    slugs = [d.parent.name for d in sorted(data_root.glob("*/tickets")) if d.is_dir()]
    if "--instance" in argv:
        slug = argv[argv.index("--instance") + 1]
    elif len(slugs) == 1:
        slug = slugs[0]
    else:
        raise SystemExit(
            f"instance_pointer: pass --instance <slug>; under {data_root} found "
            + (", ".join(slugs) or "no <instance>/tickets/ folder")
        )
    written = write(root, data_root, slug, root / "config" / "config.local.json")
    print(f"wrote {written}")
    print(json.dumps(read(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
