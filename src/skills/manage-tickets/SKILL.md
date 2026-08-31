---
name: manage-tickets
description: Writes and updates the cards on the ticket board, sizes them, and leaves the board correct when a session ends. Use when writing a card, sizing one, finishing a session, or when the user asks what's next, where were we, or status.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3, and PySide6 for the viewer.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---

# manage-tickets

How any agent uses `tickets.db` as its cross-session memory. This skill owns the
*procedures*: how to write a ticket body, how to close a session, how to size a
card. The rules for reading and working the queue are `src/app.md` Phase 3; the
storage and CLI mechanism is `src/tools/ticket_tools/README.md`. Style contract
for all three: `src/templates/identity_template.md`.

## When to read the board

- **At every session start**, per `src/app.md` Phase 3.1.
- **Whenever the user asks "what's next," "where were we," "status" or
  "continue."** Re-read; never answer from conversation memory.

## When to update the board

Update it whenever the user expresses any of these, without waiting to be asked:

- **A new task** — "remind me to…", "add…", "we should…", "later we need to…".
- **A change to an existing task** — "mark this done", "block this", "move this
  up".
- **A new epic or project**, or an epic opening or closing.
- **A shift in order or focus.**

Route every update through `src/tools/ticket_tools/ticket_write.py`.

**Add casual mentions as cards on the spot.** Parse the mention as a task,
insert it under the appropriate epic, and confirm back only if it is ambiguous.

**Give every card you touch an `--estimate`** on the S/M/L/XL scale in §Effort
sizing. Size it in one pass against the anchors there. An XL card is one to
split, not one to start.

## Record types: Build vs Fix

Every ticket ("issue" and "ticket" are synonyms) is exactly one record type,
stored in `task.record_type`. Match a Description you author to its type.

**Build** — a thing to build, something new or changed:

```
Story:
As [owner] I want [what should change] so that [why it matters].

Acceptance Criteria:
1. Given [starting state], when [action], then [expected result].
```

Add a numbered line per criterion. A worked one: "Given the active agent is
chief_of_staff and a host is loading Bristol, when a session loads
tickets.db, then it treats its next priorities as its own active-board tasks
(stage='active') in precedence order."

**Fix** — a broken thing. No story, no acceptance criteria:

```
Expected:
Given [precondition], when [action], then [expected result].

Observed:
[what happened instead]
```

The viewer pre-fills these as mad-libs — constant words with short `[bracketed]`
blanks; replace the whole bracket, brackets included.

**Your own text always wins over the skeleton.** Switching Build⇄Fix swaps the
skeleton only while the field is still untouched boilerplate; once you type
anything of your own it is never overwritten. Emptying the field entirely brings
the skeleton back next time the record opens.

**Where everything that is not the skeleton goes** (the rule it serves:
`src/tools/ticket_tools/README.md` §Board conventions):

| What you wanted to write | Where it goes |
| --- | --- |
| Reasoning, findings, what you did, what's needed next | An `add-issue-log` comment |
| A decision the user must make before you proceed | An `add-issue-log` comment, plus `assignee` = `user` |
| What kind of thing stopped the card | `update-task-status --block-reason dependency\|decision\|capability\|transient` |
| "This came from that review / that note / that page" | A link (`link-add --uri`) |
| "This relates to ticket #153" | A link (`link-add --to-task 153`) |
| Durable technical detail (schema notes, a working pattern) | The file that owns it — a README or skill — then link to it |

Use comments freely: they are human prose rather than a template, they are what
the board renders under the Log, and the only rule on them is
`src/tools/ticket_tools/README.md` §Format.

## Session closure

Before wrapping up any session that changed state (skip only for pure Q&A),
reflect the true state into the board.

**1. Put every task you touched in the column that reflects reality.** `done`
when finished, `doing` for anything else you touched. Per `src/app.md` Phase 3.5
that move already happened when you first touched the card; this is the check.
**A finished task stays on the active board in `done`** — archiving is the
user's board-tidy call, not part of marking work done.

**2. Leave half-done work as the handoff.** Move the card to the top of its
column (`set-order --id N --position 1`), onto the active board
(`set-stage --id N --stage active`), set the proper `assignee`, and say what
remains in its description or one short `add-issue-log` comment.

