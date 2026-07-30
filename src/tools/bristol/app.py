"""app.py — launch the Bristol GUI.

The DB path follows the canonical resolution order documented in
``src/tools/config_tools/instance_pointer.py``: TICKETS_DB env var, then the
per-machine instance pointer, then the legacy ``tickets_db.local`` file, then
relative discovery from the source tree.

This tool is mechanism-only: it launches the PySide6 GUI for a tickets DB.
It contains no agent-specific logic, no personal paths, and no complex provisioning.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instance  # noqa: E402  (bristol-local; see module docstring)



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
    """Resolve the tickets DB path.

    Order per ``config_tools/instance_pointer.py``. Steps 2 and 3 exist because
    step 4 only succeeds while app.py still sits above the repo's data/ folder,
    which is not the case inside a built .app.
    """

    # 1. Explicit DB path via TICKETS_DB env var (testing/overrides).
    env_db = os.environ.get("TICKETS_DB")
    if env_db:
        return Path(os.path.expanduser(env_db))

    # 2. The per-machine instance pointer.
    data_root = instance.get_path("data_root")
    slug = instance.read().get("instance_slug")
    if data_root and slug:
        candidate = data_root / slug / "tickets" / "tickets.db"
        if candidate.exists():
            return candidate
    if data_root:
        matches = sorted(data_root.glob("*/tickets/tickets.db"))
        if matches:
            return matches[0]

    # 3. Legacy: a git-ignored one-line file next to app.py holding an
    #    absolute path, bundled into older .app builds.
    local_pointer = Path(__file__).resolve().parent / "tickets_db.local"
    if local_pointer.exists():
        text = local_pointer.read_text().strip()
        if text:
            return Path(os.path.expanduser(text))

    # 4. Relative discovery — works when run in-place from the repo.
    data_dir = _project_root() / "data"
    if data_dir.exists():
        matches = sorted(data_dir.glob("*/tickets/tickets.db"))
        if matches:
            return matches[0]

    # Nothing resolved: name where a fresh instance would go.
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