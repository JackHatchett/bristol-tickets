# Bristol Reports

The analytic report Bristol writes to the user's Markdown notebook every time
the board's **Clear Done** button sweeps finished cards into the Archive.

A Kanban board has no sprints and so no natural period boundary. Clear Done is
the closest thing this board has — a batch of finished work leaving together, at
a moment the user chose — so it is where the reporting cadence comes from.

## What it produces

One note per sweep, plus a rebuilt `_index.md`:

```
<markdown_notebook.reports_dir>/
    _index.md                              Dataview trend tables across all reports
    bristol_report_2026-07-20_0345.md      one period
    bristol_report_2026-07-28_1912.md
```

Each report carries an executive summary, headline metrics compared against the
previous report, what shipped (grouped by epic), a lead-time distribution, flow
health, composition by owner and originator, threshold-driven findings, a data
quality note, and a full ledger of the archived cards.

Every headline number is duplicated into the note's YAML frontmatter. That is
what makes the index's Dataview tables work — the individual note is for
reading once, the frontmatter is what turns a folder of them into a trend.

## What can and cannot be measured

Two durations get conflated as "how long did it take", and the difference
matters:

| | Definition | Availability |
| --- | --- | --- |
| **Lead time** | `created_at` → `closed_at` | Always. Includes waiting. |
| **Cycle time** | first entry into `doing` → `closed_at` | Only for cards that moved after the `task_event` log existed. |

Without a change log the schema records *what* a card's status is but never
*when* it changed, so cycle time, flow efficiency and work-item age are
uncomputable. `task_event` (see `bristol/schema.sql`) supplies the missing
moments from its `status` and `stage` rows; it cannot be backfilled, so early
reports state their coverage rather than averaging whatever rows happen to
exist.

Percentiles use nearest-rank, and the reported pair is median + 85th. That is
the flow-metrics convention because completion times are right-skewed: the
median is the typical case, the 85th is what can honestly be promised, and a
mean is just one stalled card away from being a lie.

## Where reports go

Resolved in `paths.py`, on the order
`src/tools/config_tools/instance_pointer.py` states:

1. `BRISTOL_REPORTS_DIR` — an explicit override, for testing.
2. The per-machine instance pointer, whose `config_path` names the config file
   even when Bristol runs as a relocated `.app` that cannot see the repo.
3. `bristol/bristol_reports.local` — a git-ignored one-line absolute path,
   bundled into older `.app` builds.
4. `markdown_notebook.reports_dir` in the `config.local.json` found by walking
   up the source tree.

Nothing resolving means no report and no failure. The archive sweep commits
before the report runs, so a missing notebook costs a report, never a board
action.

## Running it by hand

```bash
python3 generate.py --stdout         # preview the Done column, write nothing
python3 generate.py --last-batch     # re-report the last sweep
python3 generate.py --ids 117,118    # specific cards
python3 generate.py --out-dir /tmp   # write elsewhere
python3 generate.py --db /path/to/tickets.db
python3 generate.py --no-index       # skip the index rebuild
```

## Module layout

| File | Responsibility |
| --- | --- |
| `paths.py` | Where the report goes. The only module that knows about out-of-repo locations, and it hardcodes none. |
| `metrics.py` | DB → a dict of computed facts. No I/O, no formatting. |
| `render.py` | That dict → Markdown. No DB, no computation. |
| `generate.py` | Orchestration, period boundaries, CLI. |

Each piece is independently testable, and the note restyles without touching a
calculation.

## Rules

- **Write the summary from rules, never generate it.** It runs behind a Qt
  button with no network and must produce identical words for identical
  numbers.
- **Draw charts in block characters.** They render in preview, in source, on a
  phone, and in a diff.
- **Take a period's start from the previous report's `period_end`**, read out of
  its frontmatter. A report is an artefact, not state — `src/app.md` §The board
  is the only channel — so nothing about the series is stored elsewhere, and
  deleting the folder starts a fresh one.
- **Give every finding a number and an action.** Thresholds live at the top of
  `metrics.py` and in `_signals`.
