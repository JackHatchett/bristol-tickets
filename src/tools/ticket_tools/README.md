# Ticket Tools

The non-UI ticket utilities used by agents and system processes. This file owns
the board's *mechanism*: schema, CLI surface, storage semantics, and the
conventions that describe how the data is shaped. The behavioural rules an agent
must hold at all times — queue precedence, the `doing` rule, the board as the
only channel, what a file may say — are owned by `src/app.md`, which loads at
every session start; this file references them and never restates them. Style
contract for both: `src/templates/identity_template.md`.

## Invariants

- **No personal data.** Never a literal username, home directory, or
  cloud-provider path. A directory representing a user is `<instance>`.
- **Stable project-relative paths.** Find the project root by marker (the
  nearest ancestor holding `src/app.md`) and resolve everything relative to the
  tool's own location — no environment variables, no config files, no external
  path sources.
- **Canonical DB discovery.** The tickets database is the first match under
  `data/*/tickets/tickets.db`. Never assume the name of `<instance>`.
- **One shared database per instance, never one per agent.** Scope an agent by
  tagging, not by storage: `epic.owner` holds the slug that owns an epic (or a
  descriptive string for genuinely shared work), and a task's owner is its
  `assignee`, else its epic's. Onboard an agent with
  `ticket_write.py add-epic --owner <slug>`; never provision a second database
  under `data/<agent>/tickets/`. First-glob-match discovery is safe precisely
  because exactly one `tickets.db` exists per instance.
- **Use Python's built-in `sqlite3` module, never a `sqlite3` CLI subprocess.**
  // A sandboxed runtime often carries no `sqlite3` binary, and the module is
  // always there. This binds ad-hoc DB inspection too.
- **Open every write with `PRAGMA journal_mode=MEMORY`** (see `ticket_write.py`).
  // Where the database is reached across a file bridge rather than on the
  // running machine, a default-journal write can fail mid-write and leave a
  // stuck rollback-journal file that blocks all further access, reads included,
  // until it is cleared by hand. MEMORY mode writes no on-disk journal.
- **Write the database in place, never by replacing the file.** A copy
  delivered over a file bridge unlinks the old inode, and a viewer already
  holding it goes on reading the dead one.
  // Refresh in Bristol Tickets re-queries that handle, so a stale board
  // survives every refresh and reads as writes that never landed. Relaunching
  // the viewer shows them all at once.
- **Keep the schema in step with Bristol Tickets.** Any inline migration the
  viewer performs is reflected in `create_tickets.py`.
- **These are not user-facing commands.** They are internal mechanisms for
  agents and automation.
- **Any tool added here obeys the same invariants.**

## Tools

### cos_status.py
Status snapshot for `chief_of_staff`. Prints the milestone and active epics
(fleet-wide), the active-board size (`stage='active'`), then chief_of_staff's
own next action and queue, then a **FLEET** section of active-board tasks owned
by other agents — coordination visibility only, never its own queue.

### agent_status.py
The same reader for every other agent, requiring an `agent_slug` argument
(`python3 agent_status.py career_coach`). Scoped to that agent's own epics and
cards. It shares the `owned_by`, active-stage and precedence logic with
`cos_status.py`; the two stay in lockstep.

Both scripts implement the selection rule in `src/app.md` Phase 3 and are
authoritative over any prose restatement of it. **Read the database directly
only where one of them errors, the database was just created, or the user asks
for history the snapshot omits.**

### create_tickets.py
`python3 create_tickets.py --instance <name>` provisions an empty tickets
database under `data/<instance>/tickets/` with the full schema the viewer
expects, and errors if the target already exists. It writes no config and
assumes no external path source. This provisions a brand-new *instance*; giving
an existing instance's agent a presence on the board is `add-epic`, not this
script.

- **A new board is created empty.** A seeded epic or sample task is invented
  content — `src/templates/identity_template.md` §Data locations.
- **`provision()` and `locate_or_provision()` live here too**, and are what
  every other ticket tool calls when it finds no database at all.

### ticket_write.py
The safe write helper — `add-epic`, `update-epic`, `add-task`, `update-task`,
`update-task-status`, `set-stage`, `set-order`, `add-issue-log` and the `link-*`
subcommands. Prefer it over inline SQL from a session. `connect()` self-heals
the `issue_log` table and the Kanban `stage` / `sort_order` columns into older
databases, mirroring the viewer's `ensure_schema_up_to_date()`.

