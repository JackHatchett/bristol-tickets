"""paths.py — resolve the notebook folder the reports are written into.

This is the one place in the reports package that is allowed to know about
out-of-repo locations, and it never hardcodes one. Resolution order mirrors the
pattern app.py already uses for the database, for the same reason: Bristol may
be running in-place from the repo, or as a relocated .app that cannot see the
repo at all.

    1. BRISTOL_REPORTS_DIR env var           — explicit override, testing
    2. bristol/bristol_reports.local         — one line, absolute path.
                                               Git-ignored; bundled into the
                                               .app at build time so the
                                               relocated app still knows where
                                               the notebook is.
    3. config/config.local.json              — markdown_notebook.reports_dir,
                                               the real source of truth when
                                               running from the repo.

Returns None when nothing resolves, which the caller treats as "skip the
report" rather than an error — a missing notebook must never cost the user
their Clear Done.

GitHub-safe: contains no personal path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


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


_ENV_VAR = "BRISTOL_REPORTS_DIR"
_LOCAL_POINTER = "bristol_reports.local"
_CONFIG_KEY = ("markdown_notebook", "reports_dir")


def _from_env() -> Path | None:
    value = os.environ.get(_ENV_VAR)
    return Path(os.path.expanduser(value)) if value else None


def _from_local_pointer() -> Path | None:
    """A git-ignored one-line file next to app.py holding an absolute path.
    This is what makes report writing work from a built .app, which has no view
    of the repo's config/ directory."""
    pointer = Path(__file__).resolve().parents[1] / _LOCAL_POINTER
    if not pointer.exists():
        return None
    text = pointer.read_text(encoding="utf-8").strip()
    return Path(os.path.expanduser(text)) if text else None


def _from_config() -> Path | None:
    """Read markdown_notebook.reports_dir from the git-ignored config.

    Walks up from this file to the repo root rather than assuming a working
    directory. Any failure — no repo, no config, no key — returns None; this
    resolver is one of three and must not raise for the others to be tried.
    """
    root = _project_root()
    config_path = Path(
        os.environ.get("CONFIG_LOCAL_JSON")
        or (root / "config" / "config.local.json")
    ).expanduser()
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for key in _CONFIG_KEY:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return Path(os.path.expanduser(data)) if isinstance(data, str) and data else None


def resolve_reports_dir(explicit: str | os.PathLike | None = None) -> Path | None:
    """The folder reports are written to, or None if it cannot be determined.

    `explicit` (a CLI --out-dir) wins over everything. The directory is created
    if its parent exists; if the parent does not, the notebook itself is
    missing (an unmounted iCloud folder, say) and we return None rather than
    materialising a stray tree in the wrong place.
    """
    candidate = (
        Path(os.path.expanduser(str(explicit))) if explicit
        else _from_env() or _from_local_pointer() or _from_config()
    )
    if candidate is None:
        return None
    if candidate.is_dir():
        return candidate
    if candidate.parent.is_dir():
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    return None
