# Bristol — Consultant Context

You have been handed only this folder, and it is sufficient. Everything needed
to understand, run, build and modify this tool is in it. The surrounding
application it lives in is not needed and will not be given; do not infer it or
add a reference to it.

## What this tool is

A desktop GUI in PySide6 that opens one SQLite database of epics and tasks and
shows it as a Kanban board a human edits. It has no notion of who the user is,
no business logic, no network and no automation — a specialized viewer for one
database shape.

## Rules when editing

- **Never write a personal path, a username, or any personal data into the
  code.** The database is discovered at runtime; use the `TICKETS_DB`
  environment variable for testing.
- **Add no feature that assumes a specific user, project, company or
  workflow.** A change needing knowledge of anything beyond "a tickets database"
  does not belong here.
- **Preserve behaviour unless asked to change it.** The SQL and data flow are
  correct; a UI fix does not silently change what is written.
- **Split a file that grows past ~400 lines.**
- **Route every write through a parameterized query and a `commit()`**, never
  string-formatted SQL.

## Module map

The import graph runs strictly bottom-up, with no cycles. Edit the smallest file
that owns the concern.

| File | Owns | Edit it for |
| :--- | :--- | :--- |
| `app.py` | locating the DB, applying `schema.sql`, opening the window | launch behaviour |
| `config_file.py` | reading and writing `config.local.json`, preserving unknown keys | anything stored as configuration |
| `instance.py` | the per-machine instance pointer | where an installed copy looks for its data |
| `ui/theme.py` | palette, stylesheet, `COLUMNS`, `CARD_ROLE`, `log_lines`, small helpers | a colour or a shared constant |
| `ui/schema_guard.py` | `ensure_schema_up_to_date`, the change-log triggers, non-destructive migration | a new column or table the UI needs |
| `ui/card_delegate.py` | `CardDelegate` — painting one card with QPainter | how a card looks: pills, badges, layout, fonts |
| `ui/links.py` | `LinkBar` — a ticket's links to tickets and to addresses | link display, creation, removal |
| `ui/attachments.py` | a ticket's attached images | attachment handling |
| `ui/record_dialog.py` | `UnifiedRecordDialog` — the create and edit modal | the form: fields, validation, save, delete |
| `ui/kanban_column.py` | `KanbanColumn` and the queries filling it | which tasks appear in a column, and drop behaviour |
| `ui/settings_tab.py` | `SettingsTab` — board behaviour stored in config | a new setting |
| `ui/setup_wizard.py` | first-run setup: folders, board, config, pointer | the first-run flow |
| `ui/main_window.py` | `MainWindow` — toolbar, tabs, filters, search, inspector | top-level layout |

## How it finds the database

1. **`TICKETS_DB`** — an explicit path to the `.db` file. Use it for testing.
2. **The instance pointer** — written outside the repo, naming the data root and
   instance slug. This is what a relocated `.app` uses.
3. **Auto-discovery** — searching upward from `app.py` for the first
   `data/*/tickets/tickets.db`. The `*` avoids hardcoding a folder name.
4. **Fresh provisioning** — an empty database at a default location with
   `schema.sql` applied, so the app opens either way.

## The database

`schema.sql` is the authoritative definition, applied idempotently on launch.
What the viewer touches:

- **`task`** — the card, on two orthogonal axes. `stage` (`backlog` | `active` |
  `archive`) decides the tab; `status` (`todo` | `doing` | `done`) is the board
  column. `sort_order` is the manual position within a list, lower being higher;
  the Backlog is one list and each active status column its own. Also `title`,
  `description`, `pressure` (0–100, driving card colour, a rating and not a
  rank), `epic_id`, `assignee` shown as owner, `reporter` shown as originator,
  `estimate` (S | M | L | XL), and `record_type` (`build` | `fix`).
  `story_points` is retired and no longer written.
- **`epic`** — a task points at one through `task.epic_id`.
- **`issue_log`** — per-task comments, shown in the inspector.
- **`task_link`** — one row per relation, either between two tasks or from a
  task to a URI. A task-to-task row is normalized so `task_id` is the lower id,
  making the link bidirectional by construction.
- **`task_event`** — the change log: one row per changed field, holding the
  field, its new value, the actor and a timestamp, appended by database
  triggers.
- **`attachment`** — images pinned to a task; the files live in a directory
  beside the database, resolved at runtime.

`scope`, `task_meta` and `theme` exist and the viewer does not edit them. There
are no `sprint`, `sprint_task` or `handoff` tables; `schema_guard` drops them
from any database still carrying one.

## Run it

```bash
pip install PySide6
export TICKETS_DB=/path/to/tickets.db   # optional; else it auto-discovers
python3 app.py
```

`BUILD_APP.md` covers building a double-clickable macOS `.app`.

## Worked examples

- **A pressure pill is the wrong colour** → `ui/theme.py`, and
  `ui/card_delegate.py` where the pill is drawn.
- **Add a field to the task form** → `ui/record_dialog.py`: add the widget, add
  it to `task_rows`, load it in `_load_existing_data`, save it in `save_data`.
  Add the column in `ui/schema_guard.py` where one is needed.
- **The Board tab shows the wrong tasks** → `ui/kanban_column.py`,
  `load_board_tasks`.
- **Change the window title, tab names or inspector layout** →
  `ui/main_window.py`.
