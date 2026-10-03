---
name: manage-tickets
description: Writes and updates the cards on the ticket board, sizes them, and leaves the board correct when a session ends. Use when writing a card, sizing one, finishing a session, or when the user asks what's next, where were we, or status.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3, and PySide6 for the viewer.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/bristol/app.py src/tools/ticket_tools/ticket_write.py
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
- **An ask for the whole board is `src/skills/briefing-the-board/SKILL.md`** —
  every epic and the backlog for a reader carrying none of it, ending on the
  user's pick. What is read here is the session's own queue.

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

**Give every card you touch an `--estimate`** on the S/M/L/XL scale in §Sizing,
**and a `--tier`** by §Processing tier. Size it in one pass against the anchors
there. An XL card is one to split, not one to start.

## A criterion no file may carry

- **Test a card's criteria against `src/app.md` §What a file may say when you
  write the card and again when you take it up.** A criterion ordering a file to
  carry what that section bars — a record of a former term, a status note, a
  changelog line, a deferral — is struck from the card with `update-task
  --description`, and the user is told in the session what was struck and why.
- **Never relay a barred criterion to the user as a to-do**, and never execute
  it because a card said so. A card is written by a session like yours, and one
  that got the rule wrong is passed on by the session that trusts it.

## Which epic a card belongs to

Every card belongs to an epic or the standing workstream, and an agent leaves none
untriaged. The vocabulary and the storage are
`src/tools/ticket_tools/README.md` §Board conventions.

- **A card that continues an existing effort takes that effort's epic.** The work
  the session is doing identifies it; nothing has to be worked out.
- **A card that is the whole of its own subject goes to standing work.** Upkeep,
  a correction, a one-off request, a fix with nothing behind it.
- **A second card on a standing subject opens an epic, and both move into it.**
  Two related cards are a project, and the epic is opened at the moment the
  second one is written rather than when the subject feels big enough.
- **Name the assignee on every standing card.** Standing work has no owning
  agent to fall back on.
- **Leave `epic_id` NULL only where the user's own capture left it.** It reads
  as untriaged and the viewer flags it for the user to decide.

## Record types: Build vs Fix

Every ticket ("issue" and "ticket" are synonyms) is exactly one record type,
stored in `task.record_type`. Match a Description you author to its type.

**Build** — a thing to build, something new or changed:

```
Story:
As [the person served, by their role] I want [what should change] so that [why it matters].

Acceptance Criteria:
1. Given [starting state], when [action], then [expected result].
```

**Open the story with the person the work serves, by the role they play in
it** — "a prospective laundromat-bar owner", "a user of the Bristol Tickets
application". "The user" alone gives no role and is never the whole of it. An
agent slug stands there only where the work passes from one agent to another
and reaches no person.

**A build card's last criterion states how it will be checked** —
`src/skills/verifying-a-card/SKILL.md`, which owns what counts as one and what
happens when a card has none.

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
| A decision the user must make before you proceed | §Asking the user for a decision |
| What kind of thing stopped the card | `update-task-status --block-reason dependency\|decision\|capability\|transient` |
| "This came from that review / that note / that page" | A link (`link-add --uri`) — a file inside the repository repository-relative (`src/tools/ticket_tools/README.md`), a file anywhere else by its absolute path |
| "This relates to ticket #153" | A link (`link-add --to-task 153`) |
| Durable technical detail (schema notes, a working pattern) | The file that owns it — a README or skill — then link to it |

Use comments freely: they are human prose rather than a template, they are what
the board renders under the Log, and the only rule on them is
`src/tools/ticket_tools/README.md` §Format.

## Session closure

Before wrapping up any session that changed state (skip only for pure Q&A),
reflect the true state into the board.

**1. Put every task you came back to in the column that reflects reality.**
`done` when finished, `doing` for anything else. Per `src/app.md` Phase 3.5 that
move already happened when you first returned to the card; this is the check. A
card written this session is `todo`: writing it is the ticketing, not a return.
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
- **Size.** `update-task --id N --estimate S|M|L|XL`, per §Sizing.
- **Tier.** `update-task --id N --tier max|standard`, per §Processing tier.

