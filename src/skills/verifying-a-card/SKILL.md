---
name: verifying-a-card
description: Puts the check on a build card before it may close — what is run, and what result would fail it. Use when a build card is being written, and again before one goes done.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3 to read the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/ticket_tools/ticket_write.py
---
# verifying-a-card

Input: a build card. Operation: the check below. Output: a card that names how it
will be checked, and a close that rests on that check having been run.

Done means verified rather than written. Nothing here judges the work — that is
`src/skills/importing-a-skill/SKILL.md`'s neighbour, a review — and nothing here
runs a test suite. This is the one rule that a card says how it will be checked
before it may say it is finished.

## Where the verification lives

- **On the card, as its last acceptance criterion**, in the Given/when/then
  shape the rest of them take. A build card's criteria are already the contract;
  the verification is the criterion that names the evidence.
- **Never as a second card.** A check filed as its own card is a check that can
  be closed without the work, and work that can be closed without the check.
- **Never in a comment alone.** A comment records what a run produced; the
  criterion is what says a run is owed.

## What a verification names

Two things, and a step naming only one is not a verification.

- **What is run** — the command, the target, the file to open, the screen to
  look at. `python3 src/tools/test_tools/smoke.py governing_docs` is a
  verification. "Tests pass" is not: it names no run.
- **What result would fail it** — the output that means the card is not done.
  A check nothing could fail is a sentence, not a check.

**A verification that a person performs is still a verification**, and it names
the person's part the same way: what they open, and what they would be looking
at that means it failed.

## When a card has none

- **Say so, and write one before starting the work.** One `update-task --id N
  --description …` adds the criterion. A check written after the work could not
  have failed, so the moment to write it is before.
- **Where adding it would change what the card is for**, ask the user rather
  than deciding the scope on the way past. A verification narrows a card, and
  narrowing one is not this pass's to do silently.
- **A fix card takes the same treatment**, in its Expected: the expected line is
  the check, and it names a run and a failing result or it names nothing.

## When it cannot run here

- **Say where it runs, and stop.** A host without the library, a display the
  session has not got, a service nobody granted: each is a real answer, and the
  card stays open carrying it.
- **Never claim a pass from reading the code.** Reading says the code should
  work; a verification says it did. Where only the first happened, the comment
  says so in those words.
- **A card whose verification cannot run anywhere is the wrong card.** Its
  criteria are written against something unobservable, and rewriting them is the
  work rather than waiving them.

## Closing on it

1. **Run what the criterion names.**
2. **Put what it produced in the closing comment** — the counts, the failures,
   the output that decided it — rather than the fact that it was run.
3. **Where it failed, the card stays open** and the comment says what failed.
   `update-task-status --id N --status doing` is where it belongs until it
   passes.

## Failure modes

- **A criterion saying the work will be tested** → it names no run and no
  failure; it is the story restated.
- **A closing comment saying the checks pass** → the numbers are the evidence,
  and a reader who was not there has none without them.
- **A verification written after the work** → then it was written to match what
  happened, and it could not have failed.
- **A pass claimed for a run that did not happen** → the one failure this skill
  exists to prevent, and the one nothing downstream can catch.

## Audit

**Whether any build card closed this session without a criterion naming a run,
or with one whose run produced nothing in the comment.** Either is a card that
says verified and means written.
