# Bristol — consultant context (READ THIS FIRST)

You have been handed **only this folder**. That is deliberate and sufficient.
This tool is fully self-contained: everything needed to understand, run, build,
and modify it is in this folder. You do **not** need — and will not be given —
the surrounding application it happens to live in. Do not ask about it, infer
it, or add references to it.

## What this tool is

A single-purpose **desktop GUI** (PySide6 / Qt for Python) that opens one
**SQLite** database — a project "tickets" of epics and tasks — and lets a human
view and edit it as a Kanban board. That is the whole job.

It is **mechanism-only**: it has no notion of who the user is, no business
logic, no network, no automation. It reads a `.db` file and shows it. Think of
it as a specialized spreadsheet viewer for one database shape.

## Hard rules when editing (do not break these)

1. **No personal data, no absolute user paths, no usernames** anywhere in the
   code. The database location is discovered at runtime (see "How it finds the
   DB"). If you need a path for testing, use the `TICKETS_DB` environment
   variable — never hardcode one.
2. **Keep it mechanism-only.** No feature that assumes a specific user, project,
   company, or workflow. If a change would require knowing anything about the
   world outside "a tickets database," it does not belong here.
3. **Behaviour-preserving unless asked.** The SQL and data flow are considered
   correct. When fixing UI, don't silently change what gets written to the DB.
4. **Keep files small and single-purpose** (see the module map). If a file
   grows past ~350 lines, that's a signal to split it — the same reason this
   code is in six files instead of one.
5. **Every DB write goes through a `commit()`** and targets a parameterized
   query (`?` placeholders), never string-formatted SQL.

## Module map (`ui/` package)

Import graph is strictly bottom-up (no cycles). Edit the smallest file that
owns your concern:

| File | ~lines | Owns | Import it for… |
| :--- | :--- | :--- | :--- |
| `ui/theme.py` | 175 | Colours, the Qt stylesheet, board column list, the custom item data-role, and 3 tiny helpers | Any visual/colour change; adding a shared constant |
| `ui/schema_guard.py` | 50 | The on-launch, non-destructive schema migration | Adding a new column/table the UI needs |
| `ui/card_delegate.py` | 210 | `CardDelegate` — how a single task **card** is painted (QPainter) | Changing how cards *look* (pills, badges, layout, fonts) |
| `ui/record_dialog.py` | 300 | `UnifiedRecordDialog` — the create/edit **modal** for tasks/epics (Stage + Status pickers) | Changing the edit **form** (fields, validation, save/delete) |
| `ui/kanban_column.py` | 185 | `KanbanColumn` — one **column** of cards + the 3 DB queries that fill it (board / backlog / archive) | Changing which tasks appear in a column, or column click behaviour |
| `ui/main_window.py` | 300 | `MainWindow` — the window shell: toolbar, tabs, filters, search, inspector | Changing top-level layout, filters, search, the inspector panel |

`app.py` (repo folder, not in `ui/`) is the launcher: it locates the DB, applies
`schema.sql`, and opens `MainWindow`.

## How it finds the DB (`app.py`)

In priority order:

1. `TICKETS_DB` environment variable — an explicit path to the `.db` file.
   Use this for local testing: `export TICKETS_DB=/tmp/test_tickets.db`.
2. Otherwise it searches upward from `app.py` for a `data/*/tickets/tickets.db`
   and uses the first match. The `*` is intentional — it avoids hardcoding any
   user-specific folder name.
3. If nothing exists yet, it creates an empty DB at a default location and
   applies `schema.sql` so the app still opens.

## The database

`schema.sql` in this folder is the single, authoritative schema — full table
definitions, applied idempotently by `app.py` on launch. Read it directly for
column details.

What the viewer actually touches:

- **`task`** — the card. Two orthogonal axes (the Kanban model):
  `stage` (`backlog` | `active` | `archive`) decides **which tab** the card
  appears in, and `status` (`todo` | `doing` | `done`) is its **board column**.
  `sort_order` is the manual drag-to-reorder position within a list (lower =
  higher; the Backlog is one list, each active status column its own list).
  Other key columns: `title`, `priority` (0–100, drives card colour), `epic_id`,
  `assignee` (shown as "owner"), `reporter` ("originator"), `story_points`.
- **`epic`** — tasks link to one via `task.epic_id`.
- (**No `sprint` / `sprint_task` tables.** A task's tab is `task.stage`. The
  Board shows `stage='active'`; Backlog shows `stage='backlog'`; Archive shows
  `stage='archive'` newest-modified first.)
- **`handoff`** — one overwrite-in-place block PER AGENT (`id, agent UNIQUE,
  note, written_at`); the Handoff tab's agent picker selected whose block you
  read/write. No history is kept (there is no cross-agent `inbox`,
  archived-handoff history, or `epic_log` table).
- **`issue_log`** — per-task progress notes shown in the inspector.

Other tables exist in the shared DB (`scope`, `task_meta`, `theme`) but the
viewer doesn't edit them. You rarely need more than the above to make a UI
change.

## Run it

```bash
pip install PySide6            # once
export TICKETS_DB=/path/to/tickets.db   # optional; else it auto-discovers
python3 app.py
```

To build a double-clickable macOS `.app`, see `BUILD_APP.md`.

## Recipe examples

- *"The priority pill colour is wrong"* → `ui/theme.py` (`_priority_color`) and/or
  `ui/card_delegate.py` (where the pill is drawn).
- *"Add a field to the task edit form"* → `ui/record_dialog.py` (add the widget,
  add it to `task_rows`, load it in `_load_existing_data`, save it in
  `save_data`) and `ui/schema_guard.py` if it needs a new column.
- *"The Board tab shows the wrong tasks"* → `ui/kanban_column.py`
  (`load_board_tasks`).
- *"Change the window title / tab names / inspector layout"* →
  `ui/main_window.py`.
