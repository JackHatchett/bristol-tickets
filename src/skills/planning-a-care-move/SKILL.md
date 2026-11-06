---
name: planning-a-care-move
description: Sequences a family member's move into new housing or new care - across a state line or across town - so that her income, coverage and help never lapse on the way, with the bridge arrangement while she waits, the long pole that sets the date, and a card for every step that carries one. Use when a family member may move, when the destination is still being chosen, or when a waitlist or a move date changes.
license: MIT
compatibility: Needs python3 to resolve the declared data folder and to write the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: care_manager
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/ticket_tools/ticket_write.py
  bristol.subtitle: Plan a family member's move
---
# planning-a-care-move

Input: her profile (`src/skills/assessing-a-care-recipient/SKILL.md`), her
benefits worked for both places (`src/skills/working-a-benefit/SKILL.md`), and
where the family wants her to end up. Operation: the procedure below. Output: a
move plan in her folder, and a card for every step that carries a date.

## The destination options

- **Lay out every kind of place she could end up**, from least to most care:
  her own subsidized apartment near the family, living with the family with
  home care, an adult home or enriched housing, assisted living (and the state's
  Medicaid-paid version where one exists), a nursing home. Each with what she
  needs to qualify, what pays for it on her income, and how it is found.
- **Weigh them with `src/skills/explaining-a-recommendation/SKILL.md`**, and
  put the choice to the person and the family. The plan follows the choice.

## The plan's parts

- **What ends where she lives now** - each program that stops at the line,
  when, and what notice it needs: a lease's notice period, a subsidy's move-out
  rule, Medicaid's closure.
- **What starts where she is going** - each program she applies for, its
  residency rule, and the earliest day she may apply.
- **The bridge** - where she lives and who pays for her care between leaving
  and her new place opening, usually with the family. Record what the bridge
  does to each benefit, from the benefits document: a reduction for support
  received in kind, a household counted for a means test, a caregiver program
  that pays a relative.
- **The long pole** - the step whose path from today is longest, almost always
  a waitlist or a facility's opening, and what it blocks. Name it even where no
  wait is published, and say the duration is unavailable.
- **What runs in parallel with it** - applications she may file before moving,
  waitlists she may join from out of state, documents to gather, medical
  records and prescriptions to transfer, a Medicare plan to change where hers
  is regional, a doctor to find.
- **The day of the move** - address changes with Social Security and Medicare,
  the mail, the bank, the pharmacy.

## Order

- **Order every step by prerequisite**, so each sits after what has to be true
  before it.
- **Start no step that ends a benefit before the step that replaces it has a
  date**, unless the person and the family have chosen the gap knowing its
  cost.
- **Count the month before filing** - documents to request, appointments to
  book, a physician's form - in each step's path.

## Where it goes

- **One move plan per move**, in her folder in
  `agents.care_manager.key_data_paths`, written per
  `src/skills/writing-a-plan/SKILL.md`: intent and order, never progress.
- **Every step carrying a date is a card**, assigned to the user where the act
  is his or hers (a call, a signature, a notice) and to `care_manager` where it
  is research, linked `blocked-by` its prerequisites.
- **Every decision the family has to make is put to the user in the session**,
  per `src/skills/manage-tickets/SKILL.md` §Asking the user for a decision.

## Procedure

1. **Check the inputs stand** - her profile, her benefits in both places - and
   work whichever is missing first.
2. **Lay out the destination options** and put the choice.
3. **Write the four lists**: ends, starts, bridge, parallel.
4. **Order them, and name the long pole.**
5. **Write the plan and file the cards**, linked by prerequisite.
6. **Read it back** for any step that ends a benefit before its replacement
   has a date.

## Failure modes

- **A move date set before the waitlists are known** -> the long pole was never
  found.
- **The bridge treated as free** -> its effect on each benefit was never read.
- **A Medicare Advantage or drug plan left unchanged** -> plans are regional,
  and a move outside the area ends coverage.

## Audit

**Whether, on every day between today and her settling in, she has somewhere to
live, a way to pay for it, and coverage for her care.**
