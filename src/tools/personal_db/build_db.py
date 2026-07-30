#!/usr/bin/env python3
"""
build_db.py — create (or patch) personal.db from schema.sql and register domains.

Idempotent: safe to re-run. Creates db/ under the personal-db root if missing,
applies schema.sql (CREATE ... IF NOT EXISTS throughout), seeds the meta +
domains registry rows, and prints a summary.

Run: PERSONAL_DB_DIR=... python3 src/tools/personal_db/build_db.py
"""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_common as dbc  # noqa: E402

SCHEMA_VERSION = "1"

# name, display_name, source, primary_table, snapshot_file, stats_view, sort_order, notes
DOMAINS = [
    ("applications", "Job Applications", "personal_db", "applications",
     "applications.xlsx", "v_application_stats", 10,
     "Applications domain (career_coach)."),
    ("books", "Book Library", "zotero", "items", "library.xlsx", None, 20,
     "Books domain (librarian). Source of truth is Zotero, not this DB — "
     "read through src/tools/zotero/zotero_export.py."),
]


def main() -> None:
    root = dbc.resolve_root()
    (root / "db").mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(parents=True, exist_ok=True)

    conn = dbc.connect()
    dbc.apply_schema(conn)

    now = datetime.datetime.utcnow().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO meta(key,value) VALUES('schema_version',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (SCHEMA_VERSION,))
    conn.execute(
        "INSERT INTO meta(key,value) VALUES('created_at',?) "
        "ON CONFLICT(key) DO NOTHING", (now,))
    conn.execute(
        "INSERT INTO meta(key,value) VALUES('updated_at',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (now,))

    for name, disp, source, tbl, snap, view, order, notes in DOMAINS:
        conn.execute("""
            INSERT INTO domains(name,display_name,source,primary_table,snapshot_file,stats_view,active,sort_order,notes)
            VALUES(?,?,?,?,?,?,1,?,?)
            ON CONFLICT(name) DO UPDATE SET
              display_name=excluded.display_name,
              source=excluded.source,
              primary_table=excluded.primary_table,
              snapshot_file=excluded.snapshot_file,
              stats_view=excluded.stats_view,
              sort_order=excluded.sort_order,
              notes=excluded.notes
        """, (name, disp, source, tbl, snap, view, order, notes))
    conn.commit()

    print(f"[build_db] DB ready at {dbc.db_path()}")
    print(f"  schema_version={SCHEMA_VERSION}")
    tabs = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    print(f"  tables: {', '.join(tabs)}")
    print("  domains:")
    for r in conn.execute("SELECT name,display_name,source,primary_table,snapshot_file "
                          "FROM domains ORDER BY sort_order"):
        print(f"    - {r['name']:14s} {r['display_name']:18s} -> "
              f"{r['source']}:{r['primary_table']} / {r['snapshot_file']}")
    conn.close()


if __name__ == "__main__":
    main()
