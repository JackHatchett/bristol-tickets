#!/usr/bin/env python3
"""screen_compare.py — Bristol Tickets' screens against approved captures, pixel by pixel.

Builds the real window on the platform it runs on, on a seeded board and a
configuration of its own, in each theme and mode asked for. It grabs the Board
and Settings with ``QWidget.grab`` and compares each capture against the
approved one kept in qa_engineer's QA folder (``data/<instance>/qa/screens``).
Run on the Mac the app is used on, a capture has that machine's fonts and pixel
ratio; anywhere else it compares against captures made there.

    python3 screen_compare.py                          # every theme, light and dark
    python3 screen_compare.py --theme warm --mode dark
    python3 screen_compare.py approve                  # every capture that differed
    python3 screen_compare.py approve board-warm-dark  # one

A capture whose changed share of pixels is over ``THRESHOLD`` is reported with
its screen, theme, mode and share. Its fresh capture is kept beside the approved
one as ``<name>.new.png``, with ``<name>.diff.png`` showing the changed pixels
in red over a faded copy. ``approve`` makes a fresh capture the approved one.
When nothing differs the command prints one line saying so. Exit code 0 means
no capture differed.

The window never reads or writes the installation's configuration, so the
user's theme and mode are as he left them; the command checks that the file is
unchanged when it finishes.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from array import array
from pathlib import Path
from typing import TYPE_CHECKING

from qt_headless import PROJECT_ROOT, TOOLS, tool_on_path

if TYPE_CHECKING:
    from PySide6.QtGui import QImage

# The share of a capture's pixels that may differ before it is reported. A
# capture of an unchanged tree on one machine is identical, so any share above
# this is a change somebody made.
THRESHOLD = 0.0001

# The agent whose QA folder keeps the captures, and the folder inside it.
QA_AGENT = "qa_engineer"
SCREENS = "screens"

# The window's size for every capture, in device-independent pixels.
WINDOW_W = 1440
WINDOW_H = 900

SHOWN = ("board", "settings")
MODES = ("light", "dark")

# Painted over the faded fresh capture where a pixel changed.
DIFF_RED = 0xFFE5_3935


def screens_dir() -> Path:
    """The folder the approved captures live in, created on first use."""
    sys.path.insert(0, str(TOOLS / "config_tools"))
    import data_paths

    grants = data_paths.agent_data_paths(QA_AGENT, "write")
    if not grants:
        raise SystemExit(f"screen_compare: {QA_AGENT} declares no QA folder it may write")
    folder = grants[0] / SCREENS
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _seed(db: Path) -> None:
    """A board with something in every column and the pane, with fixed dates
    so nothing on screen moves between runs."""
    conn = sqlite3.connect(db)
    conn.executescript((TOOLS / "bristol" / "schema.sql").read_text())
    conn.execute(
        "INSERT INTO epic (name, type, status, owner) VALUES ('Upkeep','standing','active','user')"
    )
    conn.execute(
        "INSERT INTO epic (name, type, status, owner) "
        "VALUES ('Spring Release','project','active','user')"
    )
    cards = [
        ("Write the release notes", "todo", "max", "M", "build"),
        ("Check the install path on a clean Mac", "todo", "standard", "S", "build"),
        ("Search drops a result when the title has an accent", "todo", "standard", "S", "fix"),
        ("Draw criteria as a table in the detail pane", "doing", "max", "L", "build"),
        ("Rename the archive view", "done", "standard", "S", "build"),
    ]
    for order, (title, status, tier, size, kind) in enumerate(cards):
        conn.execute(
            "INSERT INTO task (epic_id, title, description, status, stage, sort_order, tier, "
            "estimate, record_type, assignee, reporter, created_at, updated_at, closed_at) "
            "VALUES (2, ?, ?, ?, 'active', ?, ?, ?, ?, 'user', 'user', "
            "'2026-01-05T10:00:00+00:00', '2026-01-05T10:00:00+00:00', ?)",
            (
                title,
                "Story:\nA card seeded for the screen comparison.",
                status,
                order,
                tier,
                size,
                kind,
                "2026-01-06T10:00:00+00:00" if status == "done" else None,
            ),
        )
    conn.commit()
    conn.close()


def _capture(sandbox: Path, theme: str, mode: str) -> dict:
    """Build the window in one theme and mode and grab the screens it shows."""
    import json

    import config_file
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    config = sandbox / "config.local.json"
    data = json.loads(config.read_text())
    data.setdefault("appearance", {}).update(
        {"theme": theme, "mode": mode, "detail_width": 520, "detail_collapsed": False}
    )
    config.write_text(json.dumps(data, indent=2) + "\n")
    config_file.path = lambda: config

    conn = sqlite3.connect(sandbox / "tickets.db")
    win = MainWindow(conn)
    # The pointer may rest over the window; it never reaches it, so no hover
    # state is captured.
    win.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
    win.setFixedSize(WINDOW_W, WINDOW_H)
    win.show()
    win.detail_pane.show_task(4)
    for _ in range(5):
        QApplication.processEvents()
    grabs = {"board": win.grab().toImage()}
    win.settings_btn.setChecked(True)
    win.settings_modal.show_tab("Sessions")
    for _ in range(5):
        QApplication.processEvents()
    grabs["settings"] = win.grab().toImage()
    win.settings_modal.close_modal()
    win.close()
    win.deleteLater()
    conn.close()
    for _ in range(3):
        QApplication.processEvents()
    return grabs


def _changed(fresh: QImage, approved: QImage) -> tuple[float, QImage | None]:
    """The share of pixels that differ, and an image of where, or None when
    the two are identical."""
    from PySide6.QtGui import QImage, QPainter

    fresh = fresh.convertToFormat(QImage.Format.Format_ARGB32)
    approved = approved.convertToFormat(QImage.Format.Format_ARGB32)
    if fresh.size() != approved.size():
        return 1.0, fresh
    a = bytes(fresh.constBits())
    b = bytes(approved.constBits())
    if a == b:
        return 0.0, None
    left, right = array("I", a), array("I", b)
    marks = array("I", (DIFF_RED if x != y else 0 for x, y in zip(left, right, strict=True)))
    count = sum(1 for m in marks if m)
    mask = QImage(
        marks.tobytes(), fresh.width(), fresh.height(), QImage.Format.Format_ARGB32
    ).copy()
    diff = QImage(fresh.size(), QImage.Format.Format_ARGB32)
    diff.setDevicePixelRatio(fresh.devicePixelRatio())
    painter = QPainter(diff)
    painter.fillRect(diff.rect(), 0xFFFFFFFF)
    painter.setOpacity(0.25)
    painter.drawImage(0, 0, fresh)
    painter.setOpacity(1.0)
    painter.drawImage(0, 0, mask)
    painter.end()
    return count / len(left), diff


def compare(themes: list[str], modes: list[str]) -> int:
    folder = screens_dir()
    real_config = PROJECT_ROOT / "config" / "config.local.json"
    real_before = real_config.read_bytes() if real_config.is_file() else None

    sandbox = folder / ".run"
    shutil.rmtree(sandbox, ignore_errors=True)
    sandbox.mkdir()
    shutil.copyfile(PROJECT_ROOT / "config" / "config.example.json", sandbox / "config.local.json")
    _seed(sandbox / "tickets.db")

    differed: list[str] = []
    unapproved: list[str] = []
    checked = 0
    try:
        for theme in themes:
            for mode in modes:
                for screen, image in _capture(sandbox, theme, mode).items():
                    name = f"{screen}-{theme}-{mode}"
                    approved_path = folder / f"{name}.png"
                    new_path = folder / f"{name}.new.png"
                    diff_path = folder / f"{name}.diff.png"
                    checked += 1
                    if not approved_path.is_file():
                        image.save(str(new_path))
                        unapproved.append(name)
                        continue
                    from PySide6.QtGui import QImage

                    share, diff = _changed(image, QImage(str(approved_path)))
                    if share > THRESHOLD and diff is not None:
                        image.save(str(new_path))
                        diff.save(str(diff_path))
                        differed.append(name)
                        print(
                            f"DIFFERS  {screen} in {theme} {mode}: {share:.2%} of pixels changed "
                            f"-> {diff_path.name}"
                        )
                    else:
                        new_path.unlink(missing_ok=True)
                        diff_path.unlink(missing_ok=True)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    real_after = real_config.read_bytes() if real_config.is_file() else None
    if real_after != real_before:
        print("FAILED   the run changed the installation's config/config.local.json")
        return 2
    for name in unapproved:
        print(f"NEW      {name} has no approved capture; {name}.new.png is waiting for approve")
    if not differed and not unapproved:
        print(f"No differences: {checked} captures match their approved captures in {folder}")
    return 1 if differed or unapproved else 0


def approve(names: list[str]) -> int:
    folder = screens_dir()
    waiting = sorted(p.name[: -len(".new.png")] for p in folder.glob("*.new.png"))
    chosen = names or waiting
    missing = [n for n in chosen if n not in waiting]
    if missing:
        print(f"No fresh capture waits for: {', '.join(missing)}")
        return 2
    for name in chosen:
        (folder / f"{name}.new.png").replace(folder / f"{name}.png")
        (folder / f"{name}.diff.png").unlink(missing_ok=True)
        print(f"APPROVED {name}")
    if not chosen:
        print("No fresh capture is waiting to be approved")
    return 0


def main() -> None:
    tool_on_path("bristol")
    from ui.themes import THEMES

    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("action", nargs="?", default="compare", choices=("compare", "approve"))
    ap.add_argument("names", nargs="*", help="for approve: the captures to approve (default all)")
    ap.add_argument("--theme", action="append", choices=sorted(THEMES), help="default: every one")
    ap.add_argument("--mode", action="append", choices=MODES, help="default: light and dark")
    args = ap.parse_args()

    if args.action == "approve":
        sys.exit(approve(args.names))

    from PySide6.QtWidgets import QApplication
    from ui.theme import install_typeface

    app = QApplication.instance() or QApplication([])
    install_typeface(app)
    sys.exit(compare(args.theme or list(THEMES), args.mode or list(MODES)))


if __name__ == "__main__":
    main()
