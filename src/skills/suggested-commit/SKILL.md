---
name: suggested-commit
description: Turn a closing session's writes into a commit to paste.
license: MIT
compatibility: Needs git available to the user; the procedure runs no git command.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# suggested-commit

Turn the files a session wrote into a commit the user can paste unedited.

## Input

- **The paths this session wrote**, and, for each, whether it resolves inside a
  git working tree. That test alone decides the offer; the agent running, the
  card worked and the size of the diff decide nothing.
- **`session.suggested_commit`, read now rather than at session start**, default
  `true`. False produces nothing, and the close reads as it otherwise would.

## Operation

- **Group the written paths by working tree, and compose one message per tree**
  naming in one line what changed, drawn from the work rather than from ticket
  numbers.
- **Render the repository root as the user's own shell would accept it.**
  Resolve it against `drives.local_home.path`; a session-mount path is a broken
  block, not a rendering detail.
- **Emit one block per tree, and no annotation.** One line offering it, then:

  ```bash
  cd <repository root>
  git add -A
  git commit -m "<what changed>"
  ```

- **Never run the commit.** The offer is the deliverable.

## Output

- **The board writes land first; the block is the last thing in the message.**
- **One block per working tree**, each complete on its own.

## Boundary

`src/skills/version-control-milestone/SKILL.md` is the coached procedure: a
user learning git, each command annotated, at a structural milestone the calling
procedure names. This one is mechanical, fires whenever a session closes, and
annotates nothing.
