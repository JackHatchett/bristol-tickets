# personal_db tools

Unified personal-tracking database: one SQLite `personal.db` with per-domain
tables (job applications, future health/…), each rendering an xlsx snapshot.
For a domain held here, the DB is source of truth and the xlsx is a generated
view. See `DESIGN.md` for the full rationale.

**Not every domain lives here.** Books live in Zotero: this DB has no
books tables, and `render_snapshot.py --domain books` reads
`src/tools/zotero/zotero_export.py` instead. The `domains` registry says which
source a domain uses.

## Invariants (shared with tools/zotero and tools/ticket_tools)

1. **No personal data in `/src`.** Paths resolve from env
   (`config/config.local.json` → `personal_db` block); never hardcoded.
2. **One instance DB**, discovered as `data/*/personal/db/personal.db` when env
   is unset.
3. **stdlib `sqlite3` only** (no CLI subprocess); `openpyxl` only for render.
4. **Write safety:** all writers use `PRAGMA journal_mode=MEMORY` via
   `db_common.connect()`. Do **not** open the mounted DB with a default-journal
   `sqlite3.connect` for writes.
   // A default-journal write over the mount can leave a hot rollback journal
   // that wedges the DB.

## Environment (set from config `personal_db`)

| Var | Meaning | Default |
|---|---|---|
| `PERSONAL_DB_DIR` | data root (contains `db/`) | canonical `data/*/personal` |
| `PERSONAL_DB_FILENAME` | db filename | `personal.db` |
| `PERSONAL_SNAPSHOT_BASE` | base dir for the per-domain snapshot folders | `<root>/../system/logs` |

Snapshots are written to `<PERSONAL_SNAPSHOT_BASE>/<subdir>/<file>` — books →
`library_snapshots/library.xlsx`, applications →
`applications_snapshots/applications.xlsx`.

## The library's dated history (books only)

Three different things live in `library_snapshots/`, and the difference matters:

| | What it is | Lifecycle |
|---|---|---|
| `library.xlsx` | the live view | overwritten every render, never dated |
| `archive/library_YYYY-MM-DD.xlsx` | the retained series | one per day max, pruned by policy |
| `checkpoints/*.xlsx` | pinned moments | never pruned, never auto-created |

`snapshot_archive.py` owns the series. Retention is grandfather-father-son —
7 daily, 5 weekly, 12 monthly, then one per year forever — the same shape
restic/borg `forget` use. `render_snapshot.py` calls it after every books
render; `--no-archive` renders the live view only.

**These dated files are wanted, and are not the backup churn the charter
forbids.** They are a longitudinal record of the collection, kept deliberately
under a policy and requested by the user. Time Machine is still the backup and
still covers this folder; it just cannot answer what the collection looked like
in a given past year, because it drops its oldest copies when the disk fills. Do
not delete `archive/` or `checkpoints/` as tidy-up.

`checkpoints/` holds pinned pre-policy snapshots. They pre-date the retention
policy, cannot be regenerated, and are exempt from it.

Scheduled daily at 09:00 by
`~/Library/LaunchAgents/com.<user>.library-snapshot.plist`, logging to
`LOG_ROOT/library_snapshot.log` / `.err`.

## Commands

```bash
export PERSONAL_DB_DIR=.../data/<instance>/personal

# create / patch the DB (idempotent)
python3 src/tools/personal_db/build_db.py

# one-time domain import (parity report; --replace to rebuild the domain)
python3 src/tools/personal_db/import_applications.py

# render snapshots (books reads Zotero, applications reads this DB)
python3 src/tools/personal_db/render_snapshot.py --domain all   # or applications | books

# the dated series: dry-run the retention policy, then enforce it
python3 src/tools/personal_db/snapshot_archive.py --dir <...>/library_snapshots --stem library
python3 src/tools/personal_db/snapshot_archive.py --dir <...>/library_snapshots --stem library --apply

# write CLI
python3 src/tools/personal_db/personal_write.py add-application --company X --role Y --status Applied
python3 src/tools/personal_db/personal_write.py update-application --id 42 --status Interviewing
python3 src/tools/personal_db/personal_write.py find-company --company Spotify   # "have I applied?"
```

Mutating write subcommands auto-re-render the affected snapshot (pass
`--no-render` to skip).

## Adding a domain

Edit `schema.sql` (tables + optional `v_<domain>_stats`), add it to
`build_db.py`'s `DOMAINS` with `source='personal_db'`, add a `SPECS` entry in
`render_snapshot.py`, and (if writable) subcommands in `personal_write.py`.
A domain whose data lives elsewhere gets a `source` of its own and a row
provider in `render_snapshot.py`, as books does. See `DESIGN.md` §4.
