---
name: writing-a-plan
description: Writes a planning document saying what will be built and in what order, and keeps progress out of it. Use when a body of work needs its intent written down, or an existing plan needs revising.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/config_tools/data_paths.py
---
# writing-a-plan

Input: intent for a body of work — what is to be built, in what order, and why.
Operation: the procedure below. Output: one planning document in the declared
planning home.

A plan says what is intended; the board says what is true. Every rule here
follows from that split, and `src/app.md` §What a file may say holds the ban it
rests on.

## Where it goes, and who writes it

- **A plan goes in `markdown_notebook.plans_dir`**, resolved through
  `src/tools/config_tools/data_paths.py`. The location is declared in
  configuration and is never chosen per document.
- **An agent whose `notebook_access` reaches the workspace zone writes the file
  itself** — `config`'s `markdown_notebook` §ZONES names the zones, and
  `agents.<slug>.notebook_access` names the ones that agent reaches.
- **Every other agent gives its plan to the user in chat**, because `plans_dir`
  and `agent_output_dir` both sit inside that same zone. Producing planning
  material is content any agent may write; writing into the notebook is access,
  and that config key is what grants it.
- **A plan that changes how an agent works is still behavior** — `src/app.md`
  §Content is yours; behavior is chief_of_staff's, whoever may write the file.

## Procedure

1. **State what is to be built, in what order, and why.**
2. **Name the phases the plan is a plan of.** They are its subject, and
   `src/app.md` says so where it bans deferral.
3. **Give the dates it intends**, where it intends any.
4. **Put nothing in it that answers "where are we?"** What has been built, what
   broke, what is next, and how the work is tracking against a date are the
   board's, and a card is where each one goes.
5. **Let the structure carry the meaning.** A heading names the thing it covers,
   one item sits on one line, and a sequence is written as an order rather than
   implied by the prose around it. A reader who infers nothing still gets the
   plan.
6. **Define every term at first use**, per `src/app.md` Phase 4. A concept
   needing more than the plan can carry gets its own note —
   `src/skills/splitting-an-explanation/SKILL.md`.

## The log test

**Take one sentence and ask whether it will be false next week with nobody
having edited the document.** If it will, it is state: cut it and put it on the
board. A document where several sentences fail this has become a log of the work
rather than a plan for it.

**Revising a plan whose course has changed is
`src/skills/changing-course/SKILL.md`**, because the board writes come first and
the document follows them.

## Reading a borrowed planning template

One test disposes of most of a template written elsewhere: **a section that
answers where are we is the board's**, and it comes out. Four shapes it catches.

- **A table of decisions, questions or owners with a status column.** Each row is
  a card, and the column is its status or its block reason.
- **A Now / Next / Later grid, and the defer list beside it.** Both are board
  columns, and `src/app.md` §What a file may say bans deferral in a file
  outright.
- **A copy-paste handoff to another tool.** The reader carrying work between two
  places is what `src/app.md` §The board is the only channel exists to stop.
- **A provenance or evidence map.** The equivalent here is links on the card,
  which stay attached to the work rather than aging inside a document.

**An effort figure in hours or days is not sizing.** A card's size is a share of
a usage budget — `src/skills/manage-tickets/SKILL.md` §Effort sizing — and a plan
carrying hours has started forecasting.

**What usually survives is the analytical opening**: the situation as it stands,
the one constraint that gates the rest, the ranked efforts, and a pre-mortem.
Those state intent, and intent is what a plan is.

## Failure modes

- **A heading that is a status** → step 4; that heading is a board column.
- **A phase that names a later time rather than work** → deferral, not subject;
  it is a card.
- **A date carrying how far along it is** → step 3 permits the date and step 4
  refuses the rest.
- **The plan and the board disagree** → the plan has started reporting; cut
  what reports.

## Audit

**Whether anything in the plan would have to be edited by the work proceeding.**
One sentence like that is the whole failure: the document is now a second place
to look for what is happening, and `src/app.md` §The board is the only channel
is what it breaks.
