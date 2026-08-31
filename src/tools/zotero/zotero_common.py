#!/usr/bin/env python3
"""
zotero_common.py — shared data layer for writing into a local Zotero library.

Zotero exposes no local write API, so these tools write zotero.sqlite directly.
That is safe only when Zotero is not running: Zotero holds the database open and
keeps unflushed state in memory, so a write behind its back is silently lost or
corrupted. Every writer here refuses to run while Zotero is up.

Path resolution (no hardcoded user paths in /src):
  - ZOTERO_DATA_DIR : absolute path to the Zotero data directory (contains
                      zotero.sqlite). Resolved from config/config.local.json's
                      `zotero.env` block, or the ZOTERO_DATA_DIR env var.
    Falls back to ~/Zotero, which is Zotero's own default.

Sync model: rows written here carry version=0, synced=0 — exactly what Zotero
records for a local edit it has not yet pushed. The next sync uploads them.
Never invent a version number; that is the server's to assign.
"""

import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Zotero's key alphabet: base32 minus the letters that read as digits.
KEY_ALPHABET = "23456789ABCDEFGHIJKLMNPQRSTUVWXYZ"
USER_LIBRARY_ID = 1


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


def _config() -> dict:
    path = _project_root() / "config" / "config.local.json"
    if not path.exists():
        return {}
    with path.open() as fh:
        return json.load(fh)


def data_dir() -> Path:
    """Absolute path to the Zotero data directory."""
    env = os.environ.get("ZOTERO_DATA_DIR")
    if not env:
        env = _config().get("zotero", {}).get("env", {}).get("ZOTERO_DATA_DIR")
    if not env:
        env = str(Path.home() / "Zotero")
    return Path(env).expanduser()


def db_path() -> Path:
    return data_dir() / "zotero.sqlite"


def zotero_is_running() -> bool:
    """True if Zotero holds the library open.

    The signal is the file rather than the process, because a shell that is not
    the machine's own shell reads a process table the desktop is not in, and
    answers "no Zotero" whatever Zotero is doing. The database and the files
    beside it are on the real disk and are read the same way from anywhere.
    """
    # // Zotero keeps the library in PERSIST journal mode, so
    # // zotero.sqlite-journal exists for as long as Zotero holds the database
    # // and goes when it closes. Its header is zeroed between transactions,
    # // which is a committed journal rather than a stale file.
    if (data_dir() / "zotero.sqlite-journal").exists():
        return True
    try:
        out = subprocess.run(
            ["pgrep", "-x", "zotero"], capture_output=True, text=True, timeout=10
        )
        return out.returncode == 0 and bool(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def require_zotero_closed() -> None:
    if zotero_is_running():
        sys.exit(
            "Zotero is running. Quit Zotero (Cmd-Q) and run this again — writing "
            "to zotero.sqlite behind a live Zotero loses the write."
        )


def connect(read_only: bool = False) -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        sys.exit(f"No Zotero database at {path}. Set ZOTERO_DATA_DIR.")
    if read_only:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        require_zotero_closed()
        conn = sqlite3.connect(str(path))
        # Avoid an on-disk rollback journal on a mounted volume; same reasoning
        # as personal_db.db_common.
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def now_utc() -> str:
    """Zotero's timestamp format: 'YYYY-MM-DD HH:MM:SS' in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def new_key(conn: sqlite3.Connection, taken: set) -> str:
    """An 8-character Zotero object key not already used by an item or collection."""
    while True:
        key = "".join(random.choice(KEY_ALPHABET) for _ in range(8))
        if key in taken:
            continue
        taken.add(key)
        return key


def existing_keys(conn: sqlite3.Connection) -> set:
    keys = {r[0] for r in conn.execute("SELECT key FROM items")}
    keys |= {r[0] for r in conn.execute("SELECT key FROM collections")}
    return keys


def field_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT fieldID FROM fields WHERE fieldName=?", (name,)).fetchone()
    if row is None:
        raise KeyError(f"Zotero has no field named {name!r}")
    return row[0]


def item_type_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute(
        "SELECT itemTypeID FROM itemTypes WHERE typeName=?", (name,)
    ).fetchone()
    if row is None:
        raise KeyError(f"Zotero has no item type named {name!r}")
    return row[0]


def creator_type_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute(
        "SELECT creatorTypeID FROM creatorTypes WHERE creatorType=?", (name,)
    ).fetchone()
    if row is None:
        raise KeyError(f"Zotero has no creator type named {name!r}")
    return row[0]


def value_id(conn: sqlite3.Connection, value: str) -> int:
    """The itemDataValues id for a string, inserting it if new."""
    row = conn.execute(
        "SELECT valueID FROM itemDataValues WHERE value=?", (value,)
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute("INSERT INTO itemDataValues (value) VALUES (?)", (value,))
    return cur.lastrowid


def creator_id(conn: sqlite3.Connection, first: str, last: str, field_mode: int) -> int:
    """The creators id for a name, inserting it if new."""
    row = conn.execute(
        "SELECT creatorID FROM creators WHERE firstName=? AND lastName=? AND fieldMode=?",
        (first, last, field_mode),
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO creators (firstName, lastName, fieldMode) VALUES (?,?,?)",
        (first, last, field_mode),
    )
    return cur.lastrowid


def backup_to_scratch(scratch: Path) -> Path:
    """Copy the live database into a scratch directory that is not the user's.

    This is a within-run rollback point, never a file left on the user's machine.
    Callers delete it on success.
    """
    scratch.mkdir(parents=True, exist_ok=True)
    dest = scratch / f"zotero.sqlite.{int(time.time())}"
    shutil.copy2(db_path(), dest)
    return dest
