# project_context — game_designer playbook

Always-on: read at the start and close of every session. It governs which
project-content files get loaded, after the charter's §2.1 board snapshot, which
happens first. Where design content lives is `design_proposals.md` §The two
homes.

## Session start

1. **Identify the active game project** after the board snapshot.
   `config/config.local.json`'s Code Projects table resolves which project
   folder is active; **confirm which one the user means** where more than one is
   tracked and context does not make it obvious.
2. **Take phase, blockers and next focus from the epic the snapshot already
   returned** — its name, `status`, `description` and `next_action`, plus its
   ordered task queue. **Never look for a project-local state file to re-derive
   them from.** Echo a short summary before waiting on the user.
3. **Read this agent's cards for recent design decisions.** There is no canon
   record and no separate decision log.
4. **Never bulk-read the notebook or the repo `design/` at session start.**
   On-demand lookup only.
5. **The notebook wiki is a read-only lookup resource, not a standing context
   source.** Read a specific note when a request needs that fact, never sweep it,
   and never write into the wiki directories. Proposing a page or fact goes
   through `design_proposals.md`.
6. **Read a project's own frozen local state file where it has one** (the
   charter's §2.2 exception). This is a per-project fact to confirm, never a
   default to assume.

## On-demand lookup

- **Worldbuilding** → the user's notebook, in the wiki directory this project
  names in `/config`. That directory's map-of-content note and its wiki-links
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
4. **Run `src/playbooks/_shared/version_control_milestone.md` before ending**
   where the session reached a structural milestone.

**Never create a project-local state or tracking bundle for a new project.** The
board is the default; a project-local state file is an exception that needs its
own justification.
