# git_milestone_coaching.md — game_designer playbook

## Purpose
Give copy-paste git steps with plain-English explanations at each
structural milestone of a game project's build, for a user with little to
no coding exposure. Triggered from `socratic_design_coaching.md` whenever a
session reaches a milestone worth saving — never run preemptively on a
session that didn't actually change anything durable.

## Preconditions
- A real, structural change just landed (a scaffold exists, a design phase
  closed, a first playable slice works) — not routine chat-only design
  discussion.
- The project's own repository state is known (initialized or not); if
  unsure, ask rather than assume.

## Procedure
1. Name the milestone in one line ("first playable slice," "art pipeline
   locked," etc.) so the commit message will mean something later.
2. If this is the project's first commit, explain what git is in one plain
   sentence with an analogy the user can hold onto (a labeled save-state for
   the whole project folder, not just one file) before giving any commands.
3. Give the exact terminal commands, one line at a time, in a copy-paste
   block — `cd` into the project folder, `git init` only if not already a
   repo, `git add .`, `git commit -m "<milestone message>"`.
4. Do not introduce GitHub, branching, or remotes unless the user asks or
   the project's own roadmap phase calls for it (see the project's roadmap
   epic, `owner='game_designer'` in `data/*/roadmap/roadmap.db` — going
   public/remote is usually a later-phase decision, not a day-one one).
5. After the commit, remind the user this is now a recoverable point they
   can return to, and move on — don't over-explain git internals beyond
   what's needed for this milestone.

## Tools Used
None — this is a coaching script, not a callable.

## Logging Requirements
If the milestone also represents a new design decision, record it in its home
(worldbuilding → the user documents it in the notebook; mechanics/art → the
repo `design/`) and, if it's worth flagging to the
next session, put it on a `doing` card via `roadmap_write.py add-issue-log`.
A purely mechanical commit
(no new design content) needs neither — just the git steps themselves. (There
is no separate per-epic log.)

## Failure Modes
- **User unsure if git is already initialized.** Give a one-line check
  command (`git status`) before assuming either way.
- **User asks for more than the current milestone needs** (branching,
  GitHub, rebasing). Answer the specific question plainly, but don't expand
  scope beyond what the milestone requires unless asked.

## Human Audit Notes
- Whether commit messages accumulated across a project actually read as a
  useful history, or have drifted into noise worth tidying.
