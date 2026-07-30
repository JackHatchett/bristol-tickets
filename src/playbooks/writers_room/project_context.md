# project_context.md — writers_room playbook

**Always-on, not triggered** — read at the start and close of every session,
the same way `career_coach`'s `session_closure.md` is
([playbooks/career_coach/session_closure.md]). This is the project-content
counterpart to that pattern: it governs which *novel-project* files get
loaded, not the agent's own roadmap-db session tracking, which is a separate
step and happens first (per the charter's standard Phase 3 pattern).

## Session start

1. After the standard roadmap-db check (including backlog cards assigned to
   you), identify the active
   project. The config's project links (`/config`) resolve which project
   folder is active; there is normally exactly one, but the layout supports
   more than one novel project over time.
2. Read that project's own state file (its `STATE.md` or equivalent) for
   the previous session's updates and the recommended next focus. Echo a
   short summary before waiting on the user: current focus, open blockers,
   the last handful of decisions.
3. Read that project's own content-rules file (its `AGENTS.md` or
   equivalent) before authoring or judging any content in that project —
   not just at session start, but the first time in a session that content
   work actually begins. Content rules bind every crew role working on that
   project, including external roles briefed through
   `protocols/writers_room/gemini_crew_handoff.md`.
4. Do **not** bulk-read wiki files at session start. On-demand lookup only
   (see below) — a wiki file gets read when a specific question needs it. The
   wiki is user-authored and read-only to this agent (see `writers_room.md`
   §2.7); there is no 'canon' concept and nothing to re-vet.
5. Do **not** read `private/`-equivalent personal-notes folders unless the
   user names a specific file. This is a hard rule, not a default-closed
   convenience — never list, scan, or summarize that folder unprompted.

## On-demand lookup

When a request needs a project fact not already in hand: read that
project's router/index file to find which wiki file holds it, read **that
one file**, continue. Needing three files to answer one question means the
request is under-specified — ask, don't keep reading. Conventions:
`tools/wiki_tools/` (read-and-reconcile; no ratification gate).

## End of session

On "end of session" / "update everything," or the natural end of a content
work session — the project's state file and decision log live in the
user-authored wiki, which is read-only to this agent, so you **prepare** these
updates as a summary in the shared agent-output dir
(`markdown_notebook.agent_output_dir`) for the user to fold in; you don't write
the wiki files yourself:

1. Summarize the project's state update: current focus, blockers, the most
   recent handful of settled decisions, a pointer to this session's log entry.
2. Summarize a short session log entry — a diff since last time, not a
   snapshot. A few lines is normal.
3. Do not regenerate the encyclopedia or recap already-settled decisions.

This project-content state file is a deliberate, scoped exception to this
framework's general "no state tracking outside the roadmap database"
principle — the same shape of exception `career_coach` makes for its
applications tracker (see that agent's charter §2.2). It tracks the
*novel's* narrative progress (what's settled in the story, what's still
open in the worldbuilding), not this agent's own operational tasks, which
stay in its roadmap epic. Don't collapse the two, and don't try to migrate
this file's contents into the roadmap db — they answer different
questions.
