---
name: version-control-milestone
description: Saves a project to a recoverable point with git, giving the commands one line at a time with what each does. Use when something real just landed — a scaffold exists, a phase closed, or a first working version runs.
license: MIT
compatibility: Needs git available to the user in the project folder.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# version-control-milestone

Walk a project folder to a saved, recoverable point with git. The calling
procedure decides when a milestone has been reached.

## Preconditions

- **A real structural change just landed** — a scaffold exists, a phase closed,
  a first working slice runs. **Never run this on a session that changed nothing
  durable.**
- **The repository state is known.** Ask, or run `git status`, rather than
  assuming whether the folder is already a repo.

## Procedure

1. **Name the milestone in one line** ("first playable slice," "art pipeline
   locked") so the commit message still means something months later.
2. **Give the commands one line at a time, in a copy-paste block, each with what
   it does.**

   ```bash
   cd <project folder>                    # work in the project's own directory
   git init                               # only if it is not already a repo
   git add .                              # stage every change in the folder
   git commit -m "<milestone message>"    # save them as one labelled point
   ```

3. **Keep the scope at a local commit.** GitHub, branches and remotes enter only
   when the user asks or the project's own phase calls for them; where it stands
   is the project's epic on the board.
4. **Say that this point is recoverable, and return to the work.**
5. **Record a decision the milestone carried in the file that owns it**, and,
   where the next session needs it, as one `add-issue-log` comment on a `doing`
   card — `src/skills/manage-tickets/SKILL.md`. A purely mechanical commit
   needs neither.

## Failure modes

- **The user is unsure whether the folder is a repo** → `git status` answers it
  before either assumption.
- **The user asks for more than the milestone needs** — branching, remotes,
  rebasing → answer that question plainly and leave the scope where it was.
