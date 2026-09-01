---
name: migrate-legacy-agent
description: Converts an older folder of instructions and scripts into an agent this framework can run, and moves its personal content out of the published tree. Use when an agent from a previous setup should be brought in.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/ticket_tools/ticket_write.py
---
# migrate-legacy-agent

Convert a legacy agent bundle — a pre-framework folder of instructions and
tools — into this framework's pattern: a charter under `src/agent_identities/`,
machinery split across skills, tools and protocols, and personal data relocated
out of `/src`. For an agent that does not exist yet, use
`src/skills/create-agent/SKILL.md` instead.

## Preconditions

- **The legacy bundle's location is known and confirmed to still exist.**
- **Step 0's backup question is answered.** Whether an independent backup exists
  decides whether the staging copy may be deleted piece by piece as it is
  ported.

## The hard rule: map data stores, never touch them

A data store in the bundle — a database, a document corpus, credential files, a
browser profile, anything that is bulk content rather than logic — stays exactly
where it is. Note its location and one-line purpose in the closing report and
move on. Redesigning how an agent's data is stored is its own pass; folding it
into a migration means two uncontrolled changes at once.

## Procedure

### Step 0 — Confirm source against backup

**Confirm which copy is being translated and which, if any, is the real
backup**, before deleting anything. Ask the user rather than assuming; the
answer is specific to how that bundle was carried forward.

### Step 1 — Read the whole bundle before writing anything

Read every loader or instruction file (however named — `AGENTS.md`,
`CLAUDE.md`,
`README.md`, a `_bootstrap` or `_agent_instructions` file, anything under a
`charter/` folder), every procedure, prompt and tool script, and the config.
Convert nothing until you know what the agent does and with what toolset.

### Step 2 — Locate the personal-data root

Legacy agents usually keep personal content outside the agent's own folder.
**Find where it actually is, not where the legacy docs claim** — a stale path is
common, and a bounded search can miss a distinct-but-similarly-named mount (an
app's own cloud container against the generic Documents sync). Confirm with the
user rather than guessing past a bounded search, and do not let this block
writing the charter or porting machinery, which do not depend on it.

**Step 2a — Read the data root's own README for logic, not just content.**
Navigational or operational logic sitting there ("which file is the master
version," "where a finished artifact is saved") is ported into `/src`: to a
skill if it is a step of a procedure, to the agent's config entry if it is a
location. A data-folder README is read on demand by a human and never consulted
at session start, so logic left there is invisible at runtime.

**Step 2b — Quarantine any state-tracking file, never inherit it.** A legacy
data root often holds a living `STATE.md`, `CHANGELOG.md` or `next_session.md`.
Check its claims against the board and against the thing it describes by direct
inspection before believing any of them. Migrate still-open, user-confirmed
items into the agent's board epic as tasks
(`tools/ticket_tools/ticket_write.py add-epic` / `add-task`), then move the file
into the data root's `archive/legacy_state_files/`.

### Step 3 — Grep for personal markers before moving a file

Search the whole bundle for the user's name, contact details and other personal
specifics. This tells you which files move verbatim and which need Step 6 first.

### Step 4 — Write the new charter

Create `src/agent_identities/<agent>.md` from
`src/templates/identity_template.md`. Two constraints beyond the template:
`src/app.md` §What a file may say governs what may appear in it, and **no
procedure logic is inlined and no file is named** — a charter carries what a
session must have read before it can act safely and nothing else.

### Step 5 — Split the machinery

- **`src/tools/<agent>/`** — callable scripts, and anything closer to a
  single-purpose callable than a multi-step workflow. A fixed prompt counts as a
  tool when it produces one kind of output.
- **`src/skills/<name>/`** — a procedure a session follows end to end, one
  folder each.
- **`src/skills/external-ai-bridge/references/<agent>.md`** — how that agent
  hands work to an outside party and takes the answer back.
  `src/skills/external-ai-bridge/assets/protocol_template.md` draws the line.

### Step 6 — Depersonalize as you go

Keep every procedural and structural rule; replace hardcoded personal specifics
— names, contact fields, named anecdotes, past employers, absolute paths
containing a username — with a pointer to where that content lives in the data
root, or with a generic placeholder where the content is reusable once
depersonalized. **Treat a generic-looking design default (fonts, colors, layout
spacing) as a judgment call rather than personal data**, and name the ones you
kept in the closing report.

### Step 7 — Delete each original once its replacement is verified

Delete as you go rather than batching to the end, per Step 0's confirmed backup
situation. A piece is verified when its scripts run and no personal markers
remain in the new copy. Leave anything not yet fully translated.

**The staging folder ends empty.** A real, undeleted sub-project sitting in it
is never a valid end state: either it is disposable and gets archived outside
the project, or it is ongoing content and gets a home under `data/`. **Something
unrelated to the agent being migrated gets flagged, never silently relocated**,
unless its disposition is obvious.

### Step 8 — Port only what exists

A migration is a translation pass. **Where the bundle implies a capability that
exists as neither a script nor a documented procedure, say so in the closing
report** rather than writing one to fill the gap.

### Step 9 — Board onboarding

Give the migrated agent its own epic (`epic.owner` = its slug), seeded with the
open items Step 2b carried over. Every quarantined item and every judgment call
becomes a task on that epic, or a comment on the relevant card via
`ticket_write.py add-issue-log`.

### Step 10 — Close with a report in chat

Say what is ported, what is intentionally left behind and why, what data stores
were mapped but not touched, and every judgment call made along the way. The
report is disposable; nothing about it becomes a file.

## Failure modes

- **Step 2's bounded search comes up empty** → confirm with the user before
  concluding the data does not exist. Never fabricate replacement content.
- **A file the bundle points at resolves to nowhere** → surface it and ask; do
  not assume a different file was meant.
