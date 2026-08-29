---
name: session-review
description: Propose one skill change as a card, at session close. Use when a session that changed something is closing and its board is already true.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3 to read the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# session-review

Read what a session actually did and propose at most one skill change as a card.
The pass writes no skill file. The skill format and the folder shape are
`src/playbooks/skill_conversion.md`; the loader is `src/tools/skill_tools/`.

## Preconditions

- **The session changed something.** A session that only read has no corpus.
- **The board is already true** — `src/skills/manage-tickets/SKILL.md`
  §Session closure runs first, so every card this session touched carries its
  status and its comment before the corpus is read.

## The corpus

Three sources, all of them the board, all of them scoped to this session:

- **the cards this session moved to `doing` or `done`**,
- **their `issue_log` comments**,
- **their `task_event` rows.**

- **Nothing else is corpus** — not this conversation, not a folder listing, not
  a diff. `src/app.md` §The board is the only channel already forbids deriving a
  fact from any of them, and a pass reading the transcript would propose from
  something no later reader can check.
- **A lesson that never reached a comment is not in the corpus**, which is what
  the closure ordering above exists to prevent.

## What is a lesson

Capture only these:

- **A correction the user made to how the work was done**, never to what was
  decided. A decision is the card's; a method is a skill's.
- **A technique or an exact command line that was not obvious** and that a later
  session would otherwise re-derive.
- **A skill loaded this session that proved wrong, stale or missing a step.**

## What is never a lesson

- **An environment-dependent failure** — a missing binary, an unmounted volume,
  an ungranted tool, an unconfigured credential. The user can change any of
  them, and a standing rule outlives its cause.
- **A negative claim about a tool, a host or a path** — "the bridge cannot reach
  X", "that tool does not work". One refused request is evidence about one
  request, and a claim written as a property of a whole system hardens into a
  refusal cited for months.
- **A transient error that resolved inside the session.** Where a retry worked,
  the retry is the lesson.
- **A one-off task narrative.**
- **An unresolved failure written up as a workflow**, which presents a sequence
  of dead ends as validated guidance.

A durable technical constraint that survives all five is a `//` note in the file
that owns the mechanism — `src/app.md` §What a file may say — and writing it is
chief_of_staff's like any other behaviour change.

## Procedure

### Step 1 — Choose the target, earliest that fits

1. **A skill this session actually loaded** that covers the territory.
2. **An existing skill that covers the class**, found with
   `python3 src/tools/skill_tools/skills.py list`.
3. **A `references/` file under one of those.**
4. **A new skill**, and only when its name is at the class level.

**A name that only makes sense for this session's task fails the test.** Drop
the proposal rather than minting a skill named after a card, an error string or
a feature.

### Step 2 — Read the skill you propose to change

```
python3 src/tools/skill_tools/skills.py view <name>
```

**Propose against the body you loaded, never against a memory of it.** A patch
proposal names the section it replaces, or the exact text before and after.

### Step 3 — File one card

```
python3 src/tools/ticket_tools/ticket_write.py add-task \
  --title "<Patch|Add> <skill> — <what changes>" \
  --record-type build \
  --assignee chief_of_staff --reporter <your slug> --actor <your slug> \
  --estimate S \
  --description "<the proposed text in full>"
```

- **The description carries the proposed text in full**, in the shape
  `skill_conversion.md` requires, so the card can be applied without deriving it
  again.
- **Link the card the lesson came from** —
  `link-add --task <new> --to-task <source> --type related` — so the evidence is
  one hop away.
- **One proposal per session.** A pass that files three has stopped judging.
- **Nothing to propose is a real outcome** and files no card.

### Step 4 — Stop

**Writing or patching a skill is a behaviour change**, and `src/app.md` §Content
is yours; behavior is chief_of_staff's assigns every one of them to
chief_of_staff working an ordinary card. This pass holds no privileged write: it
files a card with the same `add-task` any agent already has, and the card is
where the change is reviewed and applied.

## Failure modes

- **A proposal written from a skill that was not loaded** → it will patch text
  that does not exist. Step 2 is not optional.
- **A proposal that is really a decision** → the user chose something; that
  belongs in the card that carried the choice, not in a skill.
- **A second proposal in the same session** → the first was not the strongest.
  Pick one.
- **A proposal naming this session's task** → Step 1's name test failed; drop
  it.
- **A skill file written directly** → the pass has become the thing it replaces.

## Audit

- Every proposal card carries `assignee` chief_of_staff and a `reporter` that is
  the agent that ran the pass.
- No proposal card was filed by a session that wrote a skill file in the same
  run.
- Every proposal card links the card its evidence came from.
- No skill under `src/skills/` was written by any agent but chief_of_staff.
