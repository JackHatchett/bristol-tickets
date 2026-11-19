---
name: verifying-a-card
description: Puts the check on a build card before it may close — what is run, and what result would fail it. Use when a build card is being written, and again before one goes done.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3 to read the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/ticket_tools/ticket_write.py
  bristol.subtitle: State how a build card will be checked
---
# verifying-a-card

Input: a build card. Operation: the check below. Output: a card that states how it
will be checked, and a close that rests on that check having been run.

Done means verified rather than written. Nothing here judges the work — that is
`src/skills/importing-a-skill/SKILL.md`'s neighbour, a review — and nothing here
runs a test suite. This is the one rule that a card says how it will be checked
before it may say it is finished.

## Where the verification lives

- **On the card, under Test Criteria**, below its Requirements. The
  requirements say what must be true; a test criterion says what is run to show
  it, and what result would fail it. A requirement is never a test.
- **Never as a second card.** A check filed as its own card is a check that can
  be closed without the work, and work that can be closed without the check.
- **Never in a comment alone.** A comment records what a run produced; the test
  criterion is what says a run is owed.

## What a verification states

Two things, and a step stating only one is not a verification.

- **What is run** — the command, the target, the file to open, the screen to
  look at. `python3 src/tools/test_tools/smoke.py governing_docs` is a
  verification. "Tests pass" is not: it specifies no run.
- **What result would fail it** — the output that means the card is not done.
  A check nothing could fail is a sentence, not a check.

**Who performs it:**

- **The session that made the change runs the check**: a command it runs, a
  value it reads back from config, a changed passage it reads against each
  requirement in turn.
- **The user reviews only where he asked for it, or for anything sent or
  published in his name.** A change to how an application looks is the
  session's to look at, on his running app through computer use —
  `src/skills/checking-a-bristol-change/SKILL.md` §What a visible change
  additionally needs.
- **A card awaiting his review stays assigned to its agent, in `doing`.** Its
  comment gives what to open, what to do there and what would fail it, and
  says the next session asks him whether he has reviewed it before
  continuing.
- **The next session asks him in the session, before any other card** —
  `src/skills/manage-tickets/SKILL.md` §Asking the user for a decision. His
  verdict closes the card or reopens the work; not yet, and the session carries
  on with its queue.

## When a card has none

- **Say so, and write one before starting the work.** One `update-task --id N
  --description …` adds the Test Criteria. A check written after the work could not
  have failed, so the moment to write it is before.
- **Where adding it would change what the card is for**, ask the user rather
  than deciding the scope on the way past. A verification narrows a card, and
  narrowing one is not this pass's to do silently.
- **A fix card takes the same treatment**, in its Expected: the expected line is
  the check, and it states a run and a failing result or it states nothing.

## When it cannot run here

- **Ask the user to clear a blocker only he can clear, and wait.** An
  application keeping a file open, a credential nobody has supplied, a service
  not granted: each is one sentence to him and a card that stays open, never a
  reason to run something else. Where the asking happens is
  `src/skills/manage-tickets/SKILL.md` §Asking the user for a decision.
- **Never substitute a copy of what the check specifies.** A snapshot, a scratch
  database, a duplicate folder: running against one proves the code and not the
  change, so it is preparation for the verification rather than the
  verification. Where a copy is what a session had, the comment says the check
  has not run.
- **Say where it runs, and stop.** A host without the library, a display the
  session has not got: each is a real answer, and the card stays open carrying
  it.
- **Never claim a pass from reading the code.** Reading says the code should
  work; a verification says it did. Where only the first happened, the comment
  says so in those words.
- **A card whose verification cannot run anywhere is the wrong card.** Its
  criteria are written against something unobservable, and rewriting them is the
  work rather than waiving them.

## Closing on it

1. **Run what the Test Criteria specify.**
2. **Put what it produced in the closing comment** — the counts, the failures,
   the output that decided it — rather than the fact that it was run.
3. **Where it failed, the card stays open** and the comment says what failed.
   `update-task-status --id N --status doing` is where it belongs until it
   passes.

## Failure modes

- **A test criterion saying the work will be tested** → it specifies no run and no
  failure; it is the story restated.
- **A closing comment saying the checks pass** → the numbers are the evidence,
  and a reader who was not there has none without them.
- **A verification written after the work** → then it was written to match what
  happened, and it could not have failed.
- **A pass claimed for a run that did not happen** → the one failure this skill
  exists to prevent, and the one nothing downstream can catch.
- **A closing comment offering the real run as a next step** → the real run was
  the check, and offering it is closing the card without it.

## Audit

**Whether any build card closed this session without a test criterion specifying a run,
or with one whose run produced nothing in the comment.** Either is a card that
says verified and means written.
