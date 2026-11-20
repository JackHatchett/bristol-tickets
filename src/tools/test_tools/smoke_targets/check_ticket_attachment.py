"""smoke_targets/check_ticket_attachment.py — the `ticket_attachment` smoke target, run by smoke.py."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

from qt_headless import TOOLS
from smoke_targets.failure import SmokeFailure


def check_ticket_attachment() -> list[str]:
    """An agent attaches an image to a card from the command line, and it is
    stored as the viewer stores one: copied into the board's images folder
    under the viewer's name pattern, with a row naming it.

    No Qt: the CLI and attachment_store are plain sqlite3 and shutil.
    """

    ok: list[str] = []
    tools = TOOLS / "ticket_tools"
    sys.path.insert(0, str(tools))
    import create_tickets
    import ticket_write

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "tickets.db"
        create_tickets.provision(db)
        image = Path(tmp) / "screen shot.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nsmoke")

        original = ticket_write.resolve_db_path
        ticket_write.resolve_db_path = lambda: db
        argv = sys.argv
        try:

            def run(*args):
                sys.argv = ["ticket_write.py", *args]
                ticket_write.main()

            run("add-task", "--title", "pictured", "--assignee", "chief_of_staff")
            run("add-attachment", "--task", "1", "--file", str(image), "--author", "chief_of_staff")
        finally:
            sys.argv = argv
            ticket_write.resolve_db_path = original

        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT task_id, filename, original_name FROM attachment").fetchall()
        conn.close()
        if len(rows) != 1 or rows[0][0] != 1 or rows[0][2] != image.name:
            raise SmokeFailure(f"add-attachment recorded {rows}")
        stored = Path(tmp) / "images" / rows[0][1]
        if not stored.is_file() or stored.read_bytes() != image.read_bytes():
            raise SmokeFailure(f"add-attachment did not copy the file to {stored}")
        if not rows[0][1].startswith("task1_") or not image.is_file():
            raise SmokeFailure(f"the stored name or the original is wrong: {rows[0][1]}")
        ok.append(
            "add-attachment copies the image beside the board under the "
            "viewer's name and records it, leaving the original"
        )

        store = (tools.parent / "bristol" / "attachment_store.py").read_text()
        if "PySide6" in store:
            raise SmokeFailure("attachment_store imports Qt")
        ok.append("the store the viewer and the CLI share imports no Qt")
    return ok
