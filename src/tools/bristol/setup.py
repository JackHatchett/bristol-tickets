"""setup.py — build a standalone macOS .app for Bristol with py2app.

Usage (see BUILD_APP.md for the full walkthrough):

    pip install py2app PySide6
    python3 setup.py py2app          # → dist/Bristol.app

This file is GitHub-safe: it hardcodes no personal path. The built app locates
the database via `tickets_db.local` (git-ignored) or the TICKETS_DB env var —
see app.py `_resolve_db_path`. Put an `icon.icns` next to this file to give the
app a custom icon (optional; the OPTIONS block picks it up only if present).
"""

from pathlib import Path

from setuptools import setup

HERE = Path(__file__).resolve().parent

APP = ["app.py"]

# Files copied into the bundle's Resources. schema.sql must ship so a fresh DB
# can be provisioned; tickets_db.local ships (if present) so the relocated app
# can find the database, and bristol_reports.local likewise tells it where the
# notebook is (the bundle cannot see the repo's config/). Added only if present.
DATA_FILES = [
    f for f in ("schema.sql", "tickets_db.local", "bristol_reports.local")
    if (HERE / f).exists()
]

OPTIONS = {
    "argv_emulation": False,
    # Bundle the ui/ and reports/ packages (py2app's import scanner can miss
    # relative-imported submodules, and reports/ is only reached through a
    # guarded import inside Clear Done, so name both explicitly).
    "packages": ["ui", "reports"],
    "includes": ["sqlite3"],
    "plist": {
        "CFBundleName": "Bristol",
        "CFBundleDisplayName": "Bristol",
        "CFBundleIdentifier": "local.bristol.app",
        "CFBundleVersion": "18.0",
        "CFBundleShortVersionString": "18.0",
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