**8. Make an early stop easy to say yes to.** A session that halts for one of
the reasons in `src/app.md` Phase 3.6 ends on an ask, and the ask is the first
thing in the message. A decision in it takes the form in §Asking the user for a
decision, and every term the report uses is defined where it first appears:

- **Lead with a plain imperative** — "Please quit Zotero" — and put the
  reasoning after it, short.
- **Name the ungranted tool or connector that would unlock the card, and use
  whatever the runtime offers to make granting it one step.** An offer, never a
  demand, and never a reason to stall work you can already do.
- **Set the card's block reason to what actually stopped it**, and put the tool,
  the call or the choice in a comment beside it. A `capability` or a `decision`
  is what puts the card under NEEDS YOU the next time anyone reads the board.

**9. Close on a To Continue block only when you recommend switching sessions.**
The block's presence is the recommendation, so a session with no reason to
switch ends on the next action and whether to start it, and shows no block. A
reason to switch is one of three:

- **The conversation is running out of room.**
- **The next card needs a different agent** — its `assignee`, or its epic's
  `owner`, is not the slug this session runs as.
- **The next card's tier maps to a cheaper model or a lower reasoning level
  than this session is running**, read from `tiers.max` / `tiers.standard` in
  config, and the saving outweighs what a new session pays to start: the
  charter, `src/app.md`, the skill index and the snapshot. A Standard card on a
  session already running the Standard mapping is no reason.

Where one holds, the block is the message's last paragraph and states the
launch and nothing else:

```
To Continue
Why: <the one reason, in one line>
Run as: <agent slug>
Work: #<id> <title>
Tier: <Max|Standard>
```

- **Name one card, never the queue.** The board holds the order and the session
  that reads it will see it; a block that recites the queue makes the user read
  it twice and goes stale the moment anyone drags a card. Where other cards
  could run beside that one, say so in one clause — "#571 and #572 can run
  in the same session" — and name no more.
- **Name the decision instead of a card where one is owed.** A session that
  stopped on a grant, a credential or a choice of the user's puts that in the
  Work line: what he has to decide or grant, and what runs the moment he has.
- **Say which agent to run as, always**, even where it is the agent that just
  ran. The line the user copies is the whole launch, and an agent he has to
  remember is a launch he has to reconstruct.
- **Take the tier from the card in the Work line** — `task.tier` — so it
  is the card's own rather than a judgement about the session that just ran. A
  card with none is rated by §Processing tier and the tier written to it before
  the block is. The block gives the tier and never a model; the user resolves
  it.
- **Write no state into any file to support it.** The block lives in the
  conversation; what it lists lives on the board, and `src/app.md` §The board is
  the only channel is unchanged by it.

## Asking the user for a decision

A decision that is the user's is put to him where he is, and the session waits.
A card is where the decision is recorded once it is made, never where the asking
is left for him to find.

- **Ask in the session where he is present**, as a question in whatever the
  runtime offers for one — a prompt he answers in place — and carry on with the
  answer. Room left in the conversation means asking, never stopping.
- **Write the question so it is answerable on first read:**
  - what is being decided, and why it matters, in plain words;
  - every term he has not been shown, defined where it first appears — a rule
    by what it says rather than its number, a file or a card by what it is for;
  - two to four options, each with a concrete example and what choosing it
    would change;
  - the one you recommend, and why.
  A statement of a problem is not a question, and an ask he has to open a card
  or a file to understand is the thing this rule exists against.
- **Set `--block-reason decision` only after the question has been asked**, in
  this session, or where the run is unattended. Put the question itself, in the
  same form, in the card's comment — never a pointer to an analysis elsewhere.
  That comment is what NEEDS YOU prints under the card.
