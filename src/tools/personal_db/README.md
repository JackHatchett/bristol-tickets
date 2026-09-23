# Personal Database

One SQLite `personal.db` holding the personal-tracking domains that have no
better home, each rendering an xlsx snapshot. For a domain stored here the
database is the source of truth and the xlsx is a generated view.

- **A domain with a real application behind it lives in that application.**
  Books live in Zotero, so this database holds no books tables and
  `render_snapshot.py --domain books` reads `tools/zotero/zotero_export.py`
  instead. A parallel copy here would be a second source of truth that drifts.
- **The `domains` registry says which source a domain uses.** Registering a
  domain is one row in it.
- **The xlsx is a readable view and a mistake-finding aid, never the backup.**

## Invariants

Shared with `tools/zotero/` and `tools/ticket_tools/`.

- **No personal path in `/src`.** Every path resolves from the environment
  variables the `personal_db` block of config sets.
- **One database per instance**, discovered as `data/*/personal/db/personal.db`
  when the environment is unset.
- **Use stdlib `sqlite3` only**, never a CLI subprocess. `openpyxl` is for the
  render and nothing else. No ORM.
- **Open every write through `db_common.connect()`**, which sets
  `PRAGMA journal_mode=MEMORY`.

## Environment

| Variable | Meaning | Default |
|---|---|---|
| `PERSONAL_DB_DIR` | data root, containing `db/` | first `data/*/personal` |
| `PERSONAL_DB_FILENAME` | database filename | `personal.db` |
| `PERSONAL_SNAPSHOT_BASE` | base for the per-domain snapshot folders | `<root>/../system/logs` |

A snapshot lands at `<PERSONAL_SNAPSHOT_BASE>/<subdir>/<file>`: applications at
`applications_snapshots/applications.xlsx`, books at
`library_snapshots/library.xlsx`.

## Files

```
src/tools/personal_db/
  schema.sql          multi-domain DDL: meta, domains registry, per-domain tables and views
  db_common.py        path discovery, connect() with write safety, with_writeback()
  build_db.py         create or patch the DB from schema.sql; seed meta and the registry
  render_snapshot.py  the renderer: applications from this DB, books from Zotero
  personal_write.py   the write CLI
  contacts_due.py     who is owed something today, read from v_contact_due alone
  install_due_schedule.py  the due list on the machine's own daily schedule
  snapshot_archive.py the dated series and its retention policy

data/<instance>/personal/db/personal.db
data/<instance>/system/logs/<domain>_snapshots/
```

## Schema

- **`meta(key, value)`** — `schema_version`, `created_at`, `updated_at`.
- **`domains(name, display_name, source, primary_table, snapshot_file,
  stats_view, active, sort_order, notes)`** — what the renderer iterates.
  `source` is `personal_db` or `zotero`; `stats_view` is NULL when the source is
  not this database.
- **`applications`** — columns mirroring `data/*/career/SCHEMA.md`, indexed on
  company, status and year, with a `v_application_stats` view.
- **`books`** — a registry row with `source='zotero'` and no tables. Its metrics
  are computed in `tools/zotero/zotero_export.py` and, in the xlsx, as live
  Excel formulas over the sheet, so they follow the data.
- **`learning_progress`** — one row per thing the learner did in a course, with
  `v_learning_stats` and `v_learning_place` beside it. `kind` is `opened`,
  `reading`, `quiz` or `exercise`, `item` says which quiz or exercise, and
  `UNIQUE(course, lesson, kind, item)` means doing the same thing again updates
  that row rather than adding a second. `v_learning_place` is the one query the
  study interface runs to reopen a course.

- **`contact`, `contact_ask`, `contact_link`** — who is owed what, and since
  when. A contact is one person, once: name, aliases, how the user knows them,
  where they are now, a `cadence_days` and the date of the last exchange. An ask
  is one outstanding thing between them, with a `direction` saying who the next
  move waits on — `us` or `them` — a `due_on` and a `status`. A link joins a
  contact to an application, a document or a client, by `target_id` in this
  database or by `target_path`. No application, document or job identifier is a
  column on `contact`: a person is attached to many of them over time.
- **`v_contact_due`** — one view answering one question, who is owed something
  today: a contact whose cadence has come round, and an open ask past its
  `due_on`, each row saying which of the two it is. `v_contact_stats` counts
  both beside the contacts themselves.

**The contacts domain is a state layer, not a description of a person.** The
applications table keeps its own `contact` and `referral` text, the career
dossiers and the notebook's own pages stay where they are, and nothing migrated
into these tables.

**The learning domain is read by an interface, never by an agent deciding what
is next.** Where the fleet stands on a course is a card;
`docs/architecture.md` §The study interface owns the boundary.

## Commands

