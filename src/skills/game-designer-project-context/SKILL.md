---
name: game-designer-project-context
description: Loads the files for whichever game project is active at the start of a session and closes them out at the end, so the session knows the game it is working on. Use at the open and close of every session on a game.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: game_designer
  bristol.scripts: src/tools/config_tools/active_project.py
  bristol.subtitle: Open and close a game project session
---
# game-designer-project-context

Governs which project-content files get loaded, after the charter's §2.1 board
snapshot, which happens first. Where design content lives is
`src/skills/design-proposals/SKILL.md` §The two homes.

## Session start

1. **Identify the active game project** after the board snapshot, with `python3
   src/tools/config_tools/active_project.py game_designer`, and **say which one
   it is before reading any of its content.** Where the user says he is working
   another, move with `--set <project>`. Where it reports no project, ask which
   folder is meant.
2. **Take phase, blockers and next focus from the epic the snapshot already
   returned** — its name, `status`, `description` and `next_action`, plus its
   ordered task queue. **Never look for a project-local state file to re-derive
   them from.** Echo a short summary before waiting on the user.
3. **Read this agent's cards for recent design decisions.** There is no canon
   record and no separate decision log.
4. **Never bulk-read the notebook or the repo `design/` at session start.**
   On-demand lookup only.
5. **The notebook wiki is a lookup resource, not a standing context source.**
   Read a specific note when a request needs that fact, never sweep it.
   Proposing a page or fact goes through
   `src/skills/design-proposals/SKILL.md`.
6. **Never read a project-local state, to-do or session-log file**, frozen or
   otherwise. Where one is in a project that arrived from elsewhere, name it to
   the user and leave it to him — `game_designer.md` §The Project and the
   Notebook.

## On-demand lookup

- **Worldbuilding** → the user's notebook, in the wiki directory this project
  sets in `/config`. That directory's map-of-content note and its wiki-links
  are the index.
- **Mechanics and art** → the repo `design/` folder's file names.

**Read one target file per question.** Needing three files to answer one
question means the request is under-specified — ask rather than keep reading.

**Never conclude a project's data root does not exist because a stale reference
missed it.** Where a project's files point at a location a first bounded search
does not find, say so and ask; a legacy reference is frequently a stale pointer
to real content that moved.

## End of session

On "end of session," "update everything," or the natural end of a design
session:

1. **Update the project's board epic** — `status` and `next_action` where the
   phase or immediate focus changed — via `ticket_write.py`. There is no
   `update-epic` subcommand; ask before hand-editing the database, or file the
   gap as a card assigned to `chief_of_staff`.
2. **Put where things stand on the cards, never in a note.** The next session
   learns the state from the board: anything to pick up is a `doing` card at the
   top of its column with `assignee: game_designer`, and a one-line
   `add-issue-log` comment carries the detail. **Durable design facts go to
   their home, never onto a card.**
3. **Close a task the session's decision resolved** —
   `ticket_write.py update-task-status --id N --status done` — rather than
   leaving it to go stale in the queue.
4. **Run `src/skills/version-control-milestone/SKILL.md` before ending**
   where the session reached a structural milestone.

**Never create a project-local state or tracking bundle**, for a new project or
an old one. The board is the only channel — `src/app.md`, the section of that
name — and there is no exception to it.
