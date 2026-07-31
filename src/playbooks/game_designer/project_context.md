# project_context.md — game_designer playbook

**Always-on, not triggered** — read at the start and close of every session,
the same way `career_coach`'s `session_closure.md` and `writers_room`'s
`project_context.md` are. This is the project-content counterpart to the
charter's standard tickets-db check, which happens first (per the
charter's §2.1).

## Session start

1. After the standard tickets-db check (including backlog cards assigned to
   you), identify the active game
   project. `config/config.local.json`'s Code Projects table resolves which
   project folder is active; there may be more than one project tracked
   over time, so confirm which one the user means if it isn't obvious from
   context.
2. The tickets-db check already surfaced that project's epic (name,
   `status`, `description`, `next_action`) and its ordered task queue —
   that *is* the phase/blockers/next-focus summary; don't look for a
   separate project-local state file to re-derive it from. Echo a short
   summary before waiting on the user: current phase, open blockers (open
   tasks on the epic), and — if useful — the last handful of locked decisions
   (see step 3).
3. For recent design decisions, read the game_designer cards on the board (what the last
   session worked on). Durable worldbuilding lives in the user's notebook
   (read-only; see On-demand lookup); mechanics/art live in the repo `design/`.
   There is no 'canon' record or separate decision log — see `design_proposals.md`.
4. Do **not** bulk-read the notebook or the repo `design/` at session start.
   On-demand lookup only (see below).
5. The user's notebook worldbuilding wiki is a **read-only lookup resource**, not
   a standing context source: read a specific note when a request needs that fact,
   don't sweep it at session start, and never write into the wiki dirs. To propose
   a page/fact, write a summary to the shared agent-output dir
   (`markdown_notebook.agent_output_dir`)
   for the user to review — see `design_proposals.md`.
6. **Exception:** if this particular project has its own pre-existing, frozen
   local state file (see the charter's §2.2 exception note), read that too.
   This is a per-project fact to confirm, not a default to assume.

## On-demand lookup

When a request needs a project fact not already in hand, look it up in the
right home:

- **Worldbuilding** → the user's notebook, in the wiki directory this project
  names in `/config`. That directory's root map-of-content note and its
  wiki-links are the index.
- **Mechanics / art** → the repo `design/` folder's own file names.

Read **one** target file per question. Needing three files to answer one
question means the request is under-specified — ask, don't keep reading.

**Do not assume a project's data root doesn't exist just because it isn't
where a stale reference expected it.** If a project's own files point at a
personal/instance data location that isn't found on a first bounded search,
say so and ask the user rather than concluding it never existed — legacy
references are frequently stale pointers to real, still-existing content
that simply moved or was never where an old note claimed. Confirm before
treating any project as data-less.

## End of session

On "end of session," "update everything," or the natural end of a design
session:

1. Update the project's board epic: `status`/`next_action` if the phase or
   immediate focus changed, via `ticket_write.py` (there is no
   `update-epic` subcommand yet — ask before hand-editing
   the db directly, or flag the gap via a `backlog` card assigned to
   `chief_of_staff`).
2. Put where-things-stand on the cards, not in a note. There is no handoff
   mechanism: the next session learns the state from the board. Anything the
   next session should pick up is a `doing` card at the top of its column and
   `assignee: game_designer`; a one-line `add-issue-log` comment carries the
   detail. Durable design facts go in the project's bible, never on a card.
3. If a decision resolves an open task, close it via `ticket_write.py
   update-task-status --id N --status done` rather than leaving it to go stale
   in the queue.
4. If the session reached a structural milestone (a design phase closing, a
   first buildable slice), see `git_milestone_coaching.md` before ending.

**Model:** this project's worldbuilding
lives in the user's wiki-linked Markdown notebook as its single home
(resolved via `config`'s `markdown_notebook`); the repo's `design/` holds only
game-design/production files (mechanics + art). There is **no 'canon' concept** —
game_designer reads the notebook wiki as a read-only lookup resource and never
writes into those wiki dirs; to propose a page/fact it writes a summary to the
shared agent-output dir (`markdown_notebook.agent_output_dir`) for the user to
review and fold in. The
session-start, on-demand-lookup, and `design_proposals.md` steps above already
reflect this. Don't recreate a project-local state/tracking bundle for a new game
project — the tickets db is the default; a project-local state file is the
exception requiring its own justification.