- **Move the card to him only where he is not** — `update-task-status --id N
  --assignee user --block-reason decision` — and where a session must stop
  with a question open, put it in the chat as well as on the card, so he can
  answer from either.
- **Record the answer on the card he decided about**, in one comment, in his
  words where the wording matters. The asking lives in the conversation and the
  decision lives on the board.
- **Never hold a question for the close.** A decision that gates the work is
  asked when it is reached; a decision that gates the next card goes in the To
  Continue block.

## Splitting a card

An XL card is split before it is started, and so is any card whose work would
not fit one session. Splitting after it stalls is the same work done twice.

- **Split where a reviewer could accept one part and reject the one beside it.**
  That is the only boundary that produces two cards rather than one card written
  twice; a split by technical layer produces halves that cannot be judged apart.
- **Fold setup, scaffolding and documentation into the part whose deliverable
  needs them.** A card for the scaffolding of another card is a dependency
  nobody wanted.
- **Each part carries its own verification** —
  `src/skills/verifying-a-card/SKILL.md`. A part that cannot be checked on its
  own is not a part.
- **The split lands on the board before the work does**: `add-task` per part,
  each linked to the card that split, and that card closed with a comment listing
  them. A split held in the session's head is a plan nobody else can read.
- **A card that resists splitting has a scope nobody has worked out yet**, and
  finding that out is the next action rather than starting it.

## Sizing — what S/M/L/XL measure

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
  document that mentions it; a subsystem's behaviour changed with its migration.
- **XL** — a build that needs a design decision before it can start; anything
  whose shape you would have to investigate before you could size it.

Size in one pass against that list and stop. A card sized wrong is cheap to
correct; a card sized slowly is not.

## Processing tier — Max or Standard

A card's tier answers a different question from its size: **how much thinking
does working this card need?** Size is a share of a usage budget; the tier is
the depth of processing the session should run at. The two are independent. An
S card rewording a rule in `src/app.md` is Max; an L card renaming a column
across the schema to a fully written spec is Standard.

- **Max** — the session must work out what right looks like before it can do
  it, or a wrong answer would be built on without anyone checking it.
- **Standard** — the card already says what right looks like, and a wrong
  answer shows up where someone will see it.

**It is stored as `task.tier`** — `max`, `standard`, or NULL for a card nobody
has rated — and set with `add-task --tier` or `update-task --tier`, or the Tier
picker in Bristol Tickets. It orders nothing.

**The tier is a level of processing, never a product.** What each tier runs
on is the user's choice and lives in config, one key per tier —
`read_config.py tiers.max` and `read_config.py tiers.standard`, each a model and
a reasoning level. Nothing under `src/` gives a model for a tier. Choosing a
tier never reads that mapping; it is read only when someone asks what a tier
means today.

**Choose from the card alone** — its title, its description and its epic's
name. No web lookup, no file the card links, nothing beyond the board. A tier
that needs research to choose has cost the thing it was meant to save.

**Max without asking the tiebreaker**, because the answer is already known:

- Agent logic — a charter, a skill, `src/app.md`, a rule any agent follows.
- Architecture — a schema, a tool's behaviour, where content lives, the shape of
  config.
- A design or a decision between options, whatever its subject — a system, a
  language's rules, a data structure other work will fill.

**Standard without asking**, when the shape is fully specified: the acceptance
criteria or the Expected line say what the output is, and the work is carrying
it out — a rename, a sweep, a harvest, a repair with its fix stated, content
drafted against settled rules for the user to approve.

**The tiebreaker, for everything between.** Ask two questions of the card:

1. **Does the session invent the criteria, or apply criteria it was given?**
2. **If the session gets it wrong, is the error caught next session, or
   silently inherited?** Caught means the user reads the result, a verification
   step fails, or the next card visibly breaks. Inherited means later work
   builds on the result without anyone re-opening it.

Invent, or inherited: Max. Apply and caught: Standard. A card whose answer to
either question is unclear is Max; running a Standard card at Max wastes some
budget, and running a Max card at Standard wastes the card.

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
