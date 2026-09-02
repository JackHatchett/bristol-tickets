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

## agents.py

```
python3 agents.py list [--json]
python3 agents.py read <slug> [--json]
python3 agents.py skeleton <slug>
python3 agents.py edit <slug> [--identity …] [--description "…"]
                              [--charter-file <path>]
                              [--data-path …]... [--context-file …]...
                              [--notebook-read yes|no] [--write-zone …]...
                              [--archive-moves yes|no] [--env NAME=VALUE]...
                              [--extra-file <json>]
```

Reads the agents that exist and changes what one says. `create_agent.py` writes
an agent that is not there yet; this one requires that it is, which is why they
are two commands rather than one with a flag.

- **One call writes both files.** The charter and the config entry cannot land
  separately, and every change is checked before the first write, so a refused
  edit leaves both exactly as they were.
- **The charter is read and written whole.** Nothing here parses it into
  fields. A charter is prose a person wrote, and a tool that recognized only
  the shapes it generates itself would refuse to edit the ones that matter most.
  `--charter-file` supplies the document; `skeleton` prints the starting one,
  taken from `src/templates/identity_template.md` §The skeleton, which owns it.
- **Every key an entry holds travels through an edit.** The ones with options of
  their own are written from those options; every other key is carried
  untouched, and `--extra-file` is how they are replaced as a set. A key this
  build predates is never dropped.
- **A repeatable option replaces its whole list.** Its `--no-…` partner empties
  one.
- **`--identity` moves the charter**, writing it at the new path and removing
  the old one, and refuses a path outside the repository or one already taken.
- **Skills are `skill_tools/skills.py`'s.** Attaching and detaching go through
  its own commands, here as everywhere.
- **Notebook access is written one part at a time** — `--notebook-read`,
  `--write-zone` and `--archive-moves` — because `config`'s markdown_notebook
  §ZONES grants them separately: the notebook is read whole or not at all, and
  writing is granted a zone at a time. `create_agent.py` takes the same three,
  and its `--notebook` shorthand sets all three at once.

Bristol Tickets' Agents tab is a front end to these two commands and to
`skills.py`, and writes nothing itself —
`src/tools/bristol/ui/agents_tab.py`.