**3. Continue a ticket; never finish-and-spawn.** When your work leaves
follow-up in another agent's or the user's court, keep the same card alive: move
it to `doing`, trim its title and description to the work that remains
(`update-task --id N --title … --description …`), add one short comment, and
reassign it to whoever acts next. Marking it `done` and opening a fresh card for
the remainder clutters the board with duplicate walls. Open a new card only for
genuinely new, separable work.

**4. File new to-dos onto the active board.** `add-task` puts them there, and
this includes cross-agent suggestions: `--assignee` = that agent or the user,
`--reporter` = you, still on the active board.

**5. Scope each card to one agent's context.** The user runs sessions per agent,
so a session loads that agent's charter and matches its own skills first. Write
the
card so its assignee can execute it with only its own documents loaded — that is
what makes `assignee` the routing key rather than a label.

**6. Record prerequisites as links, and set the position too.**
`link-add --task N --to-task M --type blocked-by` says N cannot start until M is
`done`. Queue position cannot express "this one may not start yet," and it is
lost the moment anyone reorders the column, so the two do different jobs and you
do both.

**7. Leave the queue in the order you would work it, and rate what you touched.**
Three separate acts, all cheap:

- **Order.** `set-order --id N --position K`, position 1 = next. Order by what
  should actually happen next, not by what you happened to open. A stale order
  is worse than none; the user overrides by dragging.
- **Size.** `update-task --id N --estimate S|M|L|XL`, per §Effort sizing.
- **Pressure.** `update-task-status --id N --status <its column> --pressure K`,
  0–100, your honest gestalt of urgency, impact and how alive the thing feels.
  Say so in the card's comment if the number is surprising.

**8. Make an early stop easy to say yes to.** A session that halts for one of
the reasons in `src/app.md` Phase 3.6 ends on an ask, and the ask is the first
thing in the message:

- **Lead with a plain imperative** — "Please quit Zotero" — and put the
  reasoning after it, short.
- **Name the ungranted tool or connector that would unlock the card, and use
  whatever the runtime offers to make granting it one step.** An offer, never a
  demand, and never a reason to stall work you can already do.
- **Set the card's block reason to what actually stopped it**, and put the tool,
  the call or the choice in a comment beside it. A `capability` or a `decision`
  is what puts the card under NEEDS YOU the next time anyone reads the board.

## Effort sizing — what S/M/L/XL measure

A card's `estimate` answers one question: **how much of a full usage budget
would this card consume?** The budget is the user's plan allowance over its
rolling window — one string in config (`read_config.py sizing.usage_window`), so
nothing here assumes a vendor or a number. It is a hypothetical full budget, not
the one you are part-way through.

- **S** — under a tenth of a budget.
- **M** — a tenth to about half.
- **L** — half a budget or more, but finishable within one.
- **XL** — more than one budget. Not a size: a card to split, not to start.

**Three things this is not.**

- **Not the conversation you are in.** A conversation is one chat; a budget spans
  several. Running low on conversation room is a reason to stop, never a reason
  to re-size a card.
- **Not a countdown.** The estimate is the size of the whole card and stays put
  as work proceeds. It changes only when the card's *scope* changes.
- **Not a measurement.** You cannot see the budget meter and must not pretend to.

**Anchors — size by nearest match, not by calculation.**

- **S** — a rule reworded across two or three files; one CLI flag added; a card
  triaged, commented and re-linked; a config key renamed.
- **M** — one self-contained tool written and wired in; a doc rewritten with its
  call sites updated; one UI field replaced end to end.
- **L** — a column renamed across the schema, both writers, the UI and every
  document that names it; a subsystem's behaviour changed with its migration.
- **XL** — a build that needs a design decision before it can start; anything
  whose shape you would have to investigate before you could size it.

Size in one pass against that list and stop. A card sized wrong is cheap to
correct; a card sized slowly is not.

## When to open the viewer

Open Bristol Tickets when the user wants to inspect the board visually,
reorganize cards by hand, or browse epics and scopes:

```
python3 src/tools/bristol/app.py
```

## When to create or rebuild a tickets database

Only when creating a new instance, migrating schema, or rebuilding from markdown
archives — never during normal operation, and never to give an existing
instance's agent its own store (`src/tools/ticket_tools/README.md` §Invariants).
