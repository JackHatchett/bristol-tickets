# Tools

Standalone programs, each independently runnable. A folder here names the agent
that maintains it or the function it performs — never who is allowed to run it.
Any agent loads any of these on demand: `src/templates/identity_template.md`
§Boundaries and coordination. Editing one is `chief_of_staff`'s.

Style contract for every README here:
`src/templates/identity_template.md` §The governing-doc style contract.

## A borrowed format's words, and our own

Some strings in this tree are spelled the way somebody else spells them, and
changing one breaks an exchange. Most are spelled the way we choose, and are
free. One test separates them:

**Would a file written by someone else stop being readable, or a file we write
stop being read by them, if this string changed?**

- **Yes — the string belongs to a protocol, and its spelling is not ours to
  improve.** Defer to the format even where its wording is worse than ours. This
  covers the Agent Skills frontmatter keys and the folder names the
  specification defines, and the extension keys a borrowed skill carries, such as
  Hermes's `metadata.hermes.*`. `src/playbooks/skill_conversion.md` §Frontmatter
  is where that set is written down.
- **No — the string is ours, and reads however serves the reader best.** This
  covers every caption and label in `bristol/`, and the stored vocabularies only
  `tickets.db` reads: `status`, `stage`, `record_type`, `estimate`,
  `block_reason`, an epic's status.

**A vocabulary borrowed as an idea is not a protocol.** `block_reason` was taken
from Hermes's `kanban_block(kind=…)` and already spells one value differently,
because nothing outside Bristol reads this board and no board imports another.
Inspiration binds nothing; only an exchange does.

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
- **`skill_tools/`** — the loader for Agent Skills: two roots, frontmatter-only
  listing, and a quarantine a third-party skill leaves only after its code is
  read. When a capability is packaged as a skill folder.
- **`agent_tools/`** — creating an agent: its charter, its config entry, its
  skill attachments and its board epic, from a mandate and its guardrails. When
  the fleet gains a member.
- **`file_management/`** — inspection of folders and photos, deduplication,
  renaming, and a verified move. When a task is about files on disk.
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
