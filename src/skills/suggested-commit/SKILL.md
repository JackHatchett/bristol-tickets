---
name: suggested-commit
description: Commits the files a session changed, or writes out the git commands for the user to run, as the user's setting says. Use when a session that edited files in a git repository is finishing.
license: MIT
compatibility: Needs git where the repository is; in Cowork, git runs in the shell on the user's computer.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.subtitle: Commit a session's changes, or write the commands
---
# suggested-commit

Turn the files a session wrote into a commit — made by the session, or pasted
by the user — as `session.suggested_commit` says.

## Input

- **The paths this session wrote**, and, for each, whether it resolves inside a
  git working tree. That test alone decides that git is involved; the agent
  running, the card worked and the size of the diff decide nothing.
- **`session.suggested_commit`, read now rather than at session start**:
  - `commit` — the session commits the files itself, by §Committing;
  - `block`, or `true` from an older configuration, and the default — the
    session ends with a block for the user to paste, by §The block;
  - `off`, or `false` — the session leaves git alone, and the close is what it
    otherwise is.

## Composing the commit

- **Group the written paths by working tree, and compose one message per tree**
  saying in one line what changed, drawn from the work rather than from ticket
  numbers.
- **End the message with any attribution lines the host asks for.**

## Committing

Run in the shell that holds the repository — on the user's computer in Cowork,
by `src/skills/working-in-cowork/SKILL.md` §Running git in a connected folder.

1. **Clear git's lock files**, by that section's route.
2. **Stage the paths this session wrote, by name** — `git add -- <path> …`. The
   user's own changes in the same tree stay his to commit.
3. **Commit** — `git commit -m "<message>"`.
4. **Clear the lock files again, and run no git command after it.**
5. **Say the commit in chat**: the repository, the short hash and the message.

Where a step fails, say what git printed and fall back to §The block for the
same paths, so the user still has the commit in hand.

## The block

- **Render the repository root as the user's own shell would accept it.**
  Resolve it against `drives.local_home.path`; a session-mount path is a broken
  block, not a rendering detail.
- **Emit one block per tree, and no annotation.** One line offering it, then:

  ```bash
  cd <repository root>
  git add -A
  git commit -m "<what changed>"
  ```

## Output

- **The board writes land first, then the commit report or the block, then the
  To Continue block where there is one** —
  `src/skills/manage-tickets/SKILL.md` §Session closure, step 9, which is the
  last thing in the message because it is what the user acts on next.
- **One commit, or one block, per working tree**, each complete on its own.

## Boundary

`src/skills/version-control-milestone/SKILL.md` is the coached procedure: a
user learning git, each command annotated, at a structural milestone the calling
procedure gives. This one is mechanical, fires whenever a session closes, and
annotates nothing.
