# Agent Tools

Creating an agent, and moving one between installations. The three parts an agent is made of are
`src/templates/identity_template.md` §What an agent is made of; this folder
holds the program that writes them. Style contract for this file: that
template's §The governing-doc style contract.

## Invariants

- **The mandate and the guardrails are supplied, never generated.** Everything
  else about a new agent follows from them or from a value the caller names, and
  a file that could grant itself authority is what
  `src/templates/identity_template.md` §What of an agent can be imported
  refuses.
- **Nothing is written until everything checks.** A slug already in use, a
  charter already on disk, or a skill name that is not loadable stops the run
  before the first write, so a mistyped argument never leaves half an agent.
- **A part is created through the tool that owns it.** Skills attach through
  `skill_tools/skills.py`, the board epic goes through
  `ticket_tools/ticket_write.py`, and the config entry goes through
  `config_tools/write_config.py`, so an agent created here and one created by
  hand are the same object.
- **No personal data.** Every location is a declared path resolved through
  `/config`.

## create_agent.py

```
python3 create_agent.py <slug> \
    --description "the one line a picker shows" \
    --role "what this agent is for, written for a stranger" \
    --guardrail "Never ..." [--guardrail ...] \
    [--data-path data/<instance>/<domain>]... \
    [--context-file <path>]... \
    [--skill <name>]... \
    [--owns tools/<slug>/]... \
    [--notebook read|write|none] \
    [--no-epic]
```

What it writes:

- **`src/agent_identities/<slug>.md`**, in the shape the template's skeleton
  gives: identity, the session-start reference, the guardrails as one bullet
  each, and the boundaries reference. It carries no list of files, because a
  charter names none.
- **`agents.<slug>` in config**, with the fields every agent has. `--notebook`
  is `none` by default, which is `read` and `write` both false.
- **An attachment per `--skill`**, through `skills.py attach`.
- **A board epic owned by the new agent**, which is what gives it a presence on
  the shared board. `--no-epic` skips it where one already exists.

A declared data root that does not exist yet is reported as a normal first
state; the folder is created at the moment of the first write, which is
`src/tools/config_tools/README.md` §A missing data location is created, never an
error.

Nothing else needs editing afterwards. The agent picker reads the `agents` block
directly, so the new agent is selectable at once, and a session started as it
loads the charter and the board epic and takes direction from the user.

## The agent file

`<slug>.agent.json` is the whole of an agent that can travel. One JSON document,
four keys:

| Key | Holds |
| --- | --- |
| `bristol_agent` | The format number. A build reads the one it knows and refuses the rest. |
| `slug` | The agent's name. |
| `charter` | The charter, in full, as Markdown. |
| `entry` | The config entry, minus `identity` and `skills`, with every local value taken out. |
| `skills` | One record per attached skill: its `name`, and `source` — `native`, or `address` with the web address of the exact commit and folder it was installed from. |

- **A value belonging to the exporter never crosses.** An absolute path and an
  environment variable's value become `<supply>`, which the importer fills; the
  instance slug becomes `<instance>` and the notebook's folder name becomes
  `<notebook>`, which the importer resolves to its own.
- **No skill's bytes travel with an agent** — only its address, and the importer
  fetches from the source. What a skill records about itself, and what happens to
  a borrowed one on the way out, is `src/tools/skill_tools/README.md` §What a
  skill records about itself.
- **The specification covers the skills and nothing else.** A skill is named by
  the address `skills.py install` already takes, so a skill in an agent file and
  a skill anyone installs by hand are the same object. The charter and the
  config entry have no equivalent in the specification, and are the whole of
  what this format invents.
- **`<supply>` survives into config where the importer has not filled it.** An
  unset value is visible and inert rather than silently resolved, and the import
  prints the exact `write_config.py` line for each one.

## export_agent.py

```
python3 export_agent.py <slug> [--out PATH]
```

Writes `<slug>.agent.json`. A skill installed before provenance records existed
carries no address, so it is recorded as unaddressed and the output names it:
the importer is told the capability is missing rather than handed a fetch that
cannot work.

## import_agent.py

```
python3 import_agent.py <file.agent.json>
python3 import_agent.py <file.agent.json> --accept
```

Two runs, because a file that arrives carrying a mandate is a stranger's
statement of what an agent may do — `src/templates/identity_template.md` §What
of an agent can be imported, and `src/skills/importing-an-agent/SKILL.md` for
the judgment.

- **The first run writes nothing.** It prints the agent's mandate and its
  guardrails, and fetches every addressed skill through `skills.py install`, so
  each lands in the same quarantine as any other and none is trusted.
- **The file is the only place a pending agent lives.** Nothing is staged, so
  there is no half-imported agent to clean up and nothing to keep in step.
- **A skill that cannot be fetched does not stop the import.** It is named, the
  agent still arrives, and the missing capability stays unattached — `attach`
  refuses a name that is not loadable, which is what keeps a quarantined skill
  out of an agent's entry.
- **`--accept` writes the charter, the config entry and the board epic**, by the
  same calls `create_agent.py` makes, so an imported agent and one created here
  are the same object.
