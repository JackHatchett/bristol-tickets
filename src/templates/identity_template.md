# {{AGENT_NAME}}.md — Agent Charter Template

> Skeleton for `src/agent_identities/<agent>.md`, in the same shape
> `chief_of_staff.md`, `career_coach.md`, and `writers_room.md` all use.

---

```markdown
# {{agent_name}}.md — Agent Charter

**Single source of truth for identity and operating mandate.**
**Loaded at every session start via `src/app.md`, same as `chief_of_staff.md`.**

---

## 1. Identity & System Role

{{One or two short paragraphs: what this agent is for, in domain-neutral
language. Write it for a stranger — someone with a different job, different
clients, a different notebook and a different software stack. Anything the
agent needs installed (a third-party app, an account, credentials) is named
here as a prerequisite, and if the agent works without it, say so. If it runs
on a machinery/personal-data split like career_coach does, say so and name the
two roots in general terms — never name the actual personal-data path here.}}

{{Then write the same thing in one line and put it in
`config/config.local.json` at `agents.<agent>.description` — that line is what
the first-run agent picker and `docs/agents.md` show.}}

---

## 2. Operating Mandate & Execution

### 2.1 Session Start
Same as every agent — `src/app.md` Phases 2 and 3. Nothing beyond this charter
and the board snapshot loads before the user says what they want done.

### 2.2 Playbooks
{{One line each, pointing at `playbooks/{{agent_name}}/<file>.md` — name and
one-sentence purpose only. No procedure logic here.}}

### 2.3 Tools
{{One line each, pointing at `tools/{{agent_name}}/<file>` — name and
one-sentence purpose only. If a tool is generic enough for other agents to
use, it belongs in a shared folder under `tools/` instead (e.g.
`tools/wiki_tools/`, `tools/writing_tools/`), not duplicated here — say so
and point at the shared location.}}

### 2.4 Protocols (only if this agent coordinates with an external party)
{{One line each, pointing at `protocols/{{agent_name}}/<file>.md` — omit this
section entirely if the agent has no external-coordination contracts.}}

### 2.5 Data Locations
The paths in `agents.{{agent_name}}.key_data_paths` are declared, not
guaranteed to exist. Resolve them through
`tools/config_tools/data_paths.py`: `ensure_dir()` right before a write,
`read_dir()` for a read that returns nothing when the folder is not there yet.
Create the container and stop — never a placeholder file, a sample record, or a
README explaining the folder. Full statement of the rule:
`src/tools/config_tools/README.md` (§A missing data location is created, never
an error).

### 2.6 Bright-Line Guardrails Only
{{The hard rules that halt execution — never approval-seeking on routine
work, only real bright lines specific to this agent's domain.}}

---

## 3. Boundaries & Coordination

Owns `playbooks/{{agent_name}}/`, `tools/{{agent_name}}/`
{{, `protocols/{{agent_name}}/` if applicable}}, and its own tagged epic(s)
in the shared tickets database (`data/*/tickets/tickets.db`, scoped via
`epic.owner = '{{agent_name}}'`) — never a private per-agent database. Never
store personal/instance content inside the tracked machinery. Coordinate
with another agent by adding a card assigned to them
(`tools/ticket_tools/ticket_write.py add-task --assignee <agent>
--reporter {{agent_name}} ...`) against the shared
tickets.db, not directly; the live registry of every agent and its data
paths is `config/config.local.json`'s Agent Registries section. There is no
session-handoff mechanism — `src/tools/ticket_tools/README.md` §Board
conventions.

**Content is yours; behavior is chief_of_staff's** — `src/app.md`, the section
of that name. Raise any change to how you work as a card assigned to
chief_of_staff and stop there.
```

---

## The governing-doc style contract

Every governing document under `/src` — a charter written from this template,
`src/app.md`, playbooks, protocols, tool READMEs, the other templates — is
written to be executed by a model, not to convince a reader. The reader already
does what it says; what it needs is the rule, its boundary, and which rule wins.
Seven rules:

- **State a rule once, in the one file that owns it.** Every other file
  references that file and adds nothing of its own. Two statements of a rule are
  two rules the moment either one is edited, and the copy is the one that goes
  stale.
- **The resident core owns whatever must be resident.** `src/app.md` loads at
  every session start and nothing else does, so a rule an agent must hold
  without opening a file is stated there and the reference documents point back
  to it. A rule that only bites once you are already reading the mechanism is
  owned by the mechanism's own file.
- **One rule per bullet, imperative mood.** Never two rules sharing a bullet,
  and never a rule buried mid-paragraph where it reads as commentary. The
  bullet's first clause is the rule; whatever follows is its boundary.
- **Keep a negative where it names a plausible failure mode; cut it where it is
  the logical complement of the positive.** "Never make the user the transport"
  earns its line because an agent will otherwise reach for it. "Do not leave the
  field blank" after "fill in the field" earns nothing.
- **Keep rationale only where the rule under-determines a case the agent will
  meet.** Explain a rule when knowing why changes what the agent does at an edge
  it will actually reach. Otherwise state the rule and stop — a rule that holds
  everywhere needs no defence.
- **State precedence wherever two rules can conflict.** Name the winner at the
  point of conflict, in both files if the conflict spans two. Saying which rule
  wins is a boundary, not a claim that one document outranks another; the latter
  is banned by `src/app.md` §What a file may say.
- **Cut anything that is neither a rule nor a fact.** No preamble justifying the
  file's existence, no history of how a rule came to be, no reassurance, no
  restatement of the previous paragraph in different words.
