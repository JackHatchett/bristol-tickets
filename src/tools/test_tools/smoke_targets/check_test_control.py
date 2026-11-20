"""smoke_targets/check_test_control.py — the `test_control` smoke target, run by smoke.py."""

from __future__ import annotations

import sqlite3

from qt_headless import offscreen_app, tool_on_path


def check_test_control() -> list[str]:
    ok: list[str] = []
    tool_on_path("test_control")
    offscreen_app()

    import app as tc_app  # test_control/app.py

    conn = sqlite3.connect(":memory:")
    tc_app._provision_schema(conn, is_fresh=True)
    ok.append("schema provisions + seeds on a fresh DB")

    from ui.main_window import TestControlWindow

    # The window is kept for the life of the process, as the running tool
    # keeps it.
    global _test_control_window
    _test_control_window = TestControlWindow(conn)
    ok.append("TestControlWindow builds against the seeded DB")
    return ok
