# Tools

Standalone programs, each independently runnable. A folder here names the agent
that maintains it or the function it performs — never who is allowed to run it.
Any agent loads any of these on demand: `src/app.md` §Any capability is
loadable. Editing one is `chief_of_staff`'s.

Style contract for every README here:
`src/templates/identity_template.md` §The governing-doc style contract.

## Index

One line per folder, and the condition that calls for it. Load a folder's README
before running anything in it.

- **`_shared/`** — capabilities promoted out of an agent's own folder.
- **`bristol/`** — the desktop Kanban app over `tickets.db`. Self-contained; it
  imports nothing else in this tree.
- **`ticket_tools/`** — the board's CLI: status readers, the write helper, the
  schema. Any agent, every session.
- **`config_tools/`** — read a config field, resolve a declared data location.
  Any agent, before touching a path outside the repo.
- **`file_management/`** — read-only inspection of folders, photos and
  duplicates, plus a safe move. When a task is about files on disk.
- **`document_tools/`** — PDF-to-Markdown, recipe normalization. When a document
  has to change format.
- **`personal_db/`** — the personal-tracking SQLite database and its xlsx
  snapshots. When a domain needs a durable record rather than a document.
- **`wiki_tools/`** — conventions for a wiki-shaped body of durable facts. When
  an agent reads or writes a knowledge base.
- **`writing_tools/`** — voice capture and draft scaffolding. When the
  deliverable is prose.
- **`voice_capture/`** — the fixed interview that produces a voice profile. Once
  per subject, before the writing tools have a voice to use.
- **`local_assistants/`** — handing bounded, offline work to a local LLM. When
  the task is cheap, private and does not need a frontier model.
- **`test_control/`** and **`test_tools/`** — the manual-QA GUI and its CLI
  counterpart. When work needs a repeatable test pass.
- **`maintenance/`** — diagram builds and housekeeping runs.
- **`zotero/`** — a local Zotero library. Requires Zotero installed.
- **`jd_scraper/`** — the job-alert harvest. Optional, and asks for real setup.
- **`career_coach/`**, **`game_designer/`**, **`teaching_assistant/`** —
  maintained by those agents, loadable by any.
