# git_milestone_coaching — game_designer playbook

Copy-paste git steps with plain-English explanations, at each structural
milestone of a game project's build, for a user with little or no coding
exposure. Triggered from `socratic_design_coaching.md` when a session reaches a
milestone worth saving.

## Preconditions

- **A real structural change just landed** — a scaffold exists, a design phase
  closed, a first playable slice works. **Never run this on a session that
  changed nothing durable.**
- **The project's repository state is known.** Ask rather than assume whether it
  is initialized.

## Procedure

1. **Name the milestone in one line** ("first playable slice," "art pipeline
   locked") so the commit message means something later.
2. **Explain git in one plain sentence with an analogy before any commands, on
   the project's first commit** — a labeled save-state for the whole project
   folder rather than one file.
3. **Give the exact terminal commands one line at a time**, in a copy-paste
   block: `cd` into the project folder, `git init` only if it is not already a
   repo, `git add .`, `git commit -m "<milestone message>"`.
4. **Never introduce GitHub, branching or remotes** unless the user asks or the
   project's own phase calls for it. Going public is usually a later-phase
   decision; the project's board epic (`owner='game_designer'`) says where it
   stands.
5. **Tell the user this is a recoverable point and move on.** Do not explain git
   internals beyond what the milestone needs.

## Logging

**A milestone that carries a new design decision records it in its home** —
worldbuilding to the notebook by the user, mechanics and art to the repo
`design/` — and, where the next session should see it, as an `add-issue-log`
comment on a `doing` card. A purely mechanical commit needs neither.

## Failure modes

- **The user is unsure whether git is initialized** → give the one-line check
  (`git status`) before assuming either way.
- **The user asks for more than the milestone needs** — branching, GitHub,
  rebasing → answer the specific question plainly without expanding scope.
