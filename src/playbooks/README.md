# Playbooks

A playbook is a repeatable, provider-agnostic procedure a session loads when a
task matches its purpose. Style contract for every file here:
`src/templates/identity_template.md` §The governing-doc style contract. Shape:
`src/templates/playbook_template.md`.

## What belongs here

- **A procedure**: an ordered workflow a session runs end to end.
- **Never a rule, a safety gate or a policy** — those are the agent's charter.
- **Never user-specific content or a storage-domain definition** — those live
  under `data/*/` and resolve through `/config`.
- **Never provider-specific behavior.** A procedure needing Gmail, Outlook or
  another named service calls that provider's connected MCP live.

## Where playbooks sit

Below `src/agent_identities/` (authority, mandate, guardrails) and
`src/protocols/` (coordination contracts with an external party). Above
`src/tools/` (the scripts a procedure calls) and the shared board
(`data/*/tickets/tickets.db`, written through `tools/ticket_tools/`).

A procedure carried in the Agent Skills format lives under `src/skills/` as a
folder holding `SKILL.md`, and its own `description` is its index — there is no
entry for it here. The format and the two roots are
`src/tools/skill_tools/README.md`; converting a file into one is
`src/playbooks/skill_conversion.md`.

## Folder structure

A folder here names the agent that maintains its playbooks, never who may run
them. Any agent loads any playbook on demand:
`src/templates/identity_template.md` §Boundaries and coordination.

`_shared/` owns the procedures that serve more than one agent; each is a skill
folder under `src/skills/`, and its own README states what belongs there.

Top-level playbooks are chief_of_staff's:

- `create_agent.md` — bootstrap a new agent from nothing.
- `fresh_clone_rehearsal.md` — prove a stranger can install Bristol, by
  download and by clone, before anything is pushed to a public remote.
- `migrate_legacy_agent.md` — convert a pre-framework agent bundle.
- `skill_conversion.md` — convert a playbook or a protocol into a skill
  folder under the Agent Skills specification.
- `storage_audit.md` — the recurring storage cleanup inventory.

Each other folder holds one agent's own playbooks, and this list is where they
are named:

- `career_coach/` — base_resume_update, cover_letter, interview_prep,
  jd_evaluation, resume_tailoring, session_closure
- `client_services/` — operator_tasks, project_intake
- `game_designer/` — design_proposals, project_context,
  socratic_design_coaching
- `librarian/` — add_book, data_safety
- `teaching_assistant/` — content_generation, html_render, lesson_pipeline,
  navigator
- `writers_room/` — manuscript_review, project_context, prose_drafting,
  story_proposals, voice_distillation

## Using this folder

- **Load a playbook only when the task matches its purpose**, never at session
  start and never as a standing rule.
- **Call a script in `src/tools/` rather than restating what it does.** Tools
  are the execution layer; a playbook names the command line.
- **Editing a playbook is chief_of_staff's** — `src/app.md` §Content is yours;
  behavior is chief_of_staff's. A change another agent wants is a card assigned
  to chief_of_staff.
- **The live registry of every agent and its data paths is the `agents` block
  of `config/config.local.json`.** There is no routing file, and a charter names
  no path — `src/templates/identity_template.md` §What an agent is made of.
