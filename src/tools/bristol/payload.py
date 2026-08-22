"""payload.py — the copy of Bristol carried inside a built .app.

A downloaded ``BristolTickets.app`` is the whole system, not just the viewer:
``setup.py`` stages the project's published files into the bundle's Resources,
and this module is what puts them on disk in the folder the user chooses and
brings them up to date when a newer app opens an older installation.

Bristol Tickets imports nothing from the rest of ``src/tools/``, and this holds
to that: the standard library only.

**Configuration and data are never written by an update.** ``PUBLISHED_DIRS``
and ``PUBLISHED_FILES`` name what ships; ``config/config.local.json`` and
``data/`` appear in neither, so an installed board survives every refresh.

GitHub-safe: contains no personal path.
"""

from __future__ import annotations

import shutil
from pathlib import Path

PAYLOAD_DIR_NAME = "payload"

# What a release carries: the machinery and the manual, and no instance of it.
PUBLISHED_DIRS = ("src", "docs")
PUBLISHED_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "requirements.in",
    "requirements.txt",
    "requirements-tools.txt",
    "config/config.example.json",
)

# Build leavings and caches that live under src/ but belong to nobody's install.
EXCLUDED = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "*.pyo", "build", "dist", ".eggs", ".DS_Store",
    "*.local", "tickets_db.local",
)


def version(root: Path) -> str | None:
    """The release a project tree declares, or None if it declares none."""
    try:
        text = (root / "src" / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def bundled() -> Path | None:
    """The payload inside the running .app, or None when there is not one.

    True of a py2app build with a staged payload, false of a source run, so a
    caller can ask "am I a downloaded app?" without inspecting the bundle.
    """
    for parent in Path(__file__).resolve().parents:
        if parent.name == "Resources" and parent.parent.name == "Contents":
            candidate = parent / PAYLOAD_DIR_NAME
            return candidate if (candidate / "src" / "app.md").is_file() else None
    return None


def schema_path(start: Path | None = None) -> Path | None:
    """The schema a fresh board is provisioned from, or None where it is
    absent.

    Searched upward from ``start`` (this module by default), because the two
    layouts put it at different depths.
    // A build lands the ui package under Resources/lib/pythonX.Y/ and a data
    // file at Resources/, so no single relative step finds both.
    """
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        candidate = parent / "schema.sql"
        if candidate.is_file():
            return candidate
    return None


def stage(source: Path, target: Path) -> Path:
    """Copy a project tree's published files into ``target``, replacing what is
    already there. Used to build a payload and to install one.

    Only the published names are touched, so a target already holding an
    installation keeps its ``config/config.local.json`` and its ``data/``.
    """
    target.mkdir(parents=True, exist_ok=True)
    for name in PUBLISHED_DIRS:
        src = source / name
        if not src.is_dir():
            continue
        dest = target / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=EXCLUDED)
    for name in PUBLISHED_FILES:
        src = source / name
        if not src.is_file():
            continue
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return target


def unstage(target: Path) -> None:
    """Undo a `stage` into a folder nothing else has used yet.

    Removes the published names and then the folder itself if that emptied it,
    so a setup run abandoned after the tree was placed leaves nothing behind. A
    folder holding anything unpublished — a board, a configuration, a file the
    user put there — survives as it stands.
    """
    for name in PUBLISHED_DIRS:
        shutil.rmtree(target / name, ignore_errors=True)
    for name in PUBLISHED_FILES:
        try:
            (target / name).unlink()
        except OSError:
            pass
        parent = (target / name).parent
        if parent != target and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
    try:
        if not any(target.iterdir()):
            target.rmdir()
    except OSError:
        pass


def installed_at(target: Path) -> bool:
    """True when ``target`` already holds a Bristol project tree."""
    return (target / "src" / "app.md").is_file()


def refresh(target: Path) -> str | None:
    """Bring an installation up to the running app's release.

    Returns the version installed when files were replaced, and None when the
    app carries no payload, the target is not an installation, or it is already
    current. Configuration and data are not among the published names, so
    neither is read or written here.
    """
    source = bundled()
    if source is None or not installed_at(target):
        return None
    incoming = version(source)
    if incoming is None or incoming == version(target):
        return None
    stage(source, target)
    return incoming
