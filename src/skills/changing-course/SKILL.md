---
name: changing-course
description: Lands an abandoned or redirected plan on the board — which cards die, which are rewritten, which are new — and leaves the plan stating the new intent. Use when what was agreed has stopped being what should happen.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3 to write the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/ticket_tools/ticket_write.py
---
# changing-course

Input: a plan, or a run of cards, that has stopped being what should happen.
Operation: the passes below. Output: a board that reflects the new course, and a
plan stating the new intent.

A change of course is card writes. It is not a conversation, not a section in a
document, and not a note explaining what happened — `src/app.md` §The board is
the only channel, and §What a file may say, which bans the history a change of
course is most tempted to write down.

## What has to be true before anything moves

- **The new course is the user's, not this pass's.** Noticing a plan has stopped
  working is an agent's job; deciding what replaces it is a decision, and a
  decision is the user's — `src/templates/identity_template.md` §Settled
  decisions.
- **Say what stopped working in one line**, and say it against the goal rather
  than as a list of what went wrong.

## The three passes, in order

**1. Every card the old course produced gets a deliberate end.** Each one, no
exceptions and no leaving the rest for later:

- **Done** where the work landed and still stands.
- **Rewritten** where the card's subject survives and its shape does not:
  `update-task --id N --title … --description …`, and one comment saying what
  the card now asks for. This is the commonest of the three and the one that
  keeps the board's history intact.
- **Archived** where the work should not happen at all: `set-stage --id N
  --stage archive`, with a comment naming what replaced it. Archiving is not
  deleting, and a card that stops being worked without being archived is the
  rot this pass exists to prevent.

**2. The new course becomes cards.** `add-task` for what the old ones do not
cover, each scoped to one agent's context, each with its assignee, its estimate
and a verification criterion — `src/skills/verifying-a-card/SKILL.md`.

**3. The queue is reordered to the new course.** `set-order --id N --position K`,
and a blocker that has changed is re-linked. An order left from the old course
is a plan nobody agreed to, quietly still running.

## The plan document

- **Revise it to state the new intent**, and nothing else —
  `src/skills/writing-a-plan/SKILL.md` owns its shape.
- **It carries no history of the old course.** Not a superseded section, not a
  what-changed note, not a struck-through phase. The board's change log is where
  the old course is legible, and it is written by triggers rather than by
  anyone's recollection.
- **Where no plan document exists, none is written for this.** A change of
  course is not an occasion to start one.

## Failure modes

- **The change lives in the conversation** → the next session opens the board
  and finds the old course still running.
- **Cards from the old course left in `todo`** → pass 1 was skipped for the ones
  that were awkward, which is every one that mattered.
- **A new card filed while the old one it replaces stays open** → two cards for
  one job, and neither says which is live.
- **The plan gains a section explaining the change** → §What a file may say; the
  document states intent, and what happened is the board's.
- **The order untouched** → the board still works the old course whatever the
  cards now say.

## Audit

**Whether every card the old course produced is done, rewritten or archived, and
whether the plan document mentions the old course at all.** One card left in
`todo` from a course nobody is running is the whole failure.
