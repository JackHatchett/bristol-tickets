# Migrate Legacy Agent — chief_of_staff Playbook

## Purpose
Convert a legacy agent bundle (a pre-reorg folder of instructions/tools that
predates this framework) into the current framework's pattern: a charter
under `agent_identities/`, playbooks/tools/protocols split correctly, and
personal/instance data relocated out of `/src` entirely. This is the sibling
of `playbooks/create_agent.md`, which is for bootstrapping a brand-new agent
from nothing — do not use that one for a migration; use this instead.

Every agent in this system has been migrated at least
once (chief_of_staff, career_coach, writers_room, game_designer, librarian,
client_services, teaching_assistant) — no legacy bundle is currently
outstanding. This playbook is kept for the day a forgotten pre-reorg bundle
turns up somewhere (a backup drive, an old repo, etc.).

## Preconditions
- The legacy bundle's location is known and confirmed to still exist.
- A likely-real backup of the bundle has been identified, or the user has
  confirmed there isn't one (see Step 0) — this determines whether the
  staging copy can be deleted piece-by-piece as it's ported, or must be
  handled more conservatively.

## Procedure

### The one hard rule: map data stores, don't touch them
If the legacy bundle includes an actual data store — a database, a large
document/knowledge corpus, credential files, a browser cache/profile,
anything that's bulk *content* rather than *logic* — leave it exactly where
it is. Migrating an agent's identity and machinery is not the moment to also
redesign how its data is stored. Note the store's location and one-line
purpose in the closing report; don't move it, don't restructure it, don't
invent a schema for it. A real redesign (e.g. flat files into a queried
database) is its own dedicated pass later, not something to fold into
routine migration.

### Step 0 — Confirm source vs. backup
Before deleting anything, confirm which copy of the legacy bundle is the one
being translated and which (if any) is the real backup. If an independent
pre-reorg backup tree exists (check with the user if unsure), the
migration-staging copy can be deleted piece by piece as each part is
ported — the backup is what makes that safe. Don't assume this; confirm it
for each bundle, since the answer is specific to how that bundle was
carried forward.

### Step 1 — Read everything first; build the whole gestalt
Before writing a single new file, read the entire legacy bundle: every
loader/instruction file (however it was named — `CLAUDE.md`, `README.md`,
any `_bootstrap`/`_agent_instructions`-style file, anything under a
`charter/` folder), every playbook and prompt file, every tool script, and
the config. Understand in full what this agent actually does and with what
toolset before converting anything.

### Step 2 — Locate the agent's personal/instance data root
Legacy agents typically split reusable machinery from personal/instance
content, with the personal side living outside the agent's own folder. Find
where that actually is now — it may not be where the legacy docs claim (a
stale path is common after prior reorganizations, and a bounded search
across every connected drive sometimes misses a distinct-but-similar-named
mount, e.g. a dedicated app's own iCloud container vs. the generic iCloud
Documents sync). Confirm with the user rather than guess past a bounded
search; but don't let this block writing the charter and porting machinery,
which don't strictly depend on it.

**Step 2a — Read the data root's own README (and any other file in it) for
logic, not just content.** If you find navigational or operational logic
sitting in a data-root README ("which file is the master version," "where
does a finished artifact get saved"), it needs to be ported into `/src` (a
charter for structural pointers, a playbook for anything tied to a workflow
step) — a data-folder README is read on-demand by a human, not
systematically consulted each session, so logic left there is functionally
invisible at runtime.

**Step 2b — Quarantine, don't inherit, any state-tracking file you find.**
Legacy data roots often contain a living "current state" file (`STATE.md`,
`CHANGELOG.md`, `next_session.md`, or similar). Do not assume this content
is still accurate just because it's the only tracking mechanism you can
find — check it against the shared tickets.db and, wherever possible,
against the real thing it describes by direct inspection (a stale status
claim caught by actually looking at the files is far better than one
propagated forward). Migrate any still-open, user-confirmed-relevant items
into the agent's own board epic as tasks
(`tools/ticket_tools/ticket_write.py add-epic` / `add-task`), then move
the file itself into the data root's own `archive/legacy_state_files/` —
never leave it sitting at the data root's top level once a tickets-db epic
exists for that agent.

### Step 3 — Grep for personal-data markers before moving anything
Search the whole legacy bundle for the user's name, contact details, and
any other personal specifics before copying files into `/src`. This tells
you which files are clean and safe to move verbatim, and which need a
depersonalization pass first — cheaper to know upfront than after.