- **`add-task` lands a new card where `board.new_ticket_stage` says**, unless
  `--stage` names a tab, and always in `--status todo`. The key defaults to
  `active`, the Board where a card is seen and worked; an explicit `--stage`
  always wins.
- **`update-epic --id N` edits what an epic *says*** — `--name`, `--type`,
  `--status`, `--owner`, `--approver`, `--description`, `--hard-constraints`,
  `--definition-of-done`, `--detail-path`, `--next-action`. It reaches the same
  fields Bristol Tickets' epic dialog writes, and sets `closed_at` when a status
  in `EPIC_STATUS_FINISHED` is given. It touches no task.
- **`update-task --id N` edits what a card *says*** — `--title`,
  `--description`, `--estimate`, `--record-type`, `--reporter`, `--epic-id` —
  and touches no board position.
- **`update-task-status --id N --status ...`** moves a card across the Kanban
  columns, setting and clearing `closed_at` on the `done` transition. It also
  takes `--stage`, `--pressure`, `--assignee` and `--block-reason` in the same
  call. A bare `--status backlog` is redirected to a stage move. A call naming
  the column a card already sits in keeps its position; only a real move re-seats
  it at the bottom of its destination. `--block-reason none` clears the reason,
  and so does `--status done`, which refuses an explicit reason in the same
  call.
- **`set-stage --id N --stage backlog|active|archive`** moves a card between
  tabs, appending it to the bottom of the destination's order. It is the CLI
  equivalent of the viewer's Board "Bulk Change" and the Backlog "Activate".
- **`set-order --id N --position K`** moves a card within its own list — one
  active-board status column, or the whole backlog — with position 1 the top,
  renumbering contiguously afterwards. It is the only thing that reorders an
  agent's queue.
- **Keep each new subcommand single-purpose** rather than merging into one large
  CLI.

## The change log (`task_event`)

Every change to a task field appends one row — the field, its new value, the
actor, an ISO timestamp — so the board shows what happened to a card without
anyone narrating it.

- **Every entry is machine-written.** Database triggers append them; no agent
  and no person composes one, explains a change, or adds a reason. An entry
  carrying prose has become the narration the change log exists to replace.
- **The append lives at the database layer**, so a drag, a Clear Done sweep, a
  record-dialog edit and a CLI call are all recorded identically.
  // Bristol Tickets writes to tickets.db directly, so a hook inside
  // ticket_write.py would miss every board move made by hand.
- **Actor** is `user` from Bristol Tickets and the `--actor` write signature
  from the CLI. Each connection installs the triggers in its own TEMP schema
  with its actor baked in.
  // A trigger in the main schema cannot read a temp table, so the actor cannot
  // come from a session variable at fire time.
- **Title and description record only that they changed** (`to_value` is
  `(changed)`) — never the old text, the new text, or a diff.
- **Repeated moves each get their own entry.** Back-and-forth is recorded as-is.
- **Not logged:** `sort_order` (a rendering position, re-seated by every column
  move), `closed_at` (implied by `status`), `created_at`, `updated_at`.
- **`updated_at` derives from the newest entry** rather than being maintained by
  each writer.
- **Pass `--actor <your agent slug>`** on `add-task`, `update-task-status`
  and `set-stage`. It is optional and analytics-only; omitting it never changes
  board state.

This log loosens nothing in `src/app.md` §What a file may say: files still carry
no history, and no agent writes a change note anywhere outside it.

Two readers. Bristol Tickets' Log pane interleaves these entries with
`issue_log` comments under a pair of filter checkboxes, both on by default.
`bristol/reports/` measures cycle time, flow efficiency and work-item age from
the `status` and `stage` rows — `created_at` / `updated_at` / `closed_at` alone
yield only lead time. The log cannot be backfilled, so its metrics cover moves
made after it existed.

## Board conventions

How the data is shaped, for every agent and the viewer alike. The rules for
*acting* on it are `src/app.md` Phase 3.

**Two orthogonal fields.** Every task has a **stage** (which tab it lives in)
and a **status** (which board column):

- `stage` — `backlog` | `active` | `archive`.
  - `backlog` — real work, "get to it whenever," not on the board. The Backlog
    tab is one manually-ordered list; new cards append to the bottom
    (`task.sort_order`).
  - `active` — on the board, in play right now.
  - `archive` — retired. The Archive tab is a stripped chronological list,
    most-recently-modified first.
