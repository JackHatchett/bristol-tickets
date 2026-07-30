# create_agent — Playbook

## Purpose
Bootstrap a brand-new agent from nothing: identity charter, playbooks/tools/
protocols scaffolding, roadmap epic, etc.

Every agent's machinery lives inside this repo, under
`src/`; every agent's personal/instance data (if any) lives under
`data/*/` (the `*` resolves to the instance's own data-root slug via
`config/config.local.json`); all agents share one roadmap database, scoped by
`epic.owner`.

## Preconditions
- The user has confirmed the agent's canonical name (snake_case).
- The user has confirmed, in general terms, what this agent is for and
  whether it needs its own personal/instance data root under `data/*/`.
- The shared roadmap database already exists at
  `data/*/roadmap/roadmap.db` (provisioned once, fleet-wide, via
  `tools/roadmap_tools/create_roadmap.py --instance <instance_slug>` — not
  re-run per agent).

## Procedure

1. **Identify agent name.**
   Confirm the agent's canonical name (snake_case). Check uniqueness
   against `config/config.local.json`'s Agent Registries section — that
   section, not a separate registry file, is the live list of every agent.

2. **Generate the charter.**
   Create `src/agent_identities/<agent>.md` from
   `src/templates/identity_template.md`. Reference the template by
   filename — do not restate its structure here; see that template for the
   exact shape (identity, session start, playbooks/tools/protocols
   pointers, guardrails, boundaries).

3. **Scaffold playbooks/tools/protocols as needed.**
   - `src/playbooks/<agent>/` — only once there's a real step-by-step
     procedure to write, generated from `src/templates/playbook_template.md`.
   - `src/tools/<agent>/` — only for genuinely agent-specific callables. If
     a tool would be useful to more than one agent, it belongs in a shared
     folder nested under `tools/` instead (e.g. `tools/wiki_tools/`,
     `tools/writing_tools/`, `tools/roadmap_tools/`), never a new top-level
     `src/` sibling.
   - `src/protocols/<agent>/` — only if this agent needs to coordinate with
     an external party (another AI service, another agent, the user, on a
     specific recurring contract). Generate from
     `src/templates/protocol_template.md`. Most new agents start with none
     of these three and add them as real needs appear — an empty scaffold
     with no content is not required up front.

4. **Give the agent a roadmap epic.**
   `python3 tools/roadmap_tools/roadmap_write.py add-epic --name "<agent> —
   initial setup" --owner <agent>` (plus `--description`/`--next-action` as
   appropriate). This is the agent's own tagged slice of the one shared
   roadmap.db — there is no separate per-agent database to create.

5. **Set up a data root only if the agent actually needs one.**
   If this agent will hold personal/instance content (records, a corpus,
   tracked application data), create `data/*/<domain>/` (naming follows
   the content, not the agent — see `career_coach`'s `data/*/career/` and
   `writers_room`'s Markdown-notebook-resident data as two different real patterns).
   Register the path in `config/config.local.json` and `config.local.json`.
   Not every agent needs this — chief_of_staff's registry entry has none.

6. **Register the agent.**
   Add the agent's entry to `config/config.local.json`'s Agent Registries
   section (identity document link, notebook access permissions, one-line
   notes) and the matching block in `config.local.json`'s `agents` key.
   This is the entire registration step — there is no separate
   `agent_registry.md` file.

7. **Bootstrap the next session.**
   The agent's next session is driven by its charter and its roadmap epic:
   load the charter, check the roadmap database for what's active under
   this agent's `owner` tag (including any backlog cards assigned to it), then act on user direction.
   No separate onboarding-task seeding step is needed beyond the epic
   created in step 4.

## Provider-specific logic
If this agent needs provider-specific behavior (a specific API, a specific
external service), that logic is handled live via a connected MCP where one
exists, or documented in the agent's own protocol/tool files — never in this
playbook, and never routed through a shared config file.

## Tools used
- `tools/roadmap_tools/roadmap_write.py` (add-epic, add-task, add-issue-log)
- `tools/roadmap_tools/create_roadmap.py` (fleet-level, one-time only — not
  part of the normal per-agent flow)

## Logging requirements
Log the creation via `roadmap_write.py add-task` (or note it in your own
one `add-issue-log` comment on the relevant card) against the
shared roadmap.db — items
created, decisions made, any deviations. Never a markdown state file.

## Failure modes
- **Name collision:** abort; ask the user to choose a different name or
  confirm they mean to extend an existing agent.
- **Charter drifts into inlining procedure logic:** stop, move that content
  into its own playbook/tool/protocol file, and reduce the charter section
  back to a one-line pointer.
- **Uncertainty about whether something is a tool, playbook, or protocol:**
  see `src/templates/protocol_template.md`'s distinction (a protocol is a
  coordination contract, not a procedure) and
  `src/playbooks/migrate_legacy_agent.md` Step 5 (the same split applies
  whether the agent is brand-new or being migrated from a legacy bundle).

## User audit notes
The user should periodically check:
- `config/config.local.json`'s Agent Registries section for staleness.
- Each agent's roadmap epic for content freshness.

## Session bootstrap (for AI)
- Role: Bootstrap a new agent from nothing (see `MIGRATION_GUIDE.md` instead
  for converting an existing legacy bundle).
- Source of truth: `src/playbooks/create_agent.md` (this repo).
- When to load: Only when the user asks to create a genuinely new agent.
- Allowed operations: File creation/edits under `src/agent_identities/`,
  `src/playbooks/<agent>/`, `src/tools/<agent>/`, `src/protocols/<agent>/`,
  `config/`, and `data/*/` as scoped above; roadmap-db writes via
  `roadmap_write.py`.
