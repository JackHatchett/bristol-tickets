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
   software stack, and every third-party prerequisite named as one.

3. **Scaffold only what has real content to hold.** Most new agents start with
   none of the three and add them as needs appear.
   - `src/playbooks/<agent>/` — once a real step-by-step procedure exists, from
     `src/templates/playbook_template.md`.
   - `src/tools/<agent>/` — for genuinely agent-specific callables. A tool
     useful to more than one agent goes in a shared folder nested under
     `src/tools/` (`tools/wiki_tools/`, `tools/writing_tools/`,
     `tools/ticket_tools/`), never a new top-level `src/` sibling.
   - `src/protocols/<agent>/` — only if the agent coordinates with an external
     party on a recurring contract, from `src/templates/protocol_template.md`.
     That template draws the line: a protocol is a contract between two parties,
     a playbook is a procedure one session runs.

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

- **The charter starts inlining procedure logic** → move that content into its
  own playbook, tool or protocol file and reduce the charter section to a
  one-line pointer.
- **A capability is unclear as tool, playbook or protocol** →
  `src/templates/protocol_template.md` draws the line, and
  `src/playbooks/migrate_legacy_agent.md` Step 5 applies the same split.

## Audit

**Whether the `agents` block has gone stale**, and **whether each agent's board
epic still reflects real work.**
