---
name: keeping-a-project-style-sheet
description: Builds and keeps a novel project's style sheet - every invented name with its spelling, capitals, accents and italics, the project's own numbers and dates, and the author's departures from the house style - drawn from the project's notes and kept beside them. Use when a project is copyedited, when its notes coin or change a name, or when the style sheet is checked against the notes.
license: MIT
compatibility: Runs inside a Bristol repository where the Markdown notebook is reachable; needs python3.
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.scripts: src/tools/config_tools/active_project.py src/tools/config_tools/read_config.py src/tools/config_tools/write_config.py
  bristol.subtitle: Keep a project's style sheet
---
# keeping-a-project-style-sheet

Input: a novel project's notes, and any passage being copyedited in it.
Operation: the entries below, drawn from the notes and kept in one sheet.
Output: the project style sheet, agreeing with the notes.

## Where the sheet is

- **The sheet's path is config**: `agents.<agent>.style_sheets.<project>`,
  where `<project>` is the folder `python3
  src/tools/config_tools/active_project.py <your slug>` prints.
- **A project with no sheet gets one** named `_<project name>_style_sheet.md`,
  in the folder the project's content-rules file gives the agent as its
  working home, or, where it gives none, in the folder that contains the
  content-rules file. Write its path to the config key with `write_config.py`.
- **The sheet is one note**, formatted by
  `src/skills/note-formatting/SKILL.md`.

## What the sheet contains

One section each, in this order; an entry gives the form, a one-line gloss,
and a link to the note that settles it.

1. **Names** — people, peoples, places, ships, institutions: spelling,
   capitals, accents and tone marks, and the familiar form beside the formal.
2. **Words of the invented languages** — spelling, accents, whether set
   italic or roman in English prose, and the plural used in English.
3. **Capitals** — titles, ranks, deities, eras and seasons the project
   capitalizes or lowercases.
4. **Compounds and hyphenation** — the project's own compounds, open, closed or
   hyphenated.
5. **Numbers, dates and time** — the calendar's month and day names, how years
   are counted and written, units of measure and how they are written.
6. **Departures from the house style** — each choice of the author's that
   overrides a rule, with the rule's ID from the house style's rules file and
   the form he uses.

## Building and keeping it

- **Draw every entry from the notes**, by the project context skill's
  on-demand lookup: the router or index first, then the one note that settles
  the form. A form the notes do not settle is a question to the author, put in
  the session, and the entry waits for his answer.
- **Add an entry whenever a copyediting pass meets a form the sheet lacks**, and
  whenever a note coins or changes one.
- **A departure enters the sheet only on the author's word**, given in the
  session or written in his notes.
- **The notes win over the sheet.** Where an entry disagrees with the note that
  settles it, the entry is corrected to the note.
- **Two notes that disagree on a form are a continuity finding**, worked by
  `src/skills/checking-a-wiki-for-disagreements/SKILL.md`; the entry follows
  the form the author settles.

## Checking the sheet against the notes

Input: the sheet. Operation: each entry read against the note it links.
Output: every entry agreeing with its note, each correction given in the
comment of the card the check belongs to — the entry before and after.

## Failure modes

- **An entry with no link to a note** → it is a guess; find the note or ask.
- **A form taken from the house style into the sheet** → the sheet states only
  what the project settles; the house style is read from its own file.
