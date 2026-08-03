# Personal Database — design

**Source of truth for the unified personal-tracking database.** Built by
`chief_of_staff`. Consolidates the user's personal-tracking
data stores behind one SQLite DB that renders xlsx snapshots — the same
"one source of truth, xlsx is a generated view" pattern as the tickets database.

## 1. Goals & principles

- **One DB, many domains.** A single `personal.db` holds the personal domains
  that have no better home: job **applications** today, future stores (e.g.
  **health**) that slot in without reworking the core.
- **A domain with a real application behind it belongs in that application.**
  Books live in Zotero and this DB holds no books tables. Zotero does catalogue
  lookup, deduplication, tagging, collections and sync properly, and a parallel
  copy here would be a second source of truth that drifts.
  The `domains` registry carries a `source` column so the renderer can serve a
  domain it does not store.
- **DB is SoT; xlsx is a generated snapshot.** Each domain renders to its own
  xlsx (`render_snapshot.py`). The snapshot is a visual backup + a
  mistake-finding aid, *not* the long-term backup — Time Machine covers the
  underlying files. Eventually a custom viewer (à la Bristol) can
  replace the snapshots.
- **Zero external deps for data.** stdlib `sqlite3` only; `openpyxl` just for
  the xlsx render. No ORM.
- **No personal paths in `/src`.** All paths resolve from env vars set in
  `config/config.local.json` (`personal_db` block), exactly like
  `ZOTERO_DATA_DIR` / tickets discovery. Falls back to canonical
  `data/*/personal/` discovery when the env is unset (forkable).
- **Write safety over the mount.** Every writer opens with
  `PRAGMA journal_mode=MEMORY` (see `tools/ticket_tools/README.md`
  §Invariants). Never
  do ad-hoc default-journal `sqlite3.connect` writes against the mounted DB.
  // A default-journal write over the sandbox→Mac bridge can wedge the DB with
  // a hot rollback journal; MEMORY mode writes no such file.

## 2. Layout

```
data/<instance>/personal/db/personal.db        # the database (SoT) — db only

data/<instance>/system/logs/                    # generated snapshots (PERSONAL_SNAPSHOT_BASE)
  library_snapshots/library.xlsx                #   books domain — rendered FROM ZOTERO
  applications_snapshots/applications.xlsx      #   applications domain

src/tools/personal_db/
  schema.sql                # multi-domain DDL (meta, domains registry, per-domain tables + views)
  db_common.py              # path discovery, connect() with write-safety, with_writeback()
  build_db.py               # create/patch DB from schema.sql; seed meta + domains registry
  render_snapshot.py        # THE renderer: applications from this DB, books from Zotero
  personal_write.py         # write CLI (add/update application, find-company, render)
  DESIGN.md / README.md
```

## 3. Schema

Two bookkeeping tables plus one block of tables per domain:

- `meta(key,value)` — `schema_version`, `created_at`, `updated_at`.
- `domains(name, display_name, source, primary_table, snapshot_file,
  stats_view, active, sort_order, notes)` — the registry the renderer (and a
  future viewer) iterate. `source` is `personal_db` or `zotero`; `stats_view`
  is NULL when the source is not this DB. **Registering a new domain = one
  INSERT here.**
- **applications** — columns mirror `data/*/career/SCHEMA.md` 1:1
  (Company…Year). Indexed on company/status/year. `v_application_stats` view.
- **books** — no tables; the domain lives in Zotero. The registry row survives
  with `source='zotero'` because the domain still renders a snapshot. Its
  metrics are computed in `tools/zotero/zotero_export.py` and, in the xlsx, as
  live Excel formulas over the sheet — so they follow the data rather than the
  database.

## 4. Adding a future domain (e.g. health)

1. Add its table(s) + optional `v_<domain>_stats` view to `schema.sql`.
2. `INSERT` a row into `domains` (do this in `build_db.py`'s `DOMAINS` list).
3. Add a render spec to `render_snapshot.py` `SPECS`.
4. (If it needs writes) add subcommands to `personal_write.py`.

No change to existing domains, tables, or agents. This is the seam for
future-proofing without a health table now.

## 5. Agent integration

- **career_coach** — reads/writes applications through this DB. `find-company`
  gives the "have I already applied here?" lookup so a new JD session pulls
  just that company's prior rows, not the whole history. `SCHEMA.md` is the
  living vocabulary reference.
- **librarian** — owns the book domain, which lives in Zotero, not here. It
  regenerates the library snapshot via `render_snapshot.py --domain books`,
  which reads Zotero through `tools/zotero/zotero_export.py`. That reader
  copies `zotero.sqlite` first, so the snapshot is regenerable with Zotero
  open; every *writer* under `tools/zotero/` refuses to run until Zotero quits.

## 6. Verification gates

- Applications: 97 CSV data rows → 97 inserted (parity).
- Books (at the Zotero retirement): every one of the 2,736 rows carried a
  `personal.db id` into Zotero, so the join was exact rather than fuzzy — 0
  unmatched, 0 duplicated. Zotero holds one extra read title, added in Zotero
  itself. Page counts and genre strings were backfilled before the drop.
- `PRAGMA integrity_check` = ok. Both snapshots render and re-open in openpyxl.
- Round-trip: `add-application` insert verified, then removed.

## 7. Deferred / later latitude

- A custom DB viewer to replace xlsx snapshots (the eventual end state).
- Normalizing authors/publishers/genres (inherited from the library's own v2
  deferral).
- Health and any further domains, per §4.
- Publish/fork hygiene: strip `price_paid` and anything private if this DB is
  ever published.
