#!/usr/bin/env python3
"""
db_common.py — shared data layer for the unified personal database.

Every personal_db tool imports these helpers so path discovery, write-safety,
and the Mac-mount read/write-back workaround live in exactly one place.

Path resolution (no hardcoded user paths in /src — invariant shared with
tools/zotero and tools/ticket_tools):
  - PERSONAL_DB_DIR       : absolute path to the personal-db data root
                            (contains db/ and data/).
  - PERSONAL_DB_FILENAME  : db filename (default 'personal.db')
  - PERSONAL_SNAPSHOT_BASE: base dir for the per-domain snapshot folders
                            (default: <root>/../system/logs; each domain writes
                            to <base>/<subdir>/, e.g. library_snapshots/)

Each is read from the environment, then from config's `personal_db.env`
block, through data_paths.resolve, so a value there may refer to the key that
owns the folder. If PERSONAL_DB_DIR is set in neither, it falls back to
canonical discovery: the first
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
tools/ticket_tools/README.md §Invariants). Writers that must be extra safe can use
with_writeback(), which edits a /tmp copy and copies it back atomically.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))
import data_paths

DEFAULT_DB_FILENAME = "personal.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _configured(name: str) -> str | None:
    """`personal_db.env.<name>` from config, or None where it is not set."""
    try:
        value = data_paths.read_config.get(f"personal_db.env.{name}")
    except (KeyError, SystemExit):
        return None
    return value if isinstance(value, str) and value.strip() else None


def resolve_root() -> Path:
    """The personal-db data root (folder containing db/ and data/).

    PERSONAL_DB_DIR, then the first data/*/personal match, then the path a
    fresh install would use. Resolving never creates anything; the writers
    below do that at the moment they write.
    """
    env = os.environ.get("PERSONAL_DB_DIR") or _configured("PERSONAL_DB_DIR")
    if env:
        return data_paths.resolve(env)
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
    env = os.environ.get("PERSONAL_SNAPSHOT_BASE") or _configured("PERSONAL_SNAPSHOT_BASE")
    if env:
        return data_paths.resolve(env)
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
    conn.execute(
        "PRAGMA journal_mode=MEMORY"
    )  # avoid the on-disk journal (ticket_tools/README.md §Invariants)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def _add_missing_columns(conn: sqlite3.Connection, sql: str) -> list[str]:
    """Add to each existing table the columns schema.sql gives it and it lacks.

    `CREATE TABLE IF NOT EXISTS` leaves an existing table as it is, so a column
    added to schema.sql reaches an older database only through ALTER TABLE.
    schema.sql is built in memory and compared table by table, so it stays the
    one place a column is declared. A column added this way is nullable.
    """
    ref = sqlite3.connect(":memory:")
    try:
        ref.executescript(sql)
        tables = [r[0] for r in ref.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        added = []
        for t in tables:
            have = {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}
            if not have:
                continue  # absent here; the CREATE below makes it whole
            for _, col, ctype, _, dflt, _ in ref.execute(f"PRAGMA table_info({t})"):
                if col in have:
                    continue
                default = f" DEFAULT {dflt}" if dflt is not None else ""
                conn.execute(f"ALTER TABLE {t} ADD COLUMN {col} {ctype}{default}")
                added.append(f"{t}.{col}")
        return added
    finally:
        ref.close()


def apply_schema(conn: sqlite3.Connection) -> list[str]:
    """Idempotently create/patch all tables + views from schema.sql.

    Returns the columns it had to add to tables that already existed.
    """
    sql = SCHEMA_PATH.read_text()
    added = _add_missing_columns(conn, sql)
    conn.executescript(sql)
    conn.commit()
    return added


class with_writeback:  # noqa: N801 (read as a function: with with_writeback(path) as conn)
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
