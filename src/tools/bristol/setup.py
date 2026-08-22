"""setup.py — build a standalone macOS .app for Bristol Tickets with py2app.

Usage:

    python3 make_release.py          # the whole release, and what to do with it
    python3 setup.py py2app          # just the bundle → dist/BristolTickets.app

The build stages the project's published files into the bundle as a payload, so
a downloaded app carries the system it installs rather than only the viewer for
it. What ships is `payload.PUBLISHED_DIRS` and `payload.PUBLISHED_FILES`, which
name neither `config/config.local.json` nor `data/`.

This file is GitHub-safe: it hardcodes no personal path, and it bundles none.
The built app locates the database through the per-machine instance pointer —
see `src/tools/config_tools/instance_pointer.py` for the resolution order. Put
an `icon.icns` next to this file to give the app a custom icon (optional; the
OPTIONS block picks it up only if present).
"""

import shutil
import sys
from pathlib import Path

from setuptools import setup

HERE = Path(__file__).resolve().parent

sys.path.insert(0, str(HERE))
import payload  # noqa: E402  (bristol-local; owns what a release carries)

APP = ["app.py"]


def project_root() -> Path:
    """The folder being packaged: the nearest ancestor holding src/app.md."""
    for parent in HERE.parents:
        if (parent / "src" / "app.md").is_file():
            return parent
    raise SystemExit("setup.py: no project root above this file")


def stage_payload() -> list[tuple[str, list[str]]]:
    """Copy the published files into a staging folder and return them as
    py2app data_files, each landing under Resources/payload/.

    Staged rather than referenced in place, so the build never reaches into the
    working tree for a file it is packaging.
    """
    root = project_root()
    staged = HERE / "build" / payload.PAYLOAD_DIR_NAME
    if staged.exists():
        shutil.rmtree(staged)
    payload.stage(root, staged)

    entries: list[tuple[str, list[str]]] = []
    for path in sorted(staged.rglob("*")):
        if not path.is_file():
            continue
        target = Path(payload.PAYLOAD_DIR_NAME) / path.parent.relative_to(staged)
        entries.append((str(target), [str(path)]))
    return entries


VERSION = payload.version(project_root()) or "0.0.0"

# Files copied into the bundle's Resources. schema.sql must ship so a fresh DB
# can be provisioned. ACKNOWLEDGEMENTS.md must ship because a distributed bundle
# carries compiled LGPL libraries inside it, and their terms travel with them.
# Nothing else: the relocated app finds the database and the notebook through
# the instance pointer, which lives outside the bundle.
DATA_FILES = [f for f in ("schema.sql", "ACKNOWLEDGEMENTS.md") if (HERE / f).exists()]
DATA_FILES += stage_payload()

OPTIONS = {
    "argv_emulation": False,
    # Bundle the ui/ and reports/ packages (py2app's import scanner can miss
    # relative-imported submodules, and reports/ is only reached through a
    # guarded import inside Clear Done, so name both explicitly).
    "packages": ["ui", "reports"],
    "includes": ["sqlite3"],
    # A board draws no Tk windows and installs no packages at runtime.
    "excludes": ["tkinter", "setuptools", "pip", "pkg_resources", "py2app",
                 "pydoc_data", "test"],
    "plist": {
        # CFBundleName drives the bundle directory and the executable, so it
        # holds no space; the display name is what Finder and the menu bar show.
        "CFBundleName": "BristolTickets",
        "CFBundleDisplayName": "Bristol Tickets",
        "CFBundleIdentifier": "local.bristoltickets.app",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        # Not a background agent — show in Dock with a normal window.
        "LSUIElement": False,
    },
}

# Attach a custom icon only if the user dropped one in.
if (HERE / "icon.icns").exists():
    OPTIONS["iconfile"] = "icon.icns"

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

# py2app copies the PySide6 package whole, which is every Qt module Qt ships.
# The bundle is slimmed to what the app imports once the build has written it.
if "py2app" in sys.argv:
    import slim  # noqa: E402  (bristol-local; owns what a bundle keeps)

    bundle = HERE / "dist" / "BristolTickets.app"
    if bundle.is_dir():
        before, after = slim.slim(bundle)
        mb = 1024 * 1024
        print(f"slim: {before / mb:.0f} MB → {after / mb:.0f} MB")