### Step 4 — Write the new identity charter
Create `agent_identities/<agent>.md` from `templates/identity_template.md`,
in the same shape as `chief_of_staff.md`. Two rules, non-negotiable:
nothing personal, dated, or state-like ever goes in this file (no user
name, no resolved/unresolved path narration, no "as of" notes); and no
procedure logic gets inlined here (describe *what* playbooks/tools exist,
not *how* they work).

### Step 5 — Separate the real machinery into tools, playbooks, and protocols
- **`tools/<agent>/`** — actual callable scripts, or anything closer to a
  single-purpose callable than a multi-step workflow (a fixed prompt, a
  linter, a scraper) — even a prompt file counts as a tool if it produces
  one kind of output.
- **`playbooks/<agent>/`** — step-by-step procedures a session follows end
  to end. `templates/playbook_template.md` has the expected shape.
- **`protocols/<agent>/`** — only if the legacy bundle has instructions for
  coordinating with an external party on a specific task (another AI
  service, another agent). `templates/protocol_template.md` defines this
  distinction precisely: does this describe a procedure one session runs,
  or a contract between two separate parties? That answers it.

### Step 6 — Depersonalize as you go
For any file flagged in Step 3: keep every procedural/structural rule (the
reusable value), and replace hardcoded personal specifics — names, contact
fields, specific named anecdotes, specific past employers, absolute paths
containing a username — with a pointer to wherever that content actually
lives in the agent's personal data root (Step 2), or with a generic
placeholder for content that's genuinely reusable once depersonalized (e.g.
a tutoring prompt addressed to "the student" instead of a name). This is
not lossy — a generic pointer survives instance changes better than a
hardcoded example ever could. Generic-looking design defaults (fonts,
colors, layout spacing) are a judgment call, not automatically personal
data — use discretion and say so in the closing report if one was kept.

### Step 7 — Delete originals as each piece is ported
Once a piece of the legacy bundle is fully translated into its new `/src`
home and verified (scripts compile/run, no personal markers remain in the
new copy), delete the original from the migration-staging location. Don't
batch this to the end — delete as you go, per Step 0's confirmed backup
situation. Leave alone anything not yet fully translated.

**A real, undeleted sub-project sitting in the staging folder is never a
valid end state.** Either it's truly disposable (archive it properly,
outside the project entirely) or it's real ongoing content (give it a
real home under `data/`) — but the staging folder itself must end up empty.
If something is found that's genuinely unrelated to the agent being
migrated (misfiled during some earlier reorg), don't silently relocate it —
flag the discovery and ask the user what should happen to it, unless the
disposition is truly obvious.

### Step 8 — Don't invent what isn't there
Only port and reformat what actually exists in the legacy bundle. If the
bundle implies a capability that doesn't actually exist as a script or a
documented procedure, say so plainly in the closing report rather than
writing a new one to fill the gap. A migration is a translation pass, not a
feature-build pass.

### Step 9 — Tickets-db onboarding
Give the migrated agent its own tagged epic in the shared tickets.db
(`epic.owner` set to the agent's slug), seeded with any real open items
carried over from Step 2b's quarantine pass.

### Step 10 — Close with a plain report, not a file
Report back in chat: what's fully ported, what's intentionally left behind
and why, what data stores were found and mapped (the hard rule above) but
not touched, and any judgment calls made along the way. This report is
disposable — durable lessons worth keeping past the conversation go to
memory, not to a new file under `/src` or `/data`.

## Tools Used
- `tools/ticket_tools/ticket_write.py` — epic/task/handoff creation during Step 9.

## Logging Requirements
Every quarantined state item and every judgment call gets recorded as a task
against the new agent's epic (or noted on a card via `add-issue-log --task-id
<slug> --note "..."`) — never a new markdown tracking file.

## Failure Modes
- Step 2's bounded search comes up empty → confirm with the user before
  concluding the data doesn't exist; never fabricate replacement content to
  fill the gap.
- An in-scope reference (a file the legacy bundle points at) resolves to
  nowhere real → surface it and ask, don't assume a different file was
  meant.

## Human Audit Notes
If a future migration surfaces the same category of mistake this playbook
warns about (a bounded search missing a distinct-but-similarly-named mount,
a stale state file treated as current), that's a signal this playbook's
guidance needs sharpening, not that the individual migration was uniquely
careless.
