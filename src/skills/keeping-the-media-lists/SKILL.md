---
name: keeping-the-media-lists
description: Adds a film, show, stage work or book the user means to get to onto his watchlist or his reading list - the general list at the top, segmented by genre with who recommended it, and below it a section for each project that sends media to watch or read and analyze. Use when someone recommends something to watch or read, or when a project surfaces a work the user has not seen or read.
license: MIT
compatibility: Runs where the Markdown notebook is reachable; needs python3 to read config.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/config_tools/read_config.py
  bristol.subtitle: Keep the watchlist and the reading list
---
# keeping-the-media-lists

Input: a work the user has not seen or read, and where it came from. Operation:
the rules below. Output: one bullet on the watchlist or the reading list.

Every rule of `src/skills/note-formatting/SKILL.md` holds for both notes. The
sections below are the notes' own, and win for those sections by that skill's
first boundary.

## Which list

- **Films, television and stage works go on the watchlist; books go on the
  reading list.** Read each note's location from config —
  `python3 src/tools/config_tools/read_config.py markdown_notebook.watchlist_path`
  and `markdown_notebook.reading_list_path`.
- **A work already on the list gets its new reason added to its own bullet**,
  never a second bullet.

## The shape of each note

- **The general list comes first**: one `##` section per genre, holding
  recommendations that arrive from outside any project, such as a friend's. A
  genre with no entry has no section.
- **Below it, one `##` section per project** that sends media to watch or read
  and analyze. Plot Archetypes is the first; a project that needs one adds its
  own section beneath the last.
- **Entries are plain bullets, never checkboxes.** The user removes an entry
  himself once he has seen or read the work, and moves what it held into a
  media note.

## The bullet

- **First line: the title and its year** — `Jaws (1975)`; a series takes its
  run, `(2005 to 2008)`.
- **Nested under it, one link to the work's page**, as `[Wikipedia](url)` or the
  page the recommendation came with.
- **Then one nested line giving why it is there:**
  - on the general list, who recommended it — `Recommended by <who>` — where
    someone did;
  - in a project section, what it serves — in Plot Archetypes,
    `Source of [[sheet|Sheet Title]]` for each beat sheet it sources.

## Who keeps which part

- **`librarian` keeps the general list**, from recommendations unrelated to
  writing.
- **`writers_room` keeps the Plot Archetypes section**, from
  `src/skills/building-a-beat-sheet/SKILL.md` §7.
- **A project section is kept by the agent whose project sends it the media.**
