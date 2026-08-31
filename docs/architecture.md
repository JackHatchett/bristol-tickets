# Architecture

Three things, meeting at one database.

## The database

`data/<instance>/tickets/tickets.db` is a SQLite file, one per installation. It
holds every card, every epic, every comment, every link, every image reference,
and a change log. It is the only place work state lives: what is done, what is
next, what is in progress, who owes whom, in what order.

Tables: `theme`, `epic`, `scope`, `task`, `task_meta`, `issue_log`,
`attachment`, `task_event`, `task_link`. A card is a row in `task`, carrying
both a `stage` (which tab) and a `status` (which column), plus a `sort_order`
that is its position in that list.

`task_event` is written by database triggers rather than by any program, so a
drag in the app, a Clear Done sweep, a dialog edit and a command-line write are
all recorded the same way. It is what makes cycle time and work-item age
computable.

One database per installation, never one per agent. An agent is scoped by
tagging — a card's assignee, or its epic's owner — not by storage.

## Bristol Tickets, the app

`src/tools/bristol/` is a PySide6 desktop application: a Kanban board over that
database, described in [board.md](board.md).

It is mechanism only. It contains no agent logic, no personal paths, and imports
nothing from the rest of `src/tools/`. Its whole job is to locate a tickets
database and show it. That isolation is why it opens, runs and changes without
anyone needing to understand the system around it.

Inside it: `app.py` locates the database and applies the schema; `schema.sql` is
an idempotent snapshot applied on every launch, so an older database
self-completes rather than needing a migration step; `ui/` holds the widgets,
split into small modules; `reports/` computes and writes the Clear Done report,
with the computation, the formatting and the path resolution in separate files.

## The agent files

`src/app.md` is what a session reads first. It describes the boot
sequence: resolve configuration, take on one agent identity, read the board,
work the queue. It is the only document resident in every session, so it holds
the rules an agent must have without opening another file.

Around it:

- `src/agent_identities/` — one charter per agent: what that agent is, what it
  owns, what it may not do.
- `src/templates/` — the shapes a new charter or README has to take.
- `src/tools/` — standalone programs. The ticket writer and status readers, the
  configuration resolver, file management, document conversion, scrapers,
  renderers, a test harness.
- `src/skills/` — a procedure as a folder holding a `SKILL.md`, in the open
  Agent Skills format, loaded when its description matches the task. This is
  where a procedure goes; `src/templates/identity_template.md` §What an agent
  is made of says why.

Inside `src/tools/`, a folder named for an agent says who maintains what is in
it, not who may run it, and a skill says the same in its `bristol.maintainer`.
Any agent may load any skill or tool. The skill index is one line per skill with
the situation that calls for it; an agent reads the index and loads only what it
will run. So a session pays
context for a capability at the moment the task needs it, and a capability is
written once instead of once per agent.

Borrowing a capability carries none of its maintainer's authority: the loading
agent's own charter gates what it executes, and handing work to another agent is
still a card on the board rather than a file left where it will be found.

## How the three meet

Bristol Tickets writes to the database directly. An agent writes to it through
`src/tools/ticket_tools/ticket_write.py`, which self-heals an older schema the
same way the app does. Whichever surface acts, the other sees the change on its
next read.

Neither surface is primary. You can run Bristol Tickets alone as a Kanban board
and never open a session. You can work a session without opening
Bristol Tickets. The database is what they agree on.

## Design constraints

**The tools stay small and separately runnable.** `src/tools/` is a set of
independent programs, each readable in a single pass. They are not consolidated
into one application, and a launcher that presents several composes them rather
than fusing them.

**Bristol Tickets is self-contained.** It depends on nothing else in the tree.

**Legibility beats cleverness.** The repository is written to be read by people
learning to build alongside AI. The data and configuration contract is explicit
and inspectable, and a clever construction that costs a reader is the wrong
choice.

**The board is the only channel.** Agents hand work to each other by assigning a
card, never by leaving a file, a note, or a message relayed through you. Nothing
derives a next action from a folder listing, a status field, or the most
recently modified file. A second place to look is a second place to disagree.
