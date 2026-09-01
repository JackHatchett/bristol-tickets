---
name: create-agent
description: Builds a new agent from nothing: its charter, its folders, its board epic and its registration in config. Use when a new job in the fleet has been decided and has to be set up.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/agent_tools/create_agent.py src/tools/ticket_tools/create_tickets.py
---
# create-agent

Bootstrap a new agent from nothing: charter, scaffolding, board epic,
registration. For converting an existing pre-framework bundle, use
`src/skills/migrate-legacy-agent/SKILL.md` instead.

## Preconditions

- **The work meets a separation test** —
  `src/templates/identity_template.md` §When one job is two agents. Work that
  meets none of them is a skill attached to an agent that already exists.
- **The user has confirmed the agent's canonical name** in snake_case.
- **The user has said in general terms what the agent is for**, and whether it
  needs a personal-data root under `data/*/`.
- **The shared board exists** at `data/*/tickets/tickets.db`. It is provisioned
  once per instance by `tools/ticket_tools/create_tickets.py --instance
  <instance_slug>`, never per agent.

## Procedure

1. **Settle the mandate and the guardrails with the user.** Those are the two
   things nobody can supply for them: what the agent answers to and what halts
   it. Everything else about the agent is a value, and the tool takes it as an
   argument.

2. **Run `src/tools/agent_tools/create_agent.py`**, which writes the charter,
   the config entry, the skill attachments and the board epic in one go and
   refuses a name already in use. Its arguments and what each writes are
   `src/tools/agent_tools/README.md`.

3. **Scaffold only what has real content to hold.** Most new agents start with
   none of it and add as needs appear.
   - `src/skills/<skill-name>/` — once a real procedure exists. The format is
     `src/tools/skill_tools/README.md`, and turning an existing procedure file
     into one is `src/skills/skill-conversion/SKILL.md`.
   - `src/tools/<agent>/` — for genuinely agent-specific callables, which a
     skill names the command line for. A tool useful to more than one agent goes
     in a shared folder nested under `src/tools/` (`tools/wiki_tools/`,
     `tools/writing_tools/`, `tools/ticket_tools/`), never a new top-level
     `src/` sibling.

4. **Stop there.** The agent's first session loads its charter and its board
   epic and takes direction from the user; no onboarding tasks are seeded beyond
   the epic.

**Provider-specific behavior belongs to the new agent's own protocol or tool
files**, or to a connected MCP where one exists — never to this skill and
never to a shared config file.

**Record the creation on the new agent's epic**: what was created, what was
decided, and any deviation from these steps.

## Failure modes

- **The charter starts inlining procedure logic** → move it into a skill, and
  leave nothing in its place; a pointer is a path, and a charter carries none.
- **A capability is unclear as a tool or a skill** → the skill is the procedure
  and the tool is the code it calls.

## Audit

**Whether the `agents` block has gone stale**, and **whether each agent's board
epic still reflects real work.**
