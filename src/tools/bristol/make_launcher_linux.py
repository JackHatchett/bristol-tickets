#!/usr/bin/env python3
"""make_launcher_linux.py — put Bristol Tickets in the Linux application menu.

The Linux counterpart of ``make_launcher.py``. It writes one desktop entry — the
small text file a Linux desktop reads to list an application — whose command
runs this repo's ``app.py``. Run it once and Bristol Tickets appears in the
application menu under its own name and icon; run it again after moving or
renaming the repo, or after switching to a different Python, and the entry is
repointed.

The entry holds absolute paths, so it is a per-machine artifact and is never
committed; it lives in the user's own applications folder, outside the repo.

Usage:
    python3 src/tools/bristol/make_launcher_linux.py            # write/repair it
    python3 src/tools/bristol/make_launcher_linux.py --where    # print its location
    python3 src/tools/bristol/make_launcher_linux.py --remove   # delete it

Bristol Tickets is self-contained: this imports nothing from the rest of
``src/tools/``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ENTRY_NAME = "bristol-tickets.desktop"
DISPLAY_NAME = "Bristol Tickets"
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]          # src/tools/bristol -> src/tools -> src -> repo


def entry_path() -> Path:
    """Where the desktop entry lives: the user's own applications folder."""
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "applications" / ENTRY_NAME


def find_python() -> str:
    """The interpreter that actually has PySide6."""
    candidates = [sys.executable]
    which = shutil.which("python3")
    if which:
        candidates.append(which)
    for exe in candidates:
        if not exe:
            continue
        try:
            subprocess.run([exe, "-c", "import PySide6"], check=True,
                           capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            continue
        return exe
    sys.exit(
        "make_launcher_linux: ERROR — no Python on this machine has PySide6.\n"
        "  Install it: pip install -r requirements.txt"
    )


def quoted(argument: str) -> str:
    """One argument of the entry's command, quoted as the desktop entry format
    requires: wrapped in double quotes, with the four characters the format
    reserves inside them escaped. A path holding a space survives it."""
    for reserved in ("\\", '"', "`", "$"):
        argument = argument.replace(reserved, "\\" + reserved)
    # A literal percent sign is doubled, because a single one starts a field
    # code such as %f.
    return '"' + argument.replace("%", "%%") + '"'


def entry_text(python_exe: str) -> str:
    """The desktop entry, complete."""
    app = HERE / "app.py"
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={DISPLAY_NAME}",
        "Comment=A Kanban board you share with AI agents",
        f"Exec={quoted(python_exe)} {quoted(str(app))}",
        f"Path={REPO_ROOT}",
        "Terminal=false",
        "Categories=Office;ProjectManagement;",
    ]
    icon = HERE / "icon.png"
    if icon.exists():
        lines.append(f"Icon={icon}")
    return "\n".join(lines) + "\n"


def build() -> Path:
    """Write the entry, replacing any existing one."""
    target = entry_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(entry_text(find_python()), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--where", action="store_true",
                        help="print where the entry lives and exit")
    parser.add_argument("--remove", action="store_true",
                        help="delete the entry and exit")
    args = parser.parse_args()

    if args.where:
        print(entry_path())
        return

    if args.remove:
        entry_path().unlink(missing_ok=True)
        print(f"OK: removed {entry_path()}")
        return

    if not sys.platform.startswith("linux"):
        sys.exit("make_launcher_linux: ERROR — a desktop entry is a Linux "
                 "artifact. On macOS, run make_launcher.py.")

    target = build()
    print(f"OK: {target}")
    print(f"    runs: {HERE / 'app.py'}")
    print(f"    {DISPLAY_NAME} is in the application menu. If it is not there "
          "yet, log out and back in.")


if __name__ == "__main__":
    main()
