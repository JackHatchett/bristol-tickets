# Ticket Tools

This folder contains the non‑UI ticket utilities used by agents and system processes. All tools in this directory follow strict invariants:

1. No personal data  
   Tools never contain literal usernames, home directories, or cloud‑provider paths. Any directory that represents a user is referred to generically as <instance>.

2. Stable project‑relative paths  
   All tools find the project root by marker (the nearest ancestor holding `src/app.md`). Paths are resolved only by walking relative to the tool’s own location. No environment variables, no config files, and no external path sources are used.

3. Canonical database discovery  
   The tickets database is always discovered using the following rule:  
   data/<instance>/tickets/tickets.db  
   Tools search for the first matching tickets.db under data/*/tickets/.  
   Tools never assume the name of <instance>

3c. One shared database per instance, not one per agent  
   There is a single tickets.db per instance, shared by every agent in the
   fleet — not a separate database per agent. Agent-level scoping is done by
   tagging, not by separate storage: `epic.owner` holds the agent slug that
   owns an epic (or a descriptive multi-agent string for genuinely shared
   work), and a task's ownership is its `assignee` (else inherited from its
   epic). Cross-agent suggestions are ordinary active-board cards
   (`assignee` = the target agent, `reporter` = the originator), not a separate
   store — see "Cross-agent suggestions" below. "First glob match" under
   invariant 3 is safe specifically because exactly one tickets.db should exist
   per instance. When onboarding a new agent, give it an epic via
   `ticket_write.py add-epic --owner <slug>` — never provision it a second
   database under a different data/<agent>/tickets/ path.

3a. Environment  
   // Tools use Python's built-in `sqlite3` module, never a `sqlite3` CLI
   // subprocess call — the CLI binary is not guaranteed to exist in every
   // execution environment (e.g. sandboxed Cowork runtimes lack it). Anyone
   // extending this folder or doing ad-hoc DB inspection should follow suit.

3b. Write safety over mounted-folder bridges  
   Any tool that writes to the DB opens with `PRAGMA journal_mode=MEMORY` (see
   ticket_write.py).
   // A default-journal write from a sandbox session, over the bridge to the
   // user's real filesystem, can fail mid-write and leave a stuck
   // rollback-journal file that blocks all further access, reads included,
   // until it is cleared by hand. MEMORY mode writes no on-disk journal.

4. Schema consistency  
   The database schema created or read by these tools matches the schema used by Bristol (the viewer UI). Inline migrations performed by the UI are reflected in the schema used by create_tickets.py.

5. No user‑facing commands  
   These tools are not intended for direct user invocation. They are internal mechanisms used by agents or future automation layers.

## Tools Overview

### cos_status.py  
Machine‑readable status snapshot for the chief_of_staff agent. Prints
milestone and active epics (fleet-wide context), the active-board size
(stage='active'), then **chief_of_staff's own next action + own active-board
queue** (see "How the next action is selected" below), a separate **FLEET**
section listing active-board tasks owned by *other* agents for coordination
visibility only. Uses canonical DB discovery.

The next-action selection is scoped (own +
active-board) per the rule below; other agents' work is context only.

### agent_status.py  
Status reader for non‑CoS agents, required to take an `agent_slug` argument
(e.g. `python3 agent_status.py career_coach`). Prints milestone (fleet-wide),
this agent's own active epics, the active-board size, and **this agent's own
next action + own active-board queue** using the identical selection rule as
cos_status.py (kept in lockstep — the two scripts share the same
`owned_by` / active-stage / precedence logic). Uses canonical DB discovery.

### How the next action is selected (every agent, every session)  
Both status scripts answer "what should *this* agent do next" the same way.
It is **not** the global top of a fleet-wide list. Precedence:

1. active-stage tasks the agent owns, status `doing` (board order — top of
   the column first);
2. then active-stage tasks the agent owns, status `todo` (board order);
3. only if 1+2 are empty, the agent's own `backlog` (stage='backlog') —
   surfaced as a planning signal (activate onto the board / confirm with the
   user), not auto-executed.

"Owns" = `task.assignee` equals the agent slug, or (when a task has no
explicit assignee) its epic `owner` names the agent (substring match, since
`owner` is sometimes a descriptive multi-agent string). **Tasks owned by other
agents are never a given agent's next action** — cross-zone work travels as an
active-board card assigned to the owning agent, never by silently picking up
someone else's board task. A task's **stage** (backlog | active | archive) —
not any sprint — decides what's in play;
stage is orthogonal to the epic, so the active board can span epics.

### create_tickets.py  
Provisioning tool for creating a new tickets database under data/<instance>/tickets/.  
Creates a fully robust schema matching the UI’s auto‑migrated structure (`issue_log`, `attachment`, `task_event`, etc.; no `inbox` and no `handoff` table).  
Seeds the database with an initial epic and default tasks.  
Throws an error if the target database already exists.  
Does not write any config files or assume any external path sources.  
This provisions a database for a brand-new *instance* of the whole system —
not a second database for an individual agent within an existing instance
(see 3c). Giving an existing instance's agent its own presence on the board means
`ticket_write.py add-epic`, not this script.

### ticket_write.py  
Safe write helper — `add-epic`, `add-task`, `update-task-status`, `set-stage`,
and `add-issue-log` subcommands. (There is deliberately no `add-handoff`; see
"There is no handoff" below.) Uses
`journal_mode=MEMORY` (see 3b) instead of ad-hoc raw sqlite3 writes.
`connect()` self-heals the `issue_log` table and the Kanban `stage`/`sort_order`
columns into older DBs that predate them, mirroring the UI's
`ensure_schema_up_to_date()`. Preferred over inline/one-off write queries from
an agent session. `add-epic --owner <slug>` is how a new or existing agent gets
its own tagged epic in the shared db (see 3c). A task's owner is its
`--assignee` (else implicit via its `--epic-id`'s epic); set `--assignee` on an
`add-task --stage active` to leave a cross-agent suggestion on the Board (filed
active, not backlog). A task carries two orthogonal fields:
`--stage` (backlog | active | archive — which tab) and `--status`
(todo | doing | done — the board column); `add-task` still defaults to the
backlog stage, but agents pass `--stage active`
so new to-dos land on the Board in `todo` (see Board conventions below).
`update-task-status --id N --status ... [--stage ...] [--pressure N]
[--assignee ...]` moves a task across the Kanban columns (sets/clears
`closed_at` on the done transition; a bare `--status backlog` is redirected to a
stage move); `set-stage --id N --stage backlog|active|archive` moves a task
between tabs, appending it to the bottom of the destination's order (the CLI
equivalent of the viewer's Board "Bulk Change" and the Backlog "Activate").
`set-order --id N --position K` moves a task within its own list — one
active-board status column, or the whole backlog — with position 1 the top; the
list is renumbered contiguously afterwards. It is the CLI equivalent of
dragging a card up or down a column, and it is the only thing that reorders an
agent's queue.
Intended to grow more subcommands (close-epic, etc.) as repeated session actions
get identified — keep each addition single-purpose rather than merging into one
large CLI.

(There are no `assign-sprint` or `set-sprint-status` subcommands; stage moves
are used instead.)

(There is no `add-epic-log` subcommand or `epic_log` table — that was a
misnamed per-agent handoff-plus-log, unrelated to the Epic *concept*; its role
is covered by the per-agent `handoff`
(current state) and ordinary issues (to-dos / done-items). The
"ledger discipline" some playbooks referenced now means: record the durable
fact where it truly lives — a project's own canon/bible file, an issue, or the
agent's own cards — not a parallel DB log.)

## The change log (`task_event`)

A ticket carries its own movement history. Every change to a task field appends
one row to `task_event` — the field, its new value, the actor, an ISO timestamp
— so the board shows what happened to a card without anyone narrating it.

**Every entry is machine-written.** Database triggers append them; no agent and
no person composes one, explains a change, or adds a reason. The grammar is
fixed. An entry carrying prose has become the thing the no-narration rule bans.

- **Both writers are covered.** Bristol writes to `tickets.db` directly, so a
  hook inside `ticket_write.py` would miss every board move made by hand. The
  append is at the database layer instead, and a drag, a Clear Done sweep, a
  record-dialog edit and a CLI call are all recorded identically.
- **Actor.** Each connection installs the triggers in its own TEMP schema with
  its actor baked in — `user` from Bristol, the `--actor` write signature from
  the CLI. // A trigger in the main schema cannot read a temp table, so the
  actor cannot come from a session variable at fire time.
- **Title and description record only that they changed** (`to_value` is
  `(changed)`). Never the old text, the new text, or a diff — a change log
  records movement, not a second copy of the ticket.
- **Repeated moves each get their own entry.** Back-and-forth is recorded
  as-is, never collapsed.
- **Not logged:** `sort_order` (a rendering position, re-seated by every column
  move anyway), `closed_at` (implied by `status`), `created_at`, `updated_at`.
- **`updated_at` derives from the newest entry** rather than being maintained by
  each writer.

This is a bounded, mechanical record the user asked for, not a licence to
narrate: it loosens nothing else. Files still carry no history, and no agent
writes a change note anywhere outside this log.

Two readers. Bristol's Log pane interleaves these entries with `issue_log`
comments under a pair of filter checkboxes, both on by default. `bristol/reports/`
measures cycle time, flow efficiency and work-item age from the `status` and
`stage` rows — `created_at` / `updated_at` / `closed_at` alone can only yield
lead time (raised → closed). The log cannot be backfilled, so metrics are
meaningful only for moves made after it was added.

Pass `--actor <your write signature>` on `add-task`, `update-task-status` and
`set-stage` so the log can distinguish fleet moves from the user's own. It is
optional and analytics-only — omitting it never changes board state.

## The board is the only channel (shared — every agent, every session)

This is the system's first rule and every convention below is downstream of it.

**Work state lives in `tickets.db` and nowhere else.** What is done, what is
next, what is in progress, what is awaited, who owes whom, in what order — all
of it is board data. No file, folder, JSON field, note, README, or chat message
is a second home for any of it.

**Apply the content/state test before writing anything.** A file may describe
*content* — what exists, what it is called, what it says. A file may never
carry *work state*. The bright-line violation is **deriving a next action, a
ordering, or an in-progress fact from anything but the board.** If you are
scanning a folder, reading a status field out of a JSON file, or taking "the
latest file by name" to decide what to do, you are reading a second tracker and
it will disagree with the board.

Three consequences, each of which has been violated in this repo before:

- **Agents task each other with tickets only.** A card with `assignee` = the
  other agent and `reporter` = you. Never a file, never a folder drop, never a
  note left for them to find, never a request relayed through the user.
- **No summary of the board outside the board.** Never write a ticket list, a
  ordering table, a "what I filed" recap, or a status roll-up into a note,
  report, or README. A report may hold analysis; it may not hold task state.
- **Never make the user the transport.** Nothing may be designed so the user
  carries work between the board and an agent — copying a ticket out, pasting
  it in. Agents read the board themselves.

**Payloads are not channels.** A file that exists because an outside party
genuinely cannot read `tickets.db` (a JSON envelope shown to an external LLM)
is a payload: a ticket names it, the ticket holds the state, and deleting the
payload loses nothing. It is never scanned to discover work.

**No phases, no deferral in prose.** Never scope work as "phase 1 / phase 2,"
and never write "later," "next pass," "not in this ticket," or "TODO" into a
file or a ticket body. Either it is this ticket's scope or it is another card.
Prose that promises future work is an untracked to-do.

## Board conventions (shared — every agent, every session)

The tickets DB is the whole fleet's — and the user's — single shared
state-tracking board. Every agent reads and writes it; the viewer renders it.
These conventions govern how any session leaves the board so the next one (a
new day, a different model, a different agent) and the user both see an
honest picture without being re-briefed. They are app-level, not any one
agent's private protocol.

**Two orthogonal fields (the Kanban model).** Every task has a
**stage** (which tab it lives in) and a **status** (which board column):

- `stage` — `backlog` | `active` | `archive`.
  - `backlog` — real work, but "get to it whenever." Not on the board. The
    Backlog tab is one manually-ordered list (drag to reorder; new cards append
    to the bottom — `task.sort_order`). **Agents do not file NEW to-dos
    here — every new card goes onto the active Board in `todo` (`add-task
    --stage active`). Existing backlog cards remain.**
  - `active` — on the board, in play right now.
  - `archive` — retired/historical. The Archive tab is a stripped chronological
    list, most-recently-modified first.
- `status` — the board column, meaningful for active-stage tasks:
  - `todo` — queued and intended for the current push.
  - `doing` — **in progress in the literal sense**: you are partway through
    executing a chained series of actions. Not a top-N wish list, not "a few
    lines got written." If resuming means "continue a sequence already
    underway," it's `doing`; otherwise it isn't.
  - `done` — finished; `closed_at` is set.

('backlog' is not a *status* value — it lives on the stage axis. The CLI
still accepts `--status backlog` and redirects it to a stage move.)

**Order, blockers and pressure are three separate mechanisms.** Confusing any
two of them is how the board and the agent stop agreeing.

- **Order — `task.sort_order`.** A card's position in its column. This is the
  queue: the status scripts return it already sorted and numbered, and position
  1 is next. The user sets it by dragging in Bristol; an agent sets it with
  `set-order --id N --position K`. Nothing else decides what gets worked next.
- **Blockers — a `blocks` link.** A hard prerequisite between two named cards:
  this one may not start until that one is `done`. A blocker never moves a card
  in the queue. It exists precisely because order cannot express it — a `doing`
  card can be waiting on a `todo` one, and precedence keeps the `doing` card
  first. An agent that meets an unmet blocker stops on that card, names the
  blocker, and hands back to the user rather than working around it.
- **Pressure — `task.pressure`, 0–100.** How hard a card is pushing: urgency,
  impact and live interest collapsed into one gestalt reading. A rating, not a
  rank. It sorts nothing and gates nothing. It is written for a human eye — a
  card low in the order carrying high pressure is a question worth asking.

Pressure is agent-local: it is one agent's reading of its own cards, and
comparing numbers across assignees means nothing. Only the user sequences work
across agents; an agent orders its own queue and nothing else.

**Move a ticket to `doing` the moment you pick it up — before you comment, not
after.** The operational tell: **if you have read into a ticket and left a
comment on it, it is `doing`.** A ticket you are actively processing this
session must not sit in `todo`. At session end it resolves to exactly one of:
`done` (finished) or `doing` (genuinely carried forward per the carry-forward rule
below) — **never left in `todo` after you touched it.** Leaving worked tickets
in `todo` is the single most common board-hygiene failure; it forces the user
to clean up after every session. Do not do it. (This is broader than the
narrow "mid-chain execution" sense of `doing` above: that sense governs what
you *carry forward*; this rule governs the *working state* of anything you
engage this session.)

**Leaving in-progress work is how you hand off — no separate mechanism.** When
a session ends with chained work only partway done, put that task on the
**active board** (`set-stage --task... --stage active`, or
`update-task-status --stage active`) in `doing`, move it to the top of its
column (`set-order --id N --position 1`), and
set the owning agent as its `assignee` (`update-task-status ... --assignee
<slug>`). The viewer's Board shows only active-stage tasks, and the status
scripts rank your own active-stage `doing` first, so the next session picks it
up first. There is no "next-pickup pointer", no handoff note, and no per-agent
protocol layered on top of this — the card itself is the signal. Work that is genuinely
"whenever" stays in the `backlog` stage so it doesn't masquerade as in-flight.

**Record types — every ticket is a Build or a Fix (`task.record_type`).** A
*Build* is a thing to build (Description = a Story + Given/When/Then acceptance
criteria); a *Fix* is a broken thing (Description = Expected/Observed). Default
`build`. Set it with `add-task --record-type fix`, or in the viewer's Create
dialog. The exact Description skeletons and precedence rules — governing how
agents and the user write ticket bodies, not stored in the DB beyond the type
flag — live in `src/playbooks/manage_tickets.md` (§Record types). Keep tickets
single-outcome: one Build or Fix per outcome, not one mega-ticket.

**A Description holds its template and nothing else (agents only).** When *you*
write or edit a ticket body, the Description contains exactly the Build or Fix
skeleton — Story + Acceptance Criteria, or Expected + Observed. Nothing above
it, nothing after it, no extra headers. No `Source:` line, no "Addressed to
…", no preamble explaining where the ticket came from, no notes to the reader,
no options-and-recommendations essay. You may edit a Description and its
acceptance criteria freely — but only into that shape.

Everything that does not belong in the Description has a home:

- **Elaboration, reasoning, findings, "what I did / what's needed next"** →
  an `add-issue-log` comment. Comments are free-form human prose (still
  scannable in ~10 seconds, per §Format) and they are where you should write.
- **Provenance and related material** — the review that raised it, the sibling
  ticket, the Obsidian note, the citation, the web page → a **link**
  (`link-add`, below). That is what links are for and why they exist.

**This binds agents, never the user.** The user writes ticket bodies however
they like, and a user-authored Description that ignores the template is not
yours to "fix." What you may do is add the links and comments that make it
legible.

## Links (`task_link`)

A link is the relation a ticket carries to something else. Two kinds, one table,
both created with `ticket_write.py link-add --task N`:

- `--to-task M` — **a link between two tickets.** Stored as ONE symmetric row
  (normalized so `task_id` is the lower id), so it appears on both tickets the
  moment it is written and both read it with `WHERE task_id=? OR other_id=?`.
  **Never run the mirror call** — there is no second row, and `link-remove`
  clears it from both ends at once. Bidirectionality is a property of the
  storage, not a pair of writes that could drift apart.
- `--uri "…"` — **a link to an address**: a web URL, a `zotero://` citation, an
  `obsidian://` note, or a filesystem path. Bristol hands whatever is stored to
  the OS to open, so the tool encodes no schemes, vault names or user paths. Add
  `--label` for a caption.

`link-list --task N` prints link ids; `link-remove --id L` deletes one. Bristol
shows the same links above the Issue Log in both the inspector and the
create/edit dialog, and the status scripts print them in a `LINKS` section.

**Follow the links on a ticket before you execute it.** Same standing as an
attached image: the ticket text alone is deliberately incomplete now that
provenance lives here instead of in the Description.

**Link, don't narrate.** "This came from the 2026-07-27 system review" is a
link, not a sentence in a Description. "Related to #153" is a link, not a
bullet.

**The active board can span epics.** The board (stage='active') is the set of
things actively in play right now; those tasks may belong to several epics,
while other tasks in those same epics remain "whenever" backlog. A task's stage
— not its epic — is what puts it on the Board.

**Stay in your lane; cross-zone requests are cards, not commands.**
An agent may freely author board tasks for *itself or the user within its own
zone of responsibility*. Anything that lands in another agent's or the user's
decision domain also goes on the board — `add-task --stage active` with
`--assignee` = that agent/user and `--reporter` = you. It lands in `todo` on
the active board, where the user actually looks, and the `assignee` is what
makes it a request rather than a command: it is that agent's card to accept,
reorder, or drop. Examples: the `librarian` does not put "delete the xyz
database" in `doing` for `chief_of_staff`; it files a `todo` card assigned to
`chief_of_staff`, reporter `librarian`. A note for the novel is a card assigned
to `writers_room`, not a `doing` task saying "add a character who shoots
lasers." The `backlog` stage still means never-auto-executed and older cards
still live there, but nothing new is filed to it.

## Cross-agent suggestions

Cross-agent suggestions are ordinary active-board cards, not a separate store.
`task` already carries `reporter` (originator) and `assignee` (owner), so a card
assigned to another agent *is* a suggestion — a visible, user-editable one that
that agent sees at the top of its own snapshot. To suggest work for another
agent, write an `add-task --stage active` with `--assignee`/`--reporter`; there
is no separate inbox store, subcommand, or status section.

## There is no handoff

There is no `add-handoff` subcommand, no `handoff` table, and no Handoff tab. A
per-agent narrative block answering "where do things stand" is work state living
outside the cards; storing it inside `tickets.db` does not make it part of the
board, and it gives every session a second place to look.

**A card is the handoff.** Leave work mid-flight by putting its card on the
active board in `doing`, at the top of its column and with the owning agent as
`assignee`. The status scripts rank exactly that first, so the next session
picks it up without being told. What remains goes in the card's description or
in one short `add-issue-log` comment. There is no other channel and no other
log — if it is not on a card, it does not carry.

`schema_guard._drop_retired_handoff` drops the table from any DB that carries
one on launch, so a stale block cannot resurface.

### Format — scannable in ~10 seconds (comments, descriptions)

The board is a status surface a human skims, not a log. Every comment and
ticket description obeys these rules:

- **Bullets, not paragraphs.** One idea per bullet, ≤ ~15 words. Never a
  run-on block.
- **2–4 short headers.** Ticket: `Goal` / `Done so far` / `Needs next`.
- **Hard length cap.** Past ~10 lines or ~8 bullets it's too long — cut it, or
  move durable detail to the file that owns it (charter/playbook/README/config).
- **No state duplication.** The board is not an archive; write the current
  state, not a history of every step.

`epic_log` was a misnamed per-agent handoff-plus-log with nothing to do with the
Epic *concept*. It is gone, as is the `handoff` table that replaced it; ordinary
cards cover the whole job. Nothing reads or writes either any more.

## Directory Structure

The expected structure under the project root is:

<project-root>  
    src/tools/ticket_tools  
        cos_status.py  
        agent_status.py  
        create_tickets.py  
        ticket_write.py  
        README.md  
    data/<instance>/tickets  
        tickets.db   (tables: theme, epic, scope, task, task_meta,
                       issue_log, attachment, task_event)
                     (task carries stage + sort_order for the Kanban board)

## Future Extensions

This folder is designed to support future initialization scripts, agent provisioning workflows, and automated maintenance tasks. Additional tools may be added as long as they follow the same invariants: no personal data, stable project‑relative paths, and canonical DB discovery.
