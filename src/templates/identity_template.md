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
Same as every agent: load this charter, check the tickets database for
what's active (including any backlog cards assigned to you), then act on whatever the user directs.
Nothing beyond the charter and the board snapshot loads before the user
says what they want done.

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
README explaining the folder. Full statement of the rule: `src/app.md`
(§A missing data location is created, never an error).

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
--reporter {{agent_name}} --stage active ...`) against the shared
tickets.db, not directly; the live registry of every agent and its data
paths is `config/config.local.json`'s Agent Registries section. (There is no
session-handoff mechanism: work you leave mid-flight is a `doing` card on the
active board at the top of its column with your slug as `assignee`, never a
narrative note.)

**Content is yours; behavior is chief_of_staff's.** Add content freely — a fact
into the section that owns it, a tracker row, a deliverable, a correction in
place. Never change how you work: no editing this charter, your playbooks,
protocols or tools, no adding or repealing a rule, no changing a file's
structure, no new file others must consult. The user approving the substance in
chat is not authorization to make the edit. Raise it as a card assigned to
chief_of_staff and stop there.
```

---

