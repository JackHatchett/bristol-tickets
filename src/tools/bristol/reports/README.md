# Bristol Reports

The analytic report Bristol writes to the user's Markdown notebook every time
the board's **Clear Done** button sweeps finished cards into the Archive.

## Why Clear Done

A Kanban board has no sprints, so it has no natural period boundary — which is
why most personal boards never produce delivery analytics at all. Clear Done is
the closest thing this board has: a batch of finished work leaving together, at
a moment the user deliberately chose. Treating it as the close of a period gets
the reporting cadence for free, and ties it to an action the user already takes.

## What it produces

One note per sweep, plus a rebuilt `_index.md`:

```
<notebook>/41_ai_workspace/bristol_reports/
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

Resolved in `paths.py`, in order:

1. `BRISTOL_REPORTS_DIR` environment variable
2. `bristol/bristol_reports.local` — a git-ignored one-line absolute path,
   bundled into the built `.app` (which cannot see the repo's `config/`)
3. `config.local.json` → `markdown_notebook.reports_dir`

If none resolve, no report is written and nothing fails. That is the rule
throughout: the archive sweep has already committed before the report runs, so
a missing notebook costs a report, never a board action.

## Running it by hand

```bash
python3 src/tools/bristol/reports/generate.py --stdout        # preview the Done column
python3 src/tools/bristol/reports/generate.py --last-batch    # re-report the last sweep
python3 src/tools/bristol/reports/generate.py --ids 117,118   # specific cards
python3 src/tools/bristol/reports/generate.py --out-dir /tmp  # write elsewhere
```

## Module layout

| File | Responsibility |
| --- | --- |
| `paths.py` | Where the report goes. The only module that knows about out-of-repo locations, and it hardcodes none. |
| `metrics.py` | DB → a dict of computed facts. No I/O, no formatting. |
| `render.py` | That dict → Markdown. No DB, no computation. |
| `generate.py` | Orchestration, period boundaries, CLI. |

The split keeps each piece independently testable and lets the note be
restyled without touching a calculation.

## Design notes

**The summary is rules-based, not generated.** It runs behind a Qt button with
no network, it must produce identical words for identical numbers, and a
summary that can hallucinate is worse than none.

**Charts are block characters.** They render in preview, in source mode, on
mobile, in a git diff, and in whatever reads Markdown in ten years.

**Period boundaries live in the artefacts.** A period runs from the previous
report's `period_end`, read back out of its frontmatter. Nothing is stored
anywhere else — the repo's standing rule is that `tickets.db` is the only place
state lives, and a report is an artefact, not state. Delete the folder and the
next report starts a fresh series.

**Findings name a number and an action.** A finding with neither is decoration.
Thresholds live at the top of `metrics.py` and in `_signals`.
