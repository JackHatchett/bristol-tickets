#!/usr/bin/env python3
"""app.py — launch the Test Control desktop QA tool.

Manual test-case management: draft blueprint test cases (Master Templates),
clone them into independent runnable session ledgers, mark steps pass/fail,
and capture defect notes. Layout mirrors bristol (app.py + ui/) for
regularity across the tools/ folder.

DB path resolution (mirrors bristol/app.py and roadmap_tools' own
canonical discovery rule — see src/tools/roadmap_tools/README.md):
    1. TEST_CONTROL_DB env var — explicit full path override (testing).
    2. Discover the active instance dir the same way roadmap_tools does
       (the parent of data/*/roadmap/roadmap.db), then use
       data/<instance>/test_control/test_control.db.
    3. Fallback if no roadmap.db exists yet: first existing data/<instance>/
       dir, else data/<AGENT_INSTANCE_SLUG or "default_user">/.

No personal paths or usernames are hardcoded — same invariant as
roadmap_tools (see its README, item 1).
"""

import os
import sys
import sqlite3
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


# ---------------------------------------------------------------------------
# DB PATH RESOLUTION (mirrors roadmap_tools' canonical rule)
# ---------------------------------------------------------------------------

def _resolve_db_path() -> Path:
    env_db = os.environ.get("TEST_CONTROL_DB")
    if env_db:
        return Path(os.path.expanduser(env_db))

    data_root = _project_root() / "data"

    instance_dir = None
    if data_root.exists():
        roadmap_matches = list(data_root.glob("*/roadmap/roadmap.db"))
        if roadmap_matches:
            instance_dir = roadmap_matches[0].parent.parent  # data/<instance>
        else:
            existing = sorted(p for p in data_root.iterdir() if p.is_dir())
            if existing:
                instance_dir = existing[0]

    if instance_dir is None:
        user_slug = os.environ.get("AGENT_INSTANCE_SLUG", "default_user")
        instance_dir = data_root / user_slug

    return instance_dir / "test_control" / "test_control.db"


# ---------------------------------------------------------------------------
# SCHEMA + SEED PROVISIONING
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS control_milestone (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    due_date TEXT
);
CREATE TABLE IF NOT EXISTS control_suite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);
CREATE TABLE IF NOT EXISTS control_case (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suite_id INTEGER NOT NULL,
    section TEXT NOT NULL DEFAULT 'General',
    title TEXT NOT NULL,
    preconditions TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium',
    FOREIGN KEY (suite_id) REFERENCES control_suite(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS control_case_step (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    instruction TEXT NOT NULL,
    expected_result TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES control_case(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS control_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    milestone_id INTEGER,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'utc')),
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (milestone_id) REFERENCES control_milestone(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS control_run_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    case_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'untested',
    notes TEXT,
    last_updated_at TEXT,
    FOREIGN KEY (run_id) REFERENCES control_run(id) ON DELETE CASCADE,
    FOREIGN KEY (case_id) REFERENCES control_case(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS control_run_step_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_item_id INTEGER NOT NULL,
    step_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'untested',
    FOREIGN KEY (run_item_id) REFERENCES control_run_item(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES control_case_step(id) ON DELETE CASCADE
);
"""

DEFAULT_CASES = [
    ("General", "App launches and connects to its database",
     "Verify the app opens cleanly and the SQLite connection is live.",
     "Clean config, no stale lock files."),
    ("General", "Session data persists across restarts",
     "Verify pass/fail status and notes survive an app restart.",
     "At least one cloned session exists."),
]


def _provision_schema(conn: sqlite3.Connection, is_fresh: bool) -> None:
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)
    conn.commit()

    if not is_fresh:
        return

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO control_suite (name, description) VALUES (?, ?)",
        ("Core Interface Verification", "Desktop application validation checks."),
    )
    suite_id = cur.lastrowid

    cur.execute(
        "INSERT INTO control_milestone (name, due_date) VALUES (?, ?)",
        ("v1.0.0 Alpha", "2026-12-31"),
    )
    milestone_id = cur.lastrowid

    cur.execute(
        "INSERT INTO control_run (milestone_id, name) VALUES (?, ?)",
        (milestone_id, "Initial smoke-test run"),
    )
    run_id = cur.lastrowid

    for section, title, instruction, preconditions in DEFAULT_CASES:
        cur.execute(
            "INSERT INTO control_case (suite_id, section, title, preconditions) "
            "VALUES (?, ?, ?, ?)",
            (suite_id, section, title, preconditions),
        )
        case_id = cur.lastrowid

        cur.execute(
            "INSERT INTO control_case_step (case_id, step_number, instruction, expected_result) "
            "VALUES (?, 1, ?, ?)",
            (case_id, instruction, "Behaves as described with no errors."),
        )

        cur.execute(
            "INSERT INTO control_run_item (run_id, case_id, status) VALUES (?, ?, 'untested')",
            (run_id, case_id),
        )
        run_item_id = cur.lastrowid

        for (step_id,) in cur.execute(
            "SELECT id FROM control_case_step WHERE case_id = ?", (case_id,)
        ).fetchall():
            cur.execute(
                "INSERT INTO control_run_step_item (run_item_id, step_id, status) "
                "VALUES (?, ?, 'untested')",
                (run_item_id, step_id),
            )

    conn.commit()


def setup_and_provision_workspace() -> sqlite3.Connection:
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    is_fresh_db = not db_path.exists()
    conn = sqlite3.connect(db_path)
    _provision_schema(conn, is_fresh_db)
    return conn


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    script_directory = Path(__file__).resolve().parent
    if str(script_directory) not in sys.path:
        sys.path.insert(0, str(script_directory))

    connection_instance = setup_and_provision_workspace()

    try:
        from PySide6.QtWidgets import QApplication
        from ui.main_window import TestControlWindow
    except ImportError as exc:
        sys.exit(
            f"app: missing dependency — {exc}. "
            "Install PySide6: pip3 install PySide6 --break-system-packages"
        )

    app = QApplication(sys.argv)
    dashboard = TestControlWindow(connection_instance)
    dashboard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