```bash
export PERSONAL_DB_DIR=.../data/<instance>/personal

python3 build_db.py                              # create or patch, idempotent
python3 render_snapshot.py --domain all          # or applications | books
python3 render_snapshot.py --domain books --no-archive

python3 personal_write.py add-application --company X --role Y --status Applied
python3 personal_write.py update-application --id 42 --status Interviewing
python3 personal_write.py find-company --company Acme

python3 personal_write.py record-progress --course git_course --lesson 3 --kind opened
python3 personal_write.py record-progress --course git_course --lesson 3 --kind quiz \
    --item q1 --score 4/5
python3 personal_write.py clear-progress --course git_course --lesson 3 --kind reading
python3 personal_write.py find-place [--course git_course]

python3 personal_write.py add-contact --name "A Person" --aliases "Nickname" \
    --how-known "how you know them" --company X --title Y --cadence-days 90
python3 personal_write.py update-contact --id 1 --last-contact-on 2026-09-19
python3 personal_write.py add-ask --contact 1 --kind referral --direction them \
    --subject "what the ask is" --due-on 2026-10-01
python3 personal_write.py close-ask --id 3 [--status dropped] [--keep-last-contact]
python3 personal_write.py add-link --contact 1 --kind application --target-id 42
python3 personal_write.py find-contact --name Nickname

python3 contacts_due.py [--json] [--capture]
python3 install_due_schedule.py [--install] [--hour 7] [--minute 30]

python3 personal_write.py render --domain all

python3 snapshot_archive.py --dir <...>/library_snapshots --stem library
python3 snapshot_archive.py --dir <...>/library_snapshots --stem library --apply
```

- **`find-contact` matches the name and the aliases**, and `add-contact`
  refuses a name already recorded unless it is given `--anyway`. A second row
  for one person is the failure this domain exists to avoid, and a different
  spelling is how it happens.
- **`close-ask` moves the contact's `last_contact_on` to the day it closed**,
  unless it is given `--keep-last-contact`. Closing an ask is the commonest
  moment two people were last in touch, and a cadence measured from a date
  nobody updates comes due for ever.
- **`contacts_due.py` reads `v_contact_due` and nothing else**, prints overdue
  before due-today, and prints nothing at all when nothing is due.
- **`--capture` writes the day's list into the notebook's capture inbox** as one
  dated note, rewritten by a second run the same day, and writes nothing when
  nothing is due. That is how a contact coming due reaches the user: calling a
  friend is his and not an agent's, so it is never a card.
- **`install_due_schedule.py` puts that capture on a daily schedule**, through
  `src/tools/_shared/install_schedule.py`, which is the same installer the
  Bluesky copy uses. Run it on the machine that will hold the schedule: it takes
  the interpreter, the repository and the log location from where it runs.

`record-progress` takes `--course`, `--lesson`, `--kind` and optionally `--item`
and `--score`; `clear-progress` takes the same key and removes that row; and
`find-place` answers where to reopen one course or every course.

- **The study interface calls this module rather than the CLI.** `record`,
  `clear`, `marks` and `place` are the four functions it imports, so the SQL
  behind them has one home — `src/tools/teaching_assistant/study_server/`. `add-application` and `update-application` take the full column set as flags —
`--company`, `--role`, `--fit-notes`, `--fit-verdict`, `--gaps`, `--location`,
`--ats`, `--date-evaluated`, `--cover-letter`, `--status`, `--contact`,
`--referral`, `--jd-link`, `--year` — and re-render the affected snapshot unless
given `--no-render`. `find-company --company X` answers whether an application
already exists.

## The dated series

Three different artifacts live in a snapshot folder:

| | What it is | Lifecycle |
|---|---|---|
| `<stem>.xlsx` | the live view | overwritten every render, never dated |
| `archive/<stem>_YYYY-MM-DD.xlsx` | the retained series | one per day at most, pruned by policy |
| `checkpoints/*.xlsx` | pinned moments | never pruned, never auto-created |

- **`snapshot_archive.py` owns the series.** `--dir` plus `--stem` identifies it, or
  `--archive <live file>` derives both. Without `--apply` it prints the plan and
  deletes nothing; `--json` prints it machine-readable.
- **Retention is grandfather-father-son** — `--keep-daily 7`, `--keep-weekly 5`,
  `--keep-monthly 12`, `--keep-yearly 0` for unlimited. A file satisfying any
  rule is kept.
- **`render_snapshot.py` archives after every books render** unless given
  `--no-archive`.
- **Never delete `archive/` or `checkpoints/` as tidy-up.** They are a
  longitudinal record kept under a policy, not the duplicate files
  `src/app.md` §What a file may say forbids. `checkpoints/` holds moments that
  cannot be regenerated at all.
- **Nothing schedules a render.** A cron entry or launchd job pointed at
  `render_snapshot.py` gets a daily one; by hand it works the same.

## Adding a domain

1. Add its tables and optional `v_<domain>_stats` view to `schema.sql`.
2. Add it to `build_db.py`'s `DOMAINS` with `source='personal_db'`.
3. Add a spec to `render_snapshot.py`'s `SPECS`.
4. Add subcommands to `personal_write.py` where it takes writes.

A domain whose data lives elsewhere takes a `source` of its own and a row
provider in `render_snapshot.py`, as books does. Existing domains, tables and
agents are untouched either way.

## Agents

- **`career_coach`** reads and writes applications here. `find-company` gives a
  new session that company's prior rows rather than the whole history.
- **The study interface** writes and reads `learning`, through the four
  functions above. No agent does either.
- **`librarian`** owns books, which live in Zotero, and regenerates the library
  snapshot with `render_snapshot.py --domain books`. That path copies
  `zotero.sqlite` first, so it runs with Zotero open; every writer under
  `tools/zotero/` refuses to run until Zotero quits.
