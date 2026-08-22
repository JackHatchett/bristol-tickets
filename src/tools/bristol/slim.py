#!/usr/bin/env python3
"""slim.py — leave a built bundle carrying only the Qt the board loads.

PySide6 ships every Qt module Qt has, and py2app copies the package whole, so an
untouched build carries a browser engine, a 3D renderer and three developer
tools to draw a Kanban board. This removes what the app never imports.

Usage:

    python3 slim.py <bundle.app>            # remove it
    python3 slim.py --report <bundle.app>   # say what would go, remove nothing

`setup.py` runs it at the end of a py2app build, so both build entry points ship
the same bundle.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# What the board imports. Every other PySide6 module goes.
MODULES = ("QtCore", "QtGui", "QtWidgets")

# The Qt frameworks those three load through on macOS. QtSvg and QtSvgWidgets
# carry the icon engine, QtNetwork and QtDBus are linked by the platform
# plugin, and QtPrintSupport is linked by QtWidgets.
FRAMEWORKS = MODULES + ("QtDBus", "QtNetwork", "QtPrintSupport",
                        "QtSvg", "QtSvgWidgets")

# The plugin folders a windowed widget app loads from.
PLUGINS = ("platforms", "styles", "imageformats", "iconengines", "tls",
           "generic")

# Whole folders under PySide6/ that serve development, QML or documentation.
DEV_DIRS = ("include", "glue", "typesystems", "examples", "scripts", "doc")
QT_DIRS = ("qml", "metatypes", "translations", "libexec", "doc", "include",
           "mkspecs", "modules")


def _pyside_root(bundle: Path) -> Path | None:
    matches = sorted(bundle.glob("Contents/Resources/lib/python*/PySide6"))
    return matches[0] if matches else None


def removals(bundle: Path) -> list[Path]:
    """Every path to remove, outermost first — a folder's children are not
    listed under it."""
    root = _pyside_root(bundle)
    if root is None:
        return []
    out: list[Path] = []

    for entry in sorted(root.iterdir()):
        name = entry.name
        if entry.is_dir():
            if name.endswith(".app") or name in DEV_DIRS:
                out.append(entry)
        elif name.endswith(".abi3.so"):
            if name.split(".")[0] not in MODULES:
                out.append(entry)
        elif name.endswith(".pyi") or name in ("assistant", "designer",
                                               "linguist", "lupdate",
                                               "lrelease", "qmlls",
                                               "qmlformat", "qmllint",
                                               "qmltestrunner", "balsam",
                                               "balsamui", "svgtoqml",
                                               "qsb", "pyside6-lupdate"):
            out.append(entry)

    qt = root / "Qt"
    for entry in sorted(qt.iterdir()) if qt.is_dir() else []:
        if entry.is_dir() and entry.name in QT_DIRS:
            out.append(entry)

    lib = qt / "lib"
    for entry in sorted(lib.iterdir()) if lib.is_dir() else []:
        if entry.name.endswith(".framework"):
            if entry.name[: -len(".framework")] not in FRAMEWORKS:
                out.append(entry)
        elif entry.is_file() and entry.name.startswith("libav"):
            out.append(entry)

    plugins = qt / "plugins"
    for entry in sorted(plugins.iterdir()) if plugins.is_dir() else []:
        if entry.is_dir() and entry.name not in PLUGINS:
            out.append(entry)

    return out


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def reseal(bundle: Path) -> None:
    """Sign the bundle again, ad hoc, after files have been taken out of it.

    py2app signs what it wrote, and every removal afterwards leaves a signature
    that no longer matches the bundle. macOS reads that as damaged rather than
    as merely unsigned: a download it moves to the trash without offering the
    Privacy and Security step an unsigned app gets. Signing again is what keeps
    the slimmed bundle in the openable case.
    """
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(bundle)],
                   check=True, capture_output=True)


def slim(bundle: Path, report_only: bool = False) -> tuple[int, int]:
    """Remove what the app never loads. Returns (bytes before, bytes after)."""
    before = _size(bundle)
    freed = 0
    for path in removals(bundle):
        freed += _size(path)
        if not report_only:
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    if not report_only:
        reseal(bundle)
    return before, before - freed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--report", action="store_true",
                        help="say what would go, remove nothing")
    args = parser.parse_args(argv)
    if not args.bundle.is_dir():
        raise SystemExit(f"no bundle at {args.bundle}")
    before, after = slim(args.bundle, report_only=args.report)
    mb = 1024 * 1024
    verb = "would leave" if args.report else "leaves"
    print(f"{before / mb:.0f} MB → {verb} {after / mb:.0f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
