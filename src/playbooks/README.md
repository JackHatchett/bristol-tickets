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

## Folder structure

A folder here names the agent that maintains its playbooks, never who may run
them. Any agent loads any playbook on demand: `src/app.md` §Any capability is
loadable.

`_shared/` holds the procedures that serve more than one agent, indexed one line
each in its own README.

Top-level playbooks are chief_of_staff's:

- `create_agent.md` — bootstrap a new agent from nothing.
- `migrate_legacy_agent.md` — convert a pre-framework agent bundle.
- `storage_audit.md` — the recurring storage cleanup inventory.

Each other folder holds one agent's own playbooks, and that agent's charter
names them:

- `career_coach/` — cover_letter, interview_prep, jd_evaluation,
  resume_tailoring, session_closure
- `client_services/` — operator_tasks, project_intake
- `game_designer/` — design_proposals, project_context,
  socratic_design_coaching
- `librarian/` — add_book, data_safety
- `teaching_assistant/` — content_generation, html_render, lesson_pipeline,
  navigator
- `writers_room/` — crew_dispatch, project_context, story_proposals,
  voice_distillation

## Using this folder

- **Load a playbook only when the task matches its purpose**, never at session
  start and never as a standing rule.
- **Call a script in `src/tools/` rather than restating what it does.** Tools
  are the execution layer; a playbook names the command line.
- **Editing a playbook is chief_of_staff's** — `src/app.md` §Content is yours;
  behavior is chief_of_staff's. A change another agent wants is a card assigned
  to chief_of_staff.
- **The live registry of every agent and its data paths is the `agents` block
  of `config/config.local.json`.** There is no routing file: an agent's own
  charter names where its durable content lives.