- `status` — the board column, meaningful for active-stage tasks:
  - `todo` — queued and intended for the current push.
  - `doing` — in progress in the literal sense: partway through executing a
    chained series of actions. If resuming means "continue a sequence already
    underway," it is `doing`.
  - `done` — finished; `closed_at` is set.

`backlog` is not a *status* value; it lives on the stage axis, and the CLI
redirects `--status backlog` to a stage move.

**An epic's status has one vocabulary** — `not started`, `in progress`,
`completed`, `on hold` — the set Bristol Tickets' epic dialog writes, held as
`create_tickets.EPIC_STATUS_CHOICES` and used by `add-epic`. The status scripts
read it through two sets beside it: `EPIC_STATUS_IN_FLIGHT` is what they list as
the active epics, and an epic outside `EPIC_STATUS_FINISHED` still carries its
backlog into an agent's fallback queue. Both sets also carry the spellings
retired versions wrote, so one long-lived database needs no second lookup.

**Order, blockers and pressure are three separate mechanisms** (`src/app.md`
Phase 3.3 states the rule). Their storage:

- **Order** is `task.sort_order`, a card's position in its column. The user sets
  it by dragging in Bristol Tickets; an agent sets it with `set-order`.
- **A blocker** is a `blocks` link between two named cards, resolved live
  against the blocking card's status. Once that card is `done`, its own last
  comment reads through the same link onto the card it blocked — a join at read
  time, so the handoff is never a second copy of the comment. It never moves a card in the queue —
  precedence keeps a `doing` card first even when it is waiting on a `todo` one.
  Only the user drops the link or waves a card past an unmet blocker.
- **A block reason** is `task.block_reason`, one of `dependency`, `decision`,
  `capability`, `transient`, or NULL for a card nothing is holding up. It says
  what *kind* of thing is in the way and never which card: a `dependency` sends
  the reader to the `blocks` links above, so a blocker that finishes clears the
  display with no field to reset. The prose goes in an `add-issue-log` comment,
  which is where the ungranted tool or the failed call gets named. `decision` and
  `capability` are the two the status scripts list under NEEDS YOU, because no
  agent can clear either by working. The vocabulary is
  `create_tickets.BLOCK_REASONS`, mirrored in `bristol/ui/theme.py`. A card
  reaching `done` has its reason cleared by every writer.
- **Pressure** is `task.pressure`, 0–100: urgency, impact and live interest
  collapsed into one gestalt reading, written for a human eye. It is
  agent-local, so a card low in the order carrying high pressure is a question
  worth asking, and a comparison across assignees is meaningless. Only the user
  sequences work across agents.

**The operational tell for `doing`:** if you have read into a ticket and left a
comment on it, it is `doing`. At session end every card you engaged resolves to
`done` or `doing` — never `todo`. Leaving worked tickets in `todo` is the single
most common board-hygiene failure. (Broader than the chained-execution sense
above: that sense governs what you *carry forward*, this governs the working
state of anything you touched.)

**A card is the handoff.** There is no `add-handoff` subcommand, no `handoff`
table, and no Handoff tab; `schema_guard._drop_retired_handoff` drops the table
from any database that carries one on launch. Leave work mid-flight by putting
its card on the active board in `doing`, at the top of its column, with the
owning agent as `assignee` — the status scripts rank exactly that first. What
remains goes in the card's description or one short `add-issue-log` comment. A
narrative block answering "where do things stand" is work state living outside
the cards; storing it inside `tickets.db` does not make it board data, and it
gives every session a second place to look.

**A file an outside party needs is a payload, not a channel.** When something
that genuinely cannot read `tickets.db` — an external service shown a JSON
envelope — needs the data in a file, a ticket names that file, the ticket holds
the state, and deleting the file loses nothing. Never scan a payload to discover
work.

**Every ticket is a Build or a Fix** (`task.record_type`, default `build`). A
*Build* is a thing to build, described as a Story plus acceptance criteria; a
*Fix* is a broken thing, described as Expected and Observed. Set it with
`add-task --record-type fix` or in the viewer's Create dialog. The skeletons and
their precedence rules live in `src/skills/manage-tickets/SKILL.md`
§Record types: Build vs Fix.

**Keep a ticket single-outcome** — one Build or Fix per outcome, split rather
than combined.

