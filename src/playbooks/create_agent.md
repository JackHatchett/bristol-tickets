# create_agent — Playbook

Bootstrap a new agent from nothing: charter, scaffolding, board epic,
registration. For converting an existing pre-framework bundle, use
`src/playbooks/migrate_legacy_agent.md` instead.

## Preconditions

- **The user has confirmed the agent's canonical name** in snake_case.
- **The user has said in general terms what the agent is for**, and whether it
  needs a personal-data root under `data/*/`.
- **The shared board exists** at `data/*/tickets/tickets.db`. It is provisioned
  once per instance by `tools/ticket_tools/create_tickets.py --instance
  <instance_slug>`, never per agent.

## Procedure

1. **Check the name is unique against the `agents` block of
   `config/config.local.json`.** That block is the live list of every agent;
   there is no separate registry file. On a collision, ask the user to choose
   another name or confirm they mean to extend the existing agent.

2. **Write `src/agent_identities/<agent>.md` from
   `src/templates/identity_template.md`.** Write it for a stranger: no
   assumption about the user's job, clients, courses, notebook layout or
   software stack, and every third-party prerequisite named as one. What may go
   in it, and what belongs in the config entry or a skill instead, is that
   template's §What an agent is made of.

3. **Scaffold only what has real content to hold.** Most new agents start with
   none of it and add as needs appear.
   - `src/skills/<skill-name>/` — once a real procedure exists. The format is
     `src/tools/skill_tools/README.md`, and turning an existing procedure file
     into one is `src/playbooks/skill_conversion.md`.
   - `src/tools/<agent>/` — for genuinely agent-specific callables, which a
     skill names the command line for. A tool useful to more than one agent goes
     in a shared folder nested under `src/tools/` (`tools/wiki_tools/`,
     `tools/writing_tools/`, `tools/ticket_tools/`), never a new top-level
     `src/` sibling.

4. **Give the agent a board epic.**

   ```
   python3 src/tools/ticket_tools/ticket_write.py add-epic \
     --name "<agent> — initial setup" --owner <agent>
   ```

   Add `--description` and `--next-action` as appropriate. The epic is the
   agent's tagged slice of the one shared board; there is no per-agent database.

5. **Create a data root only if the agent holds personal content.** Name the
   folder after the content rather than the agent (`data/*/career/`,
   `data/*/clients/`), and register the path under the agent's
   `key_data_paths`. chief_of_staff has none.

6. **Register the agent under `agents` in `config/config.local.json`**:
   `identity` (repo-relative path to the charter), `description` (the line the
   first-run wizard and `docs/agents.md` show), `key_context_files`,
   `key_data_paths`, `env` if its tools need variables, `notebook_access`, and
   `notes`. `config/config.example.json` is the shape to copy. This is the whole
   registration step.

7. **Stop there.** The agent's first session loads its charter and its board
   epic and takes direction from the user; no onboarding tasks are seeded beyond
   the epic.

**Provider-specific behavior belongs to the new agent's own protocol or tool
files**, or to a connected MCP where one exists — never to this playbook and
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
