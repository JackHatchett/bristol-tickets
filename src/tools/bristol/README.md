# Bristol — GUI viewer for the tickets database

*(Folder: `bristol/`. "Bristol" is the app's name — after Bristol board, the
card stock US double-roll tickets are printed on; the metaphor for this
personal + AI ticketing system, as "kanban" was for Ohno's.)*

A standalone PySide6 desktop tool that opens the shared tickets SQLite database
and displays it as a warm, card-based Kanban board with create/edit/delete, an
epic filter, global search, and a properties inspector. Tabs are driven by
`task.stage` (Backlog | Board=active | Archive) with manual `task.sort_order`.

It is **mechanism-only**: no agent logic, no personal paths, no coupling to the
larger application it lives in. Its only job is to open a tickets `.db` (located
at runtime) and show it.

## Folder layout

```
bristol/
├── app.py               launcher: locate DB, apply schema, open the window
├── icon.icns / icon.png the app icon (bundle icon + window/Dock icon)
├── schema.sql           idempotent (IF NOT EXISTS) schema snapshot, auto-applied on launch
├── __init__.py          package marker
├── ui/                  the PySide6 widgets (split into small modules)
│   ├── theme.py         palette, stylesheet, COLUMNS, CARD_ROLE, tiny helpers
│   ├── schema_guard.py  on-launch non-destructive migration
│   ├── card_delegate.py CardDelegate — per-card QPainter rendering
│   ├── links.py         LinkBar — a ticket's links to tickets and addresses
│   ├── record_dialog.py UnifiedRecordDialog — create/edit modal
│   ├── kanban_column.py KanbanColumn — a populated column + its queries
│   └── main_window.py   MainWindow — toolbar, tabs, filters, search, inspector
├── reports/             the analytic report written on Clear Done (own README)
│   ├── paths.py         where the report goes (env → .local → config)
│   ├── metrics.py       DB → computed facts (no I/O, no formatting)
│   ├── render.py        facts → Markdown (no DB, no computation)
│   └── generate.py      orchestration, period boundaries, CLI
├── README.md            this file
├── CONSULTANT_CONTEXT.md  hand this + the folder to an external consultant
└── BUILD_APP.md         how to build a double-clickable macOS .app (py2app)
```

The UI was refactored from a single 1069-line `main_window.py` into
the six `ui/` modules above so each file is small enough for a focused edit or
an external consultant to ingest in one pass. The split is behaviour-preserving.

## How it finds the database (`app.py`)

1. **`TICKETS_DB`** env var — explicit full path to the `.db` file (use for
   testing/overrides).
2. **The instance pointer** — `~/Library/Application
   Support/BristolTickets/instance.json`, which names the data root and the
   instance slug. This is what a relocated `.app` uses; it lives outside the
   repo so it is never committed and never bundled.
3. **Legacy `tickets_db.local`** — a one-line absolute path next to `app.py`,
   honoured for installs that predate the pointer.
4. **Auto-discovery** — walks up to the project root and searches
   `data/*/tickets/tickets.db`, using the first match. The `*` avoids
   hardcoding any user-specific folder name.
5. **Fresh provisioning** — if none exists, creates an empty DB at a default
   location and applies `schema.sql` so the app still opens.

The order is stated once, in `src/tools/config_tools/instance_pointer.py`.

No user-specific paths are hardcoded anywhere in this tool.

## Links

Above the Issue Log — in both the inspector and the create/edit dialog — a
ticket shows its **links**, one per full-width row. *Add link* opens a small
modal with the two kinds as mutually exclusive choices, so the entry fields cost
one button rather than two permanent rows. Removing a link asks first.

- **Ticket links** render as `#153 — Title`; clicking one retargets the
  inspector at that ticket. They are stored as a single symmetric row
  (`task_link`, normalized to `task_id` = the lower id), so a link is
  bidirectional by construction: it shows on both tickets, and one delete clears
  it from both. Two mirrored rows were rejected because they can half-delete
  into a one-way link.
- **Address links** hold a web URL, a `zotero://` citation, an `obsidian://`
  note, or a filesystem path, with an optional caption. Clicking hands the
  string to the OS: a scheme routes to whichever app registered it, and a bare
  path opens with whatever owns that file type. Bristol therefore knows nothing
  about schemes, vault names or user paths — the mechanism-only rule holds.

Links may be added while a ticket is still being *created*: they buffer in the
widget (shown as "on save") and are written once the INSERT yields an id.

Links exist because a ticket Description is confined to its Build/Fix template,
which left provenance with nowhere to go. The rule that puts it here rather than
in the description body is agent behaviour and lives outside this tool —
`src/playbooks/manage_tickets.md` (§Description discipline).

## Clear Done writes a report

Clearing the Done column sweeps finished cards to the Archive **and** writes an
analytic report to the user's Markdown notebook — one note per sweep, plus a
Dataview index that trends every report against the ones before it. Clear Done
is the board's only natural period boundary, so it is where the reporting
cadence comes from.

The report is strictly advisory: the sweep commits first, and a missing or
unreachable notebook folder skips the report rather than failing the action.
Where reports land is resolved from `BRISTOL_REPORTS_DIR`, then the instance
pointer's config, then a legacy `bristol_reports.local`, then the config found
by walking up the tree — see `reports/README.md`.

`task_event` (`schema.sql`) is the mechanical change log: one row per changed
task field, holding the field, its new value, the actor and a timestamp.
Database triggers write every row, so a drag, a Clear Done sweep, a dialog edit
and a CLI call are all recorded the same way. The inspector's Log pane shows
these interleaved with `issue_log` comments, filtered by two checkboxes —
Comments and Changes, both on by default. Title and description changes record
only that they changed. The status and stage rows are also what make cycle time,
flow efficiency and work-item age computable.

## Run

```bash
pip install PySide6
export TICKETS_DB="/absolute/path/to/tickets.db"   # optional; else auto-discovers
python3 app.py
```

## Get it into your Dock

See `BUILD_APP.md`. Two options: a **live-source launcher** (a tiny `.app` that
runs this repo source directly — no build, edit-and-relaunch; best while
iterating), or a **frozen py2app bundle** (`python3 setup.py py2app` →
`dist/Bristol.app`; portable but rebuild after each change).

## Headless smoke test

Runtime-error checking lives in `../test_tools` (the fleet's testing harness):
`bash ../test_tools/run_smoke.sh bristol` builds this tool's widgets on
Qt's `offscreen` platform, catching errors `py_compile` can't (bad imports,
signal/slot mismatches, widget construction that throws). It is **not** a visual
check — how things look still needs a real display (the packaged Mac app).

## Human audit notes

- `app.py` and all `ui/` modules must stay free of hardcoded user-specific
  paths and personal data.
- `schema.sql` is a generated snapshot; regenerate it if the shared DB schema
  changes (see the header comment in that file).
- Keep this tool mechanism-only — no agent behaviour embedded here.
