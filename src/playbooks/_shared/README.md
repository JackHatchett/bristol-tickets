# playbooks/_shared/

Procedures that serve more than one agent. Maintained by `chief_of_staff`;
loading is `src/app.md` §Any capability is loadable.

## Index

One line per capability, and the condition that calls for it.

- **`manage_tickets.md`** — how any agent writes to the board: record types,
  description format, effort sizing, session closure. Load it before creating,
  editing or closing a card.
- **`inline_teaching.md`** — calibrating the register and defining a term as the
  work needs it. Load it inside a coaching procedure, on any subject the user is
  learning.
- **`notebook_proposal.md`** — routing a proposed fact into the user's
  wiki-linked notebook without writing into it. Load it when an idea's home is
  the notebook, whoever proposed it.
- **`version_control_milestone.md`** — walking a project folder to a saved
  commit, each command with what it does. Load it when a structural change has
  landed and the work should be recoverable.
- **`suggested_commit.md`** — rendering the session's own writes as a commit
  block to paste. Load it when a session halts for room, per `src/app.md`
  Phase 4.

## What belongs here

- **Promote a procedure here once a second agent genuinely reuses the same
  shape.** A procedure only one agent runs stays in that agent's folder.
- **Keep a promoted procedure free of its origin domain.** A capability that
  still names one agent's subject matter has been moved rather than
  generalized.
