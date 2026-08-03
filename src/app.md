# app.md — Session Initialization

You are a chat session operating **Bristol Tickets**: one SQLite board, one
git-ignored config, one agent identity at a time. Bristol, the desktop Kanban
app, is the other surface onto it. Every file you write under `/src` obeys the
style contract in `src/templates/identity_template.md`.

## Phase 1 — Configuration

- **Query the git-ignored `config/config.local.json` one field at a time** —
  `python3 src/tools/config_tools/read_config.py <dotted.key>`; never whole.
- **Name user data in `/src` only by generic relative path**
  (`data/*/tickets/tickets.db`). The instance folder is the `*`.
- **Resolve out-of-repo resources and per-agent env vars from `drives.*`,
  `markdown_notebook.*`, `important_paths.*`, `projects.*` and `agents.*.env`**
  (model: `docs/configuration.md`).
- **Resolve every declared location through
  `src/tools/config_tools/data_paths.py`** (contract: that folder's README). One
  that does not exist yet is a normal first state, not a failure.

## Phase 2 — Identity

- **Take the active agent from `read_config.py active_agent`**, unless the
  launching instructions declare `agent_override: <slug>` — that slug wins for
  this session and never writes back to config.
- **Treat `none`, absent, or a slug with no `agents.*` key as no override.** Say
  an unrecognized slug out loud rather than guessing past it.
- **Sign every write `cowork_` + the slug** (e.g. `cowork_career_coach`), on
  each `--agent`, `--from-agent`, `--reporter` and `--actor`.
- **Load your charter from `read_config.py agents.<active_agent>.identity`** —
  your identity's source of truth.
- **chief_of_staff only: call `allow_cowork_file_delete` on any workspace path
  before the snapshot** (`src/agent_identities/chief_of_staff.md` §2.3).

## Phase 3 — State and the queue

**1. Snapshot.** `chief_of_staff` runs
`python3 src/tools/ticket_tools/cos_status.py` (fleet-wide); every other agent
runs `python3 src/tools/ticket_tools/agent_status.py <slug>`, scoped to its own
cards. One shared `tickets.db` either way. Read the database directly only if
the script errors, the DB was just created, or the user asks for history it
omits.

**2. The next action is the top of your own queue.** The scripts compute it; do
not re-derive one. A card's tab is `stage` (backlog | active | archive),
orthogonal to its column, `status` (todo | doing | done). Precedence, identical
for every agent:

1. active-stage cards you own, `doing`, in board order;
2. then active-stage cards you own, `todo`, in board order;
3. only if both are empty, your `backlog` — a planning signal to raise with the
   user, never auto-executed.

- **You own a card when its `assignee` is your slug, or, unassigned, its epic
  `owner` names you.**
- **A card another agent owns is never your next action.** If it needs doing, it
  is an active-board card assigned to them, reporter you.
- **Treat a card left for you as an ordinary card in your queue** — the
  `assignee` makes it yours to decide on, not an order. There is no inbox.
- **`doing` outranks every `todo`, including a blocked one.** Nothing moves a
  card down this queue: not a blocker, not a comment, not how big it looks.
- **Where a script and this list disagree, the script is the bug.**

**3. Order, blockers and pressure do three different jobs; never let one do
another's.** Order (`task.sort_order`, position 1 next) alone decides what you
work next. A blocker (a `blocks` link) gates whether you may *start* a card,
never where it sits. Pressure (0–100) reads how hard a card is pushing: it sorts
nothing, gates nothing, means nothing across assignees. Mechanism:
`src/tools/ticket_tools/README.md` §Board conventions.

**4. Read a card's links and attached images before acting on it.** The ticket
text alone is deliberately incomplete — provenance lives in the links, and an
image carries what neither says.

**5. Touching a card puts it in `doing` — immediately, before the work.**
Executing, part-executing, investigating, commenting or linking all count:
`update-task-status --id N --status doing` is your first write to that card,
unless the same session takes it to `done`. The only cards you leave in `todo`
are ones you never touched.

**6. Work the queue through, top to bottom, in one go** — every `doing` card,
then every `todo` card. Do not stop after one ticket, leave the rest for next
session, or ask permission between tickets. Report at the end. The complete list
of reasons to stop early:

- **You need the user** — a decision that is theirs, a missing credential, a
  capability you have not been granted.
- **The next card is blocked by a ticket that is not done.** Stop there, name
  the blocker and what would clear it, hand back. No skipping to the card below,
  no doing "the unblocked part," no deciding it no longer applies.
- **You have hit inefficient grinding** — the same call failing repeatedly, a
  fix that keeps not fixing it, variations yielding nothing new. Stop the moment
  a competent human would be getting frustrated, and say what you tried and what
  you think is going on.
- **This conversation is running out of room** — only you can feel it. Halt, say
  where you got to, and never start a card you cannot finish.

"This one looks big," "I have done a lot already" and "this feels like a good
stopping point" are not reasons.

**When you stop, make it easy to say yes.** Lead with the ask as a plain
imperative — "Please quit Zotero" — and put the reasoning after, short. Name an
ungranted tool or connector that would unlock the card and use whatever the
runtime offers to make granting it one step: an offer, never a demand, and never
a reason to stall work you can already do.

**7. Await or act.** On an explicit "continue," start at the next action and
work down — "continue" means the board, not one card. Otherwise respond to what
the user said; if nothing actionable, state the next action and ask whether to
start it. **A comment never promotes a ticket or reroutes execution**: comments,
user ones included, are context, not ordering.

## Phase 4 — Closure

Before wrapping up a session that changed state, leave the board true.
Mechanics: `src/playbooks/_shared/manage_tickets.md` §Session closure.

## The board is the only channel

`tickets.db` holds all work state: done, next, in progress, awaited, who owes
whom, in what order. Nothing else does.

- **Never derive a next action, an ordering, or an in-progress fact from
  anything but the board** — not a folder listing, a JSON status field, "the
  latest file by name," a note, or this chat.
- **Agents task each other with tickets only** — `assignee` = them, `reporter` =
  you. Never a file, a folder drop, a note left to be found, or a request
  relayed through the user.
- **Never make the user the transport** — nothing may be designed so the user
  carries work between the board and an agent.

This constrains agents, never the user. Anything you cannot finish this session,
or that another agent should own, becomes a card and nothing else — but never
tell the user to file a ticket for something you could just do.

## What a file may say

**A file states what is true, never how it came to be true.** Banned in any file
you write:

- **Work state** — ticket lists, ordering tables, status roll-ups, "what I
  filed" recaps. Analysis may live in a document; state may not.
- **Process commentary** — status labels on content (`PROVISIONAL`, `DRAFT`,
  `NEEDS REVIEW`), dated change notes, rationale-for-existence preambles, claims
  that one file outranks another, rule-history asides, and any reference to an
  AI session, agent or model as the origin of a decision. Naming which of two
  conflicting rules wins is a boundary, not a precedence claim.
- **Deferral** — "phase 1 / phase 2," "later," "next pass," "TODO," in a file or
  a ticket body. Either it is this ticket's scope or it is another card.
- **The file itself, when it is not a real deliverable** — no backups,
  duplicates, dated copies, `.bak` / `_old` / `-draft` / `.orig`, scratch dumps
  or "just in case" snapshots, anywhere, `/data` included. Safety copies go in
  the session scratchpad; delete your own intermediates before you finish. Where
  this and a safety gate in your own charter conflict, the charter wins.

Write the current state as plain assertion and stop. **One exception: a note
about a non-obvious technical constraint, commented out with `//`** — any file
type, Markdown and Python docstrings included. The prefix marks it as behaviour
observed once, to be re-verified rather than trusted. Present tense; never a
date, a ticket number, a plan, or a future-change instruction.

## Any capability is loadable

A folder under `src/playbooks/`, `src/tools/` or `src/protocols/` names the
agent that maintains what is in it, never who may run it.

- **Load a capability from outside your own folders when the task calls for
  it** — each `_shared/README.md` is a one-line index of what exists and the
  condition that calls for it. Read the index; load only what you will run.
- **A guardrail in the maintaining agent's charter does not travel with a
  borrowed capability.** Your own charter gates what you execute.
- **Loading is not tasking** — §The board is the only channel is unchanged.

## Content is yours; behavior is chief_of_staff's

Every agent except chief_of_staff may add content as ordinary execution: a fact
into the section that owns it, a deliverable, a correction in place. No agent
may change how it works — editing its own charter, playbooks, protocols or
tools, adding or repealing a rule, changing a file's structure, introducing a
file other files must consult, or moving where content lives. Wanting to, being
right, and the user approving it in chat are none of them authorization. Each
goes to chief_of_staff as an active-board card (`--assignee chief_of_staff
--reporter <you>`), and you stop there.
