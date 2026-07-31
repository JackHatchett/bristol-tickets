#!/usr/bin/env python3
"""
db_common.py — shared data layer for the unified personal database.

Every personal_db tool imports these helpers so path discovery, write-safety,
and the Mac-mount read/write-back workaround live in exactly one place.

Path resolution (no hardcoded user paths in /src — invariant shared with
tools/zotero and tools/ticket_tools):
  - PERSONAL_DB_DIR       : absolute path to the personal-db data root
                            (contains db/ and data/). Resolved from
                            config/config.local.json's `personal_db` block.
  - PERSONAL_DB_FILENAME  : db filename (default 'personal.db')
  - PERSONAL_SNAPSHOT_BASE: base dir for the per-domain snapshot folders
                            (default: <root>/../system/logs; each domain writes
                            to <base>/<subdir>/, e.g. library_snapshots/)

If PERSONAL_DB_DIR is unset, falls back to canonical discovery: the first
match of data/*/personal/ walking up from this file's location — mirroring the
tickets/library "first glob match, one instance" convention. When nothing
matches — a fresh clone, whose data tree does not exist yet — the root resolves
to <data root>/<instance>/personal and is created the first time something
writes there.

First access provisions: connect() creates the db/ folder and applies
schema.sql when personal.db is absent, so a new install gets an empty database
rather than a missing-path error. It creates the container only — no rows are
seeded.

Write safety: connect() sets PRAGMA journal_mode=MEMORY to avoid the on-disk
rollback journal that once wedged a mounted-folder DB (see
tools/ticket_tools/README.md §3b). Writers that must be extra safe can use
with_writeback(), which edits a /tmp copy and copies it back atomically.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "config_tools")
)
import data_paths  # noqa: E402  (the shared declared-path resolver)

DEFAULT_DB_FILENAME = "personal.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def resolve_root() -> Path:
    """The personal-db data root (folder containing db/ and data/).

    PERSONAL_DB_DIR, then the first data/*/personal match, then the path a
    fresh install would use. Resolving never creates anything; the writers
    below do that at the moment they write.
    """
    env = os.environ.get("PERSONAL_DB_DIR")
    if env:
        return Path(os.path.expanduser(env))
    root = data_paths.data_root()
    matches = sorted(root.glob("*/personal"))
    if matches:
        return matches[0]
    return root / data_paths.instance_slug() / "personal"


def db_path() -> Path:
    fname = os.environ.get("PERSONAL_DB_FILENAME", DEFAULT_DB_FILENAME)
    return resolve_root() / "db" / fname


def snapshot_base() -> Path:
    """Base directory the per-domain snapshot folders live under.
    Default: data/<instance>/system/logs (a sibling tree of the personal root),
    so snapshots sit with the rest of the system's generated logs rather than
    inside the DB's own folder. Each domain writes to <base>/<its subdir>/."""
    env = os.environ.get("PERSONAL_SNAPSHOT_BASE")
    if env:
        return Path(env)
    return resolve_root().parent / "system" / "logs"


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open the DB with the shared write-safety pragmas.

    An absent database is provisioned from schema.sql first, so the first tool
    to reach for personal.db on a new install finds an empty one.
    """
    p = Path(path) if path else db_path()
    if not p.exists():
        data_paths.ensure_db(p, SCHEMA_PATH)
    conn = sqlite3.connect(str(p), timeout=10)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=MEMORY")  # avoid the on-disk journal (README §3b)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Idempotently create/patch all tables + views from schema.sql."""
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


class with_writeback:
    """Context manager: copy the live DB to /tmp, yield a connection to the
    copy, and on clean exit copy it back over the original. Belt-and-braces for
    writes over a mounted-folder bridge where an in-place write once failed.

        with with_writeback() as conn:
            conn.execute(...); conn.commit()
    """

    def __init__(self, path: Path | None = None):
        self.orig = Path(path) if path else db_path()
        self.tmp = Path(tempfile.gettempdir()) / f"personal_db_wb_{os.getpid()}.db"
        self.conn: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        if self.orig.exists():
            shutil.copy2(str(self.orig), str(self.tmp))
        self.conn = connect(self.tmp)
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        if self.conn:
            self.conn.close()
        if exc_type is None:
            self.orig.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(self.tmp), str(self.orig))
        self.tmp.unlink(missing_ok=True)
        return False  # never swallow exceptions