**A Description holds its template and nothing else.** When *you* write or edit
a ticket body it contains exactly the Build or Fix skeleton: nothing above it,
nothing after it, no extra headers, no provenance line, no note to the reader,
no options-and-recommendations essay. You may rewrite a Description and its
criteria freely (`update-task --id N --description "…"`) — but only into that
shape. Everything else has a home: elaboration, findings and what is needed next
go in an `add-issue-log` comment; provenance and related material go in a link.

**This binds agents, never the user.** A user-authored Description that ignores
the template is not yours to "fix." What you may do is add the links and
comments that make it legible.

**The active board can span epics.** A task's stage, not its epic, is what puts
it on the Board, so the active set may cross several epics while other tasks in
those same epics stay in backlog.

**Cross-zone requests are cards, not commands.** An agent authors board tasks
freely for itself or the user within its own zone. Anything landing in another
agent's decision domain is an `add-task` with `--assignee` = that agent and
`--reporter` = you — an ordinary card in `todo`, and the `assignee` is what
makes it a request rather than an order: that agent's card to accept, reorder,
or drop. Which tab any new card lands in is the user's, not the agent's: `add-task`
reads `board.new_ticket_stage` from config — `active` by default, `backlog` if
the user prefers — whenever no `--stage` is given, whoever files the card and
whoever it is for. Bristol Tickets' Settings tab is where that choice is made. The
`librarian` does not put "delete the xyz database" in `doing` for
`chief_of_staff`; it files a `todo` card assigned to `chief_of_staff`, reporter
`librarian`. There is no separate suggestion store, subcommand, or status
section — `reporter` and `assignee` already carry it.

### Format — scannable in ~10 seconds

Every comment and ticket description obeys these; the board is a status surface
a human skims, not a log.

- **Bullets, not paragraphs.** One idea per bullet, ≤ ~15 words.
- **2–4 short headers.** Ticket: `Goal` / `Done so far` / `Needs next`.
- **Hard length cap.** Past ~10 lines or ~8 bullets, cut it, or move durable
  detail to the file that owns it — charter, playbook, README, config.
- **Write the current state, not a history of every step.**

## Links (`task_link`)

A link is the relation a ticket carries to something else. Two kinds, one table,
both created with `ticket_write.py link-add --task N`:

- **`--to-task M` links two tickets.** Stored as ONE row, so it appears on both
  tickets the moment it is written and both read it with
  `WHERE task_id=? OR other_id=?`. Never run the mirror call, and note that
  `link-remove` clears it from both ends at once — bidirectionality is a
  property of the storage, not a pair of writes that could drift apart.
  - `--type related` (the default) means they belong together. The row is
    normalized so `task_id` is the lower id, because it reads the same from
    either card.
  - `--type blocks` / `blocked-by` means a dependency: `--task N --to-task M
    --type blocks` says N must be `done` before M may start, and `blocked-by` is
    the same sentence from the other end. Both store the one directed row
    (`task_id` blocks `other_id`), rendering as `blocks #M` on one card and
    `blocked by #N` on the other.
  - Re-running `link-add` on an already-linked pair **retypes** it rather than
    erroring, so changing a relation is one call.
- **`--uri "…"` links to an address** — a web URL, a `zotero://` citation, an
  `obsidian://` note, or a filesystem path. Bristol Tickets hands whatever is
  stored to the OS to open, so the tool encodes no schemes, vault names or user
  paths. Add `--label` for a caption.

`link-list --task N` prints link ids and how each reads from that ticket;
`link-remove --id L` deletes one. Bristol Tickets shows links above the Issue
Log in both the inspector and the create/edit dialog, offering the relation from
the open ticket's point of view, and the status scripts print them in a `LINKS`
section.

**A dependency is the one mechanism for "not yet."** There is no `blocked` flag
and no `depends_on` column: a stored flag has to be cleared by hand and sits
lying about a blocker that finished long ago. The status scripts resolve a
blocker live and print `[BLOCKED by #N]` only while it is genuinely unmet.

**Link, don't narrate.** "This came from the 2026-07-27 system review" is a link,
not a sentence in a Description. "Related to #153" is a link, not a bullet.
Reading a ticket's links before executing it is `src/app.md` Phase 3.4.

## Directory Structure

```
<project-root>
    src/tools/ticket_tools
        cos_status.py
        agent_status.py
        create_tickets.py
        ticket_write.py
        README.md
    data/<instance>/tickets
        tickets.db   tables: theme, epic, scope, task, task_meta,
                     issue_log, attachment, task_event, task_link
                     (task carries stage + sort_order for the Kanban board)
```
