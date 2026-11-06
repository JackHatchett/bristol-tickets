---
name: building-a-household-budget
description: Builds the budget a household runs on from what the money actually did - income, fixed costs, everyday spending and the bills that come once a year - read from the household's own statements, and sets the targets the household chooses against it. Use when a household wants a budget, when income or rent changes, or when a month's spending is to be read against the plan.
license: MIT
compatibility: Needs python3 to resolve the declared data folder and to write the board; reads statements where they are kept.
metadata:
  bristol.kind: playbook
  bristol.maintainer: financial_planner
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/ticket_tools/ticket_write.py
  bristol.subtitle: Build a household budget
---
# building-a-household-budget

Input: the household's statements - bank, card, pay stubs - for the last three
months at least, twelve where the user has them. Operation: the procedure
below. Output: a budget spreadsheet in the household's folder, and a card for
each date it surfaces.

## What it is built from

- **Actual spending first, targets second.** A budget written from what the
  household thinks it spends is wrong in every category it forgot.
- **Read statements where they are kept**, and copy only date, payee, amount and
  account. An account is told apart by its last four digits at most.
- **Twelve months finds the bills that come once a year** - insurance, renewals,
  taxes, gifts - which three months misses. Where only three are given, ask the
  user for the yearly ones by name.
- **Take whose money is whose from the user.** A joint account, his own and his
  partner's are kept apart where they are apart, and a figure about the
  partner's own accounts enters only as the user brings it.

## Its shape

- **Income** - each source, net of what is withheld, monthly.
- **Fixed** - rent, utilities, insurance, debt payments, subscriptions.
- **Everyday** - groceries, eating out, transport, health, household, personal.
- **Once a year**, divided into twelve and set aside monthly.
- **Saving and goals** - an emergency fund, a goal with a date, retirement.
- **What is left**, which is the line the household reads.
- **Each category shows the actual monthly average beside the target**, and the
  target is the household's choice. A rule of thumb (a share of income for
  needs, wants and saving) is offered as one way to set targets, named as a
  convention, never as the rule.

## Where it goes

- **One spreadsheet**, in the folder `agents.financial_planner.key_data_paths`
  declares, resolved with `data_paths.ensure_dir()` at the moment of the write,
  in whatever format the user keeps his sheets in.
- **A monthly review is a recurring card**; a bill's due date or a renewal the
  statements show is a card, never a cell note.

## Procedure

1. **Ask for the statements** and where they are, and whose each account is.
2. **Extract** date, payee, amount and account into the sheet's raw tab, and
   categorize every line. Ask about payees the categories cannot place.
3. **Average each category monthly**, and set the once-a-year lines.
4. **Put targets to the user** category by category, with the actual beside
   each, per `src/skills/explaining-a-recommendation/SKILL.md` where a choice
   could go more than one way.
5. **Read the totals back by recomputing them** from the raw tab, and file the
   cards.

## Failure modes

- **Income gross of withholding** -> every line after it is overstated.
- **No once-a-year bills** -> the first insurance renewal breaks the budget.
- **A full account number in the sheet** -> cut it to the last four.

## Audit

**Whether the household can tell, on the first of a month, how much it may
spend on what without reopening a statement.**
