---
name: briefing-the-board
description: Explains the whole board to someone carrying none of it — every epic and every standalone card with its next step, then the backlog — says which card the queue would start at, and stops for the user to choose what to work. Use when a session opens with an ask for a briefing, or when the user asks what is on the board, what is going on, or where everything stands.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/ticket_tools/brief.py
  bristol.subtitle: Explain the whole board from scratch
---

# briefing-the-board

The board read out to the person who owns it, ending on their choice of what to
work. `src/app.md` Phase 3.7 owns when this runs and the rule that no card is
worked until the user picks. Writing and sizing cards is
`src/skills/manage-tickets/SKILL.md`. Style contract:
`src/templates/identity_template.md`.

## Which ask this answers

- **A briefing is the whole board for a reader carrying none of it** — every
  epic, every card under none, the backlog, whoever owns them.
- **"What is next," "where were we" and "status" are the session's own queue**
  — `src/skills/manage-tickets/SKILL.md` §When to read the board answers those,
  and this skill does not run for them.
- **An ask that opens a session, or asks about the board rather than the next card,
  is this one.**

## The read

`python3 src/tools/ticket_tools/brief.py <your slug>`. One command holds the
whole briefing: the epics in flight with cards open, the epics in flight
holding nothing, the cards under no epic, the backlog, what finished most
recently, and the card the calling agent's queue would start at.

- **Read nothing else to compose a briefing.** An epic printed with nothing
  open is a fact about the board, not a prompt to go looking for what it really
  needs.
- **Open a card's own body only where the user asks what that card means.**

## What the briefing says

In this order, as prose the user can follow without opening anything:

- **Each epic in flight with cards open** — what it is for in one sentence of
  your own, who owns it, how much of it is done, and its next step given by
  number and title.
- **Each epic in flight with nothing on the board** — one line each, and say
  what that state means: the epic is open but no card under it is, so it is
  either finished or waiting on a decision.
- **The cards under no epic** — the work belonging to no larger effort, said in
  groups of what they are about rather than card by card where several share a
  subject.
- **The backlog** — the same shape, and say what a backlog is: real work, off
  the board, that nothing starts from until the user moves it on.
- **What finished most recently** — the last few closed cards, which is what
  answers "where did we leave off" for an effort the user has been away from.
- **The card the queue would start at** — by number and title, and why that one
  is first.

## How it reads

- **`src/app.md` §What you say to the user reaches every term the board has** —
  epic, card, the active board, the backlog, `doing` against `todo`, a tier, a
  blocker, an assignee. The user owns the board and is not carrying its
  vocabulary.
- **Name every card by its number and its title.** The number is what the user
  answers with.
- **Say what an epic is for in your own words**, taken from its description and
  its open cards. Never paste the description.
- **Give nothing that is stalled the room given to what is moving.**
- **Say what an effort is for, never the edits that got it here.**

## The stop

- **End on one line offering the three answers**: continue with that card,
  start a different card, or take up another epic.
- **Work nothing until the user answers**, whatever the queue says and however
  small the next card looks.
- **A pick of an epic takes that epic's next step** — say which card
  that is before starting it.
- **A pick of a card is the queue's top for this session**, and the
  order on the board is untouched by the choice.
- **Put the picked card in `doing` before the work** — `src/app.md` Phase 3.5.
