# Bristol Tickets — GUI viewer for the tickets database

*(Folder: `bristol/`. The name is after Bristol board, the card stock US
double-roll tickets are printed on; the metaphor for this personal + AI
ticketing system, as "kanban" was for Ohno's.)*

A standalone PySide6 desktop tool that opens the shared tickets SQLite database
and displays it as a warm, card-based Kanban board with create/edit/delete, a
filter panel, global search, and a properties inspector. Tabs are driven by
`task.stage` (Backlog | Board=active | Archive) with manual `task.sort_order`.

It is **mechanism-only**: no agent logic, no personal paths, no coupling to the
larger application it lives in. Its only job is to open a tickets `.db` (located
at runtime) and show it.

A built `.app` also carries the project tree inside it, which is how Bristol
installs from a download. That is `payload.py`, and it reads none of what it
carries: the tree is bytes to copy, not files to interpret, so the
mechanism-only rule holds.

## Folder layout

```
bristol/
├── app.py               launcher: update the installation, locate DB, open the window
├── config_file.py       read/write config.local.json (unknown keys survive)
├── payload.py           the project tree a built .app carries, installs and refreshes
├── make_release.py      one command: checks, build, zip, checksum, publish line
├── slim.py              what a built bundle keeps of PySide6, and what it drops
├── icon.icns / icon.png the app icon (bundle icon + window/Dock icon)
├── schema.sql           idempotent (IF NOT EXISTS) schema snapshot, auto-applied on launch
├── __init__.py          package marker
├── ui/                  the PySide6 widgets (split into small modules)
│   ├── README.md        the styling contract: scheme keys, tokens, intent
│   ├── theme.py         schemes, design tokens, stylesheet, COLUMNS, CARD_ROLE
│   ├── filter_menu.py   FilterState + FilterMenu — what the board is showing
│   ├── schema_guard.py  on-launch non-destructive migration
│   ├── card_delegate.py CardDelegate — per-card QPainter rendering
│   ├── links.py         LinkBar — a ticket's links to tickets and addresses
│   ├── attachments.py   a ticket's attached images
│   ├── record_dialog.py UnifiedRecordDialog — create/edit modal
│   ├── kanban_column.py KanbanColumn — a populated column + its queries
│   ├── growing_edit.py  GrowingTextEdit — the field every typing surface uses
│   ├── setup_wizard.py  first-run setup: folders, board, config, pointer
│   ├── settings_tab.py  SettingsTab — app and session choices, stored in config
│   └── main_window.py   MainWindow — toolbar, tabs, filters, search, inspector
├── reports/             the analytic report written on Clear Done (own README)
│   ├── paths.py         where the report goes (env → .local → config)
│   ├── metrics.py       DB → computed facts (no I/O, no formatting)
│   ├── render.py        facts → Markdown (no DB, no computation)
│   └── generate.py      orchestration, period boundaries, CLI
├── README.md            this file
├── CONSULTANT_CONTEXT.md  hand this + the folder to an external consultant
└── BUILD_APP.md         building the release, and what signing would change
```

Each `ui/` module stays small enough for a focused edit, or for an external
consultant to ingest in one pass.

## How it looks (`ui/theme.py`)

Every colour is a key in the live palette `C`, which a named scheme fills, and
every gap, corner and font size is a step on one of three token scales. Nothing
in the UI holds a hex value or a pixel count of its own, so a new palette is a
data change and a density change is one edit. `ui/README.md` is the contract an
agent styles from: what each key means, which token governs which element, and
how to answer an instruction given as intent. The scheme in force is
`appearance.scheme` in the configuration, picked in the Settings tab.

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
5. **Fresh provisioning** — a configured installation whose board is missing
   gets an empty DB at a default location with `schema.sql` applied, so the app
   still opens.

The order is stated once, in `src/tools/config_tools/instance_pointer.py`.

No user-specific paths are hardcoded anywhere in this tool.

## A download installs itself (`payload.py`)

`setup.py` stages the project's published files into the bundle's
`Resources/payload/`; `PUBLISHED_DIRS` and `PUBLISHED_FILES` name them and
include neither `config/config.local.json` nor `data/`.

- **First launch** finds no project folder around it and no pointer, so setup
  opens by asking where Bristol should live and copies the payload there.
- **Every later launch** compares `src/VERSION` in the bundle against the one
  in the folder it opens, and replaces the published files when the app is
  newer. An installation's configuration and data are not published names, so
  neither is read.

A run from source carries no payload: `bundled()` returns None and both steps
are skipped.

## First run (`ui/setup_wizard.py`)

When nothing above resolves and no `config/config.local.json` has been written,
launch opens a setup wizard instead of an empty board. It asks where Bristol
lives (a download only — a clone already is that folder), an instance name, the
folder that instance's data lives in, which of the shipped agents to enable,
and — optionally — a Markdown notebook and a Zotero data folder.

Finish creates the data folders each enabled agent declares, provisions
`tickets/tickets.db` from `schema.sql`, writes `config/config.local.json` from
`config/config.example.json` with the answers substituted in, and writes the
instance pointer. Cancel writes nothing, and takes back a tree the same run
placed — leaving a folder that already held anything as it stands.

The run ends by naming where the installation went and offering the line to
paste into an agent host that takes typed project instructions. Replacing an existing configuration
asks first, and **File → Setup…** re-runs the flow from a running
Bristol Tickets.

A data folder already holding `tickets/tickets.db` is adopted rather than
created: the wizard offers it as you leave the first page, skips the two pages
adoption needs no answers from, runs no schema against that board, leaves
`config.local.json` as it stands, and writes only the instance pointer. The
summary page's tick box governs the pointer in both flows, so an installation
can be set up or adopted without taking over which one the app opens.

The wizard reads `config.example.json` as data and imports nothing from the rest
of `src/tools`, so the mechanism-only rule holds.

## Settings

The **Settings** tab holds every choice this installation makes, read and
written through `config_file.py` — the same file the wizard fills in, never a
second store. A save round-trips the whole document, so a key an older build
does not recognise survives untouched, and one Save commits the whole page.

Two sections, split by which program reads the key. This app reads the board and
appearance keys and acts on them itself; an agent session reads the session
keys, and this app only writes them.

**Bristol Tickets**

- **Ticket Destination** — `board.new_ticket_stage`, the To Do column or the
  Backlog. It governs every card `add-task` creates without an explicit
  `--stage`, whoever files it and whoever it is for.
  `ticket_tools/ticket_write.py` reads the same key.
- **Theme** — `appearance.scheme`, applied live as it is picked so it can be
  compared against the board it themes. The stored value names the palette
  family; the caption is what this product calls it.

**Agent Sessions**

- **Agent** — `active_agent`, the agent a session takes its identity from. The
  picker offers the agents this installation configures, and moves only on a
  deliberate choice.
- **Work Scope** — `session.work_whole_queue`, how far a session runs when told
  to continue: *Whole Queue* or *One Ticket*. Read by the agent when the scope
  decision is made.
- **Git Commit on Session Close** — `session.suggested_commit`, read by the
  agent as the session closes.

## Filtering the board

One **Filter** button on the Board opens a panel of facets: **Assignee**, every
owner the board holds, and **Epic**, every epic in play plus the cards carrying
none. Each row is a checkbox and the number of board cards it matches, and a
click applies it at once — there is nothing to confirm on the way out.

- **Options within a facet unite; facets intersect.** Two agents show side by
  side, and an agent inside an epic narrows to the overlap.
- **A count is conditional on the other facets**, so a row reading 0 is a row
  worth not clicking.
- **What is set stands on the control row** as a chip that removes itself, and
  the button carries the same count, so a narrowed board never reads as an empty
  one.
- **One state narrows the Board, the Backlog and the Archive.** Search takes no
  filter: it is the view whose job is to find a card the board is not showing.
- **Nothing is stored.** A filter is what you are looking at now, and a fresh
  launch shows the whole board.

## Links

Above the Issue Log — in both the inspector and the create/edit dialog — a
ticket shows its **links**, one per full-width row. *Add link* opens a small
modal with the two kinds as mutually exclusive choices, so the entry fields cost
one button rather than two permanent rows. Removing a link asks first.

- **Ticket links** render as `#153 — Title`; clicking one retargets the
  inspector at that ticket. They are stored as a single symmetric row
  (`task_link`, normalized to `task_id` = the lower id), so a link is
  bidirectional by construction: it shows on both tickets, and one delete clears
  it from both.
  // A mirrored pair of rows can half-delete into a one-way link.
- **Address links** hold a web URL, a `zotero://` citation, an `obsidian://`
  note, or a filesystem path, with an optional caption. Clicking hands the
  string to the OS: a scheme routes to whichever app registered it, and a bare
  path opens with whatever owns that file type. Bristol Tickets therefore knows
  nothing about schemes, vault names or user paths — the mechanism-only rule
  holds.

Links may be added while a ticket is still being *created*: they buffer in the
widget (shown as "on save") and are written once the INSERT yields an id.

A ticket Description is confined to its Build or Fix template, so provenance
lives in a link. That rule is agent behaviour and sits outside this tool:
`src/skills/manage-tickets/SKILL.md` §Record types: Build vs Fix.

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

## Build

```bash
python3 make_release.py
```

Checks, bundle, zip, checksum, and the line that publishes it. `BUILD_APP.md`
covers what it does, what signing would change, and the live-source launcher
that runs this folder's source directly while iterating.

## Headless smoke test

Runtime-error checking lives in `../test_tools` (the fleet's testing harness):
`bash ../test_tools/run_smoke.sh bristol` builds this tool's widgets on
Qt's `offscreen` platform, catching errors `py_compile` can't (bad imports,
signal/slot mismatches, widget construction that throws). It is **not** a visual
check — how things look still needs a real display (the packaged Mac app).

## Invariants

- **Keep `app.py` and every `ui/` module free of a user-specific path or any
  personal data.**
- **A published name never includes an instance.** `payload.PUBLISHED_DIRS` and
  `PUBLISHED_FILES` decide what a release carries and what an update replaces;
  adding `config/config.local.json` or `data/` to either would ship one user's
  installation to everyone and overwrite the next one's.
- **Regenerate `schema.sql` when the shared schema changes**, by the method its
  own header states.
- **Embed no agent behaviour here.** This tool opens a database and shows it.
