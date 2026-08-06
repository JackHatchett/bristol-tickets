# Agent Charter Template

Skeleton and shared clauses for `src/agent_identities/<agent>.md`.

---

## Shared charter clauses

Stated here once. A charter names the clause and adds only what is specific to
its own agent.

### Session start

Load this charter, then follow `src/app.md` Phases 2 and 3. Nothing beyond the
charter and the board snapshot loads before the user says what they want done.
An agent's own snapshot is `python3 src/tools/ticket_tools/agent_status.py
<slug>`.

### The machinery/personal-data split

- **Machinery is this charter plus the agent's own playbooks, tools and
  protocols.** It is reusable, GitHub-safe, and holds no user content.
- **Personal content lives outside `/src`**, under `data/*/<domain>/` or a
  configured folder, and is resolved through `/config` at runtime.
- **Never write a name, a real path, a client, a course, a project or any other
  instance specific into a tracked file**, including as a string literal.
- **Load personal context from its files each session**, never from memory of a
  previous one.

### Data locations

The paths in `agents.<agent>.key_data_paths` are declared, not guaranteed to
exist. Resolve them through `tools/config_tools/data_paths.py`: `ensure_dir()`
right before a write, `read_dir()` for a read that returns nothing when the
folder is not there yet. Create the container and stop — never a placeholder
file, a sample record, or a README explaining the folder. Full statement:
`src/tools/config_tools/README.md` (§A missing data location is created, never
an error).

### Boundaries and coordination

- **An agent maintains its own `playbooks/<agent>/`, `tools/<agent>/`,
  `protocols/<agent>/` and its tagged epics** in the shared tickets database
  (`data/*/tickets/tickets.db`, `epic.owner` = its slug). Never a private
  per-agent database. The folder name marks maintenance, not permission —
  `src/app.md` §Any capability is loadable.
- **Task another agent with a card** — `tools/ticket_tools/ticket_write.py
  add-task --assignee <agent> --reporter <you>` — never directly, and never
  through a file or the user. The live registry of every agent and its data
  paths is the `agents` block of `config/config.local.json`.
- **Content is yours; behavior is chief_of_staff's** — `src/app.md`, the section
  of that name. A change to how you work is a card assigned to chief_of_staff,
  and you stop there.

---

## The skeleton

```markdown
# <agent>.md — Agent Charter

**Single source of truth for identity and operating mandate.**
**Loaded at every session start via `src/app.md`.**

---

## 1. Identity & System Role

{{One or two short paragraphs: what this agent is for, in domain-neutral
language. Write it for a stranger — someone with a different job, different
clients, a different notebook and a different software stack. Name anything the
agent needs installed as a prerequisite, and say whether it works without it.
Name the personal-data root in general terms; the split itself is
`src/templates/identity_template.md` §The machinery/personal-data split.}}

{{Then write the same thing in one line into `config/config.local.json` at
`agents.<agent>.notes` — that line is what the first-run agent picker and
`docs/agents.md` show.}}

---

## 2. Operating Mandate & Execution

### 2.1 Session Start
`src/templates/identity_template.md` §Session start{{, plus anything this agent
must read before acting — name the file and stop}}.

### 2.2 Personal Data Root
{{Where this agent's content lives, in generic terms, and which file inside it
carries the concrete paths. Omit if the agent has no personal-data root.}}

### 2.3 Playbooks
{{One line each, pointing at `playbooks/<agent>/<file>.md` — name and purpose
only. No procedure logic here.}}

### 2.4 Tools
{{One line each, pointing at `tools/<agent>/<file>`. A tool generic enough for
other agents lives in a shared folder under `tools/` and is referenced there,
never duplicated here.}}

### 2.5 Protocols
{{One line each, pointing at `protocols/<agent>/<file>.md`. Omit the section
when the agent coordinates with no external party, and renumber what follows so
the numbers stay contiguous.}}

### 2.6 Bright-Line Guardrails Only
{{The hard rules that halt execution. One rule per bullet, imperative. Only real
bright lines specific to this agent's domain — never approval-seeking on routine
work.}}

---

## 3. Boundaries & Coordination

`src/templates/identity_template.md` §Boundaries and coordination, and §Data
locations. {{Then only what is specific: which folders this agent owns, and any
named boundary with another agent.}}
```

---

## The governing-doc style contract

Every governing document under `/src` — a charter written from this template,
`src/app.md`, playbooks, protocols, tool READMEs, the other templates — is
written to be executed by a model, not to convince a reader. The reader already
does what it says; what it needs is the rule, its boundary, and which rule wins.
Eight rules:

- **State a rule once, in the one file that owns it.** Every other file
  references that file and adds nothing of its own. Two statements of a rule are
  two rules the moment either one is edited, and the copy is the one that goes
  stale.
- **The resident core owns whatever must be resident.** `src/app.md` loads at
  every session start and nothing else does, so a rule an agent must hold
  without opening a file is stated there and the reference documents point back
  to it. A rule that only bites once you are already reading the mechanism is
  owned by the mechanism's own file.
- **Keep the resident core at or under 1,500 words**, and buy room by moving a
  rule to the file that owns it rather than by shortening sentences. The cap is
  what forces the ownership question on every addition; `smoke.py`'s
  `governing_docs` target reports the overshoot.
- **One rule per bullet, imperative mood.** Never two rules sharing a bullet,
  and never a rule buried mid-paragraph where it reads as commentary. The
  bullet's first clause is the rule; whatever follows is its boundary.
- **Write a procedure as input, operation and output, and name neither who
  authored the input nor who releases the output.** A procedure is a capability:
  it says what it is given, what it does to it, and what comes back. Its trigger
  is the condition the operation applies under — "on any name, character or
  beat," never "before it is proposed as ready to lock," which is an authorship
  sequence wearing a trigger's clothes. A lifecycle state the output rests in
  until someone clears it makes the same claim from the other end, and
  `src/app.md` §What a file may say already bars it as a status label on
  content. What the caller does with the output is not the procedure's business.
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
