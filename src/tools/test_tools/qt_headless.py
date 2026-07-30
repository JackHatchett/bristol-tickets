"""qt_headless.py — shared helpers for running the fleet's PySide6 GUI tools
without a display, so their runtime health can be checked in a sandbox.

This is the reusable core of test_tools' runtime-error checking: it renders to
Qt's ``offscreen`` platform, which builds real widgets (catching import errors,
signal/slot mismatches, and construction-time exceptions) but paints nothing.
It is deliberately environment-agnostic — on a machine with PySide6 and a real
display it still works; ``run_smoke.sh`` handles the extra provisioning the
Linux sandbox needs (installing PySide6, fetching GL/EGL libs).

Nothing here is specific to one GUI: ``tool_on_path`` + ``offscreen_app`` are
all a per-tool check needs to import that tool's package and build its window.
"""

from __future__ import annotations

import os
import sys
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


PROJECT_ROOT = _project_root()
TOOLS = PROJECT_ROOT / "src" / "tools"


def tool_on_path(tool_name: str) -> Path:
    """Put a sibling tool's directory first on sys.path so its top-level
    packages (each GUI tool ships its own ``ui`` package and ``app.py``) import.
    Because two tools both expose a package named ``ui``, only ONE tool may be
    imported per process — the smoke runner isolates each target in a subprocess
    for exactly this reason."""
    tool_dir = TOOLS / tool_name
    if not tool_dir.is_dir():
        raise FileNotFoundError(f"no such tool dir: {tool_dir}")
    p = str(tool_dir)
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)
    return tool_dir


def offscreen_app():
    """Return a QApplication bound to the offscreen platform (created once).
    Sets QT_QPA_PLATFORM defensively in case the caller didn't go through
    run_smoke.sh."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
