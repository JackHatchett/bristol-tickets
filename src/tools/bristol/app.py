"""app.py — launch the Bristol GUI.

DB path resolution (highest to lowest priority):
  1. TICKETS_DB env var — explicit full path to the .db file (for testing/overrides).
  2. Dynamic relative discovery — steps up to the project root and searches /data 
     for the instance tickets.db without hardcoding user identifiers.

This tool is mechanism-only: it launches the PySide6 GUI for a tickets DB.
It contains no agent-specific logic, no personal paths, and no complex provisioning.
"""

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


def _resolve_db_path() -> Path:
    """Resolve the tickets DB path dynamically.

    Priority order (highest first). The `.local` file is what makes a relocated
    py2app bundle work: relative discovery (step 3) only succeeds when app.py is
    still sitting above the repo's data/ folder, which is NOT the case inside a
    built .app. So the bundle is told the absolute path via a git-ignored
    `tickets_db.local` file that is bundled at build time — keeping the personal
    path out of version control while still letting the double-clickable app
    find the database.
    """

    # 1. Explicit DB path via TICKETS_DB env var (testing/overrides).
    env_db = os.environ.get("TICKETS_DB")
    if env_db:
        return Path(os.path.expanduser(env_db))

    # 2. A git-ignored one-line file next to app.py holding an absolute path.
    #    Create it once (see BUILD_APP.md) before building the .app.
    local_pointer = Path(__file__).resolve().parent / "tickets_db.local"
    if local_pointer.exists():
        text = local_pointer.read_text().strip()
        if text:
            return Path(os.path.expanduser(text))

    # 3. Relative discovery — works when run in-place from the repo.
    data_dir = _project_root() / "data"

    # Search for the tickets.db dynamically to avoid hardcoding an instance slug
    if data_dir.exists():
        matches = list(data_dir.glob("*/tickets/tickets.db"))
        if matches:
            return matches[0]

    # 4. Fallback for fresh provisioning if the db does not exist yet.
    user_slug = os.environ.get("AGENT_INSTANCE_SLUG", "default_user")
    return data_dir / user_slug / "tickets" / "tickets.db"


def main() -> None:
    # Make this script's own directory importable regardless of the current
    # working directory (needed when launched by double-click or from a
    # py2app bundle, not just `cd`-ed into the folder). The `ui` package is
    # then imported as a top-level package with working relative imports.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import sqlite3
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
        from ui.main_window import MainWindow
    except ImportError as exc:
        sys.exit(
            f"app: missing dependency — {exc}. "
            "Install PySide6: pip3 install PySide6 --break-system-packages"
        )

    db_path = _resolve_db_path()
    
    # Ensure the target directory structure exists before attempting connection
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)

    # Ensure schema is up to date if a schema file is present alongside app.py
    schema = Path(__file__).parent / "schema.sql"
    if schema.exists():
        conn.executescript(schema.read_text())
        conn.commit()

    app = QApplication(sys.argv)
    app.setApplicationName("Bristol")
    app.setApplicationDisplayName("Bristol")
    # Set the app-wide icon so the Dock/taskbar shows it when Bristol is
    # launched as a script (the built .app uses setup.py's iconfile instead).
    icon_file = Path(__file__).resolve().parent / "icon.png"
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))

    window = MainWindow(conn, initial_db=db_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()