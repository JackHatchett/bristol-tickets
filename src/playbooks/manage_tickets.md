## Purpose
Define how any agent uses the tickets DB as its cross‑session memory system:
- when to read it
- when to update it
- how to treat it as the canonical queue of next actions
- how to add small items during conversation
- how to keep the DB consistent with user intent

This playbook is conceptual; all mechanism lives in ticket_tools and bristol.

---

## When to read the board
- At **every session start**, run `ticket_tools/cos_status.py` to load:
  - milestone
  - active epics
  - ordered queue
  - next action

- When the user asks:
  - “what’s next”
  - “where were we”
  - “status”
  - “continue”

---

## When to update the board
Update the DB whenever the user expresses:
- a new task (“remind me to…”, “add…”, “we should…”, “later we need to…”)
- a change to an existing task (“mark this done”, “block this”, “move this up”)
- a new epic or project
- a shift in order or focus

Every card you touch carries an `estimate` — how much of a full usage budget it
would take, on the S/M/L/XL scale in §Effort sizing below. Size it in one pass
against the anchors there. An XL card is one to split, not one to start.

All updates go through `src/tools/ticket_tools/ticket_write.py`.

---

## How to treat the board
- The tickets DB is the **single source of truth** for:
  - next actions
  - active work
  - backlog
  - strategic direction

- The DB replaces:
  - next_session.md  
  - roadmap.md  
  - ad‑hoc notes  
  - memory drift  

- The DB is **always authoritative** over conversation memory.

---

## How to add items during conversation
When the user casually mentions something to do later:
- parse it as a task
- insert into the DB under the appropriate epic
- confirm back to the user only if ambiguous

Examples:
- “We should fix X later.” → add task
- “Remind me to…” → add task
- “Let’s track this.” → add task

---

## Record types: Build vs Fix

Every ticket (the umbrella term; "issue" and "ticket" are synonyms for it) is
exactly one of two **record types**, stored in `task.record_type`:

- **Build** — a thing to *build*. Something new or changed. Its Description is
  a user story plus testable acceptance criteria.
- **Fix** — a *broken* thing. Its Description states the expected behaviour and
  the observed divergence. No story, no acceptance criteria.

These deliberately avoid Atlassian's "Story / Bug" vocabulary — the system's
own path. Default is **Build**; set `--record-type fix` (CLI) or pick *Fix* in
the viewer when the ticket is fixing something that misbehaves.

These are governing rules for how *you* (any agent) and the user write ticket
Descriptions; the DB only stores the type flag and the free-text body. When you
author a ticket, match its Description to its type. The viewer pre-fills these
same skeletons as mad-libs — constant words with short `[bracketed]` blanks;
replace the whole bracket (including the brackets) with your own words.

**Build Description format:**

```
Story:
As [owner] I want [what should change] so that [why it matters].

Acceptance Criteria:
1. Given [starting state], when [action], then [expected result].
```

Add a numbered line per acceptance criterion. A worked one, from the loading
protocol: "Given the active agent is chief_of_staff and Cowork is loading
Bristol Tickets, when a session loads tickets.db, then it treats its next priorities
as its own active-board tasks (stage='active') in precedence order."

**Fix Description format:**

```
Expected:
Given [precondition], when [action], then [expected result].

Observed:
[what happened instead]
```

**Template precedence (viewer):** on create, the Description is pre-filled with
the selected type's skeleton. Your own text always wins — switching Build⇄Fix
only swaps the skeleton while the field is still untouched boilerplate; once you
type anything of your own it is never overwritten. Emptying the field entirely
brings the skeleton back next time the record opens (blank ⇒ template).

## Description discipline — the template, and only the template

**This section governs agents. It does not govern the user.**

When you author or edit a ticket body, its Description contains exactly the
skeleton above for its record type: Story + Acceptance Criteria for a Build,
Expected + Observed for a Fix. Nothing precedes it, nothing follows it, and no
other header appears in it. Specifically banned, because each of these has
actually been written into a Description:

- `Source: <file> §4.1` or any other provenance header.
- "Addressed to chief_of_staff or librarian."
- "USER DECISION REQUIRED BEFORE EXECUTING."
- An options-and-recommendations essay, or a numbered implementation plan.
- Any note to whoever reads the ticket next.

You may rewrite a Description and its acceptance criteria whenever the work
changes — but only into that shape.

**Where the banned material goes instead:**

| What you wanted to write | Where it goes |
| --- | --- |
| Reasoning, findings, what you did, what's needed next | An `add-issue-log` comment |
| A decision the user must make before you proceed | An `add-issue-log` comment, plus `assignee` = `user` |
| "This came from that review / that note / that page" | A **link** (`link-add --uri`) |
| "This relates to ticket #153" | A **link** (`link-add --to-task 153`) |
| Durable technical detail (schema notes, a working pattern) | The file that owns it — a README or playbook — then link to it |

Comments are the elaboration channel and you should use them freely: they are
human prose, not a template, and they are what the board renders under the Log.
The only rule on a comment is §Format — scannable in about ten seconds.

## Links — a ticket's relations

Two kinds, both via `ticket_write.py link-add --task N`:

- `--to-task M` links two tickets. It is stored once, so it shows on **both**
  tickets immediately. Never run the mirror call, and note that `link-remove`
  clears it from both ends. `--type` says what the link means: `related` (the
  default), or `blocks` / `blocked-by` for a dependency — `--task N --to-task M
  --type blocks` means N must be `done` before M may start. Re-running
  `link-add` on an existing pair retypes it.
- `--uri "…"` links to an address: a web URL, a `zotero://` citation, an
  `obsidian://` note, or a file path. `--label` gives it a caption. Bristol
  hands the address to the OS, so an `obsidian://` URI opens Obsidian and a
  bare `.md` path opens in whatever owns that file type.

Read the links on a ticket before executing it, exactly as you read its attached
images. Since provenance no longer lives in the Description, a ticket's text on
its own is deliberately incomplete — the status scripts print a `LINKS` section
for precisely this reason.

**When you leave work that must happen in an order, link the blocker.** Queue
position says what comes next; it cannot say "this one may not start yet," and
it is lost as soon as anyone reorders the column. Record the prerequisite with
`--type blocked-by` and set the position too — they do different jobs. The
status scripts then print `[BLOCKED by #N]` on the card for as long as the
blocking ticket is unfinished, and an agent that reaches a blocked card stops
there, names the blocker, and hands back to the user: it does not start it, does
not do "the unblocked part," and does not skip to the card below. Only the user
clears a blocker, drops the link, or says to go ahead.

**Keep tickets small.** was authored deliberately oversized (a record-
type redesign, a viewer feature, a handoff redesign, and an explainer, all in
one card) as a worked example of what *not* to do. When a ticket sprawls across
several independent outcomes, split it into one Build or Fix per outcome, each
with its own crisp acceptance criteria, rather than carrying a mega-ticket.

## Session closure

Before wrapping up any working session that changed state (skip only for pure
Q&A), reflect the true state into the shared board. It, not chat, is the record,
and it is how the next session — a new day, possibly a different model or agent
— knows where things stand.

**1. Put every task you touched in the column that reflects reality.**
`ticket_write.py update-task-status`: `done` when finished, `doing` for anything
else you touched. Per `src/app.md` Phase 3, that move already happened when you
first touched the card; this is the check, not the moment. **A finished task
stays on the active board in the `done` column** — do not move it to `archive`.
Archiving is the user's board-tidy call, not part of marking work done.

**2. Leave half-done work as the handoff.** There is no handoff note and no
handoff table (`src/tools/ticket_tools/README.md` §There is no handoff). Move
the card to the top of its column (`set-order --id N --position 1`), put it on
the active board (`set-stage --stage active`), set the proper `assignee`, and
say what remains in its description or in one short `add-issue-log` comment.

**3. Continue a ticket; do not finish-and-spawn.** When your work leaves
follow-up in another agent's or the user's court, do not mark the card `done`
and open a fresh one for the remainder — that clutters the board with duplicate
walls. Keep the same ticket alive: move it to `doing`, trim its title and
description to the work that remains, add one short comment (what you did, what
is needed next), and reassign it to whoever acts next. Open a new card only for
genuinely new, separable work.

**4. File new to-dos onto the active board.** `add-task --stage active` — the
subcommand still defaults to `--stage backlog`, so pass it explicitly. This
applies to every to-do you raise, cross-agent suggestions included: set
`--assignee` to that agent or the user and `--reporter` to yourself, and still
place it on the active board. `assignee` is the routing key — the user runs
sessions per agent, so write the card so its assignee can execute it with only
its own charter and playbooks loaded. Stay in your zone: raise to-dos only for
yourself or the user within your own area of responsibility.

**5. Record prerequisites as links, not positions.** `link-add --task N
--to-task M --type blocked-by` says N cannot start until M is `done`. Order the
queue as well — the two do different jobs.

**6. Leave the queue in the order you would work it, and rate what you
touched.** Three separate acts, all cheap:

- **Order.** `set-order --id N --position K`, position 1 = next. Order by what
  should actually happen next, not by what you happened to open. The user
  overrides by dragging; a stale order is worse than none.
- **Size.** Give every card you touched an `--estimate` — S, M, L or XL, on the
  scale in §Effort sizing below. One pass against the anchors, then move on.
- **Pressure.** Give every card you touched a `--pressure` 0–100: your honest
  gestalt of urgency, impact and how alive the thing feels. It changes no
  sequence and blocks nothing. Say so in the card's comment if the number is
  surprising.

Every comment and description stays scannable in about ten seconds — see
`src/tools/ticket_tools/README.md` §Format.

## Effort sizing — what S/M/L/XL measure

A card's `estimate` answers one question: **how much of a full usage budget
would this card consume?** The budget is the user's plan allowance over its
rolling window; what that is for this installation is one string in config
(`read_config.py sizing.usage_window`), so nothing here assumes a vendor or a
number. It is a hypothetical full budget, not the one you are part-way through.

- **S** — under a tenth of a budget.
- **M** — a tenth to about half.
- **L** — half a budget or more, but finishable within one.
- **XL** — more than one budget. Not a size: a card to split, not to start.

**Three things this is not.**

- **Not the conversation you are in.** A conversation is one chat; a budget
  spans several. Running low on conversation room is a reason to stop, never a
  reason to re-size a card.
- **Not a countdown.** An estimate is the size of the whole card and stays put
  as the work proceeds. You never decrement it because you have done some of it.
  It changes only when the card's *scope* changes.
- **Not a measurement.** You cannot see the budget meter and must not pretend
  to. Size by comparison with the anchors below.

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
Open the GUI when the user wants:
- to visually inspect the board
- to reorganize tasks manually
- to browse epics or scopes

Command:

python3 tools/bristol/app.py

---

## When to create or rebuild a tickets database
Use ticket_tools only when:
- creating a new agent
- migrating schema
- rebuilding from markdown archives

Never during normal operation.

---

## Consistency rules
- Every session ends with the cards telling the truth (§Session closure).
- Every new idea becomes a task.
- Every shift in focus updates epic status.
- The queue must always reflect the user’s real priorities.
- The DB must never fall behind the conversation.

---

## Human audit notes
- Ensure DB path in user.yaml is correct.
- Ensure no personal paths exist in mechanism tools.
- Ensure cos_status.py output matches DB state.
