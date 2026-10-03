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

import importlib.util
import shutil
import subprocess
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

EXCLUDES = ["tkinter", "setuptools", "pip", "pkg_resources", "py2app",
            "pydoc_data", "test"]

# Standard-library modules no scanner and no tool of Bristol's reaches for:
# windows, demos, an editor, and the installer bootstrap.
STDLIB_LEFT_OUT = {"turtle", "turtledemo", "idlelib", "ensurepip", "venv",
                   "antigravity", "this", "lib2to3", "distutils", "_tkinter"}


def standard_library() -> tuple[list[str], list[str]]:
    """Every standard-library package and module this interpreter has, as
    py2app's (packages, includes).

    py2app keeps only what the app itself imports. The scanners the bundle
    carries run from a folder py2app never reads, so their imports are
    invisible to it, and a module they need and the app does not would be
    missing. The whole library ships instead, which is what any scanner
    version may reach for.
    """
    packages, modules = [], []
    for name in sorted(sys.stdlib_module_names):
        if name in STDLIB_LEFT_OUT or name in EXCLUDES:
            continue
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            continue
        if spec is None or spec.origin in (None, "built-in", "frozen"):
            continue
        (packages if spec.submodule_search_locations else modules).append(name)
    return packages, modules


STDLIB_PACKAGES, STDLIB_MODULES = standard_library()

# Where the bundle carries the scanners, beside its own library. The path is
# src/tools/skill_tools/skills.py CARRIED_SCANNERS, which is what finds them.
SCANNERS_IN_BUNDLE = Path("Contents") / "Resources" / "scanners"


def carry_scanners(bundle: Path) -> None:
    """Install the scanners scanners.txt names into the bundle, where the
    app's interpreter finds them on an import."""
    target = bundle / SCANNERS_IN_BUNDLE
    if target.exists():
        shutil.rmtree(target)
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                    "--disable-pip-version-check", "--target", str(target),
                    "-r", str(HERE / "scanners.txt")], check=True)
    # The launchers pip writes name this build machine's interpreter, which a
    # downloaded app does not have; skills.py starts each scanner itself.
    launchers = target / "bin"
    if launchers.is_dir():
        shutil.rmtree(launchers)


OPTIONS = {
    "argv_emulation": False,
    # Bundle the ui/ and reports/ packages, named explicitly: reports/ is
    # reached only through a guarded import inside the epic closure.
    "packages": ["ui", "reports", *STDLIB_PACKAGES],
    # epic_closure is reached the same guarded way, from the epic dialog, so
    # nothing in the import graph would carry it in on its own. finishing is
    # imported outright by three ui modules and named here beside it.
    "includes": ["sqlite3", "epic_closure", "finishing", *STDLIB_MODULES],
    # A board draws no Tk windows and installs no packages at runtime.
    "excludes": EXCLUDES,
    "plist": {
        # CFBundleName holds no space; CFBundleDisplayName carries the name
        # with one.
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

# The bundle is slimmed to what the app imports once the build has written it.
if "py2app" in sys.argv:
    import slim  # noqa: E402  (bristol-local; owns what a bundle keeps)

    bundle = HERE / "dist" / "BristolTickets.app"
    if bundle.is_dir():
        # Before the slim, whose last act signs the bundle again.
        carry_scanners(bundle)
        before, after = slim.slim(bundle)
        mb = 1024 * 1024
        print(f"slim: {before / mb:.0f} MB → {after / mb:.0f} MB")
