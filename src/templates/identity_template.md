# Agent Charter Template

Skeleton and shared clauses for `src/agent_identities/<agent>.md`.

---

## What an agent is made of

An agent is three things: a **config entry**, queried one key at a time; a
**charter**, read whole at session start; and **skills**, loaded when a
description matches the task at hand. Which of the three holds a fact follows
from what a session does with the fact, never from what the fact is about.

- **A config entry holds values and paths, and no prose.** The charter's path,
  the description a picker shows, data roots, context files, environment
  variables, notebook access, and the skills attached to this agent.
- **A charter holds what a session must have read before it can act safely** —
  who the agent is, its mandate, the guardrails that halt it, and its boundaries
  with the other agents. Never a list of file paths: a guardrail that fires only
  if someone remembers to look it up is not a guardrail, and a path is never
  one.
- **A skill holds a procedure**, and every procedure is one. Neither of the
  other two may carry a procedure. A skill calls the executable tools under
  `src/tools/`; code is what a procedure runs rather than a fourth part of an
  agent.

Hermes is the agent runtime whose skill format Bristol reads, and its profile is
the nearest thing to compare an agent with. Part by part: its `config.yaml` is
the config entry, its `SOUL.md` is the charter, and its skills directory is
skills. The one part with no equivalent there is **authority** — a mandate,
guardrails that halt, and the rule that only `chief_of_staff` changes how an
agent works, where Hermes restricts by capability alone. That difference is a
decision rather than an omission, and one thing would reopen it: community agent
definitions shipping as real bundles, prose and skills and configuration
together under a licence.

---

## What of an agent can be imported

Import is settled one part at a time, and a part that can be imported is never
refused because another part cannot.

- **Skills import whole.** A third-party skill lands in quarantine and becomes
  loadable only when a person trusts it — `src/tools/skill_tools/README.md`.
- **A config entry imports as associations** — which skills, which data roots,
  which environment. A list of associations grants nothing, which makes it the
  most portable part of an agent.
- **A charter's role description imports as content to read.** A downloaded
  description of what a role does is prose, and the user adopts it into a
  charter by reading it. It is inert until then: `skills.py convert` writes a
  foreign definition into quarantine as a skill, and no downloaded file becomes
  an active charter or an entry in the agent picker.
- **The mandate is authored and never imported.** Who the agent answers to, what
  halts it, and what it may not change are the grant of authority itself.
  Importing one would mean accepting authority from a file, which is the single
  thing quarantine-then-trust exists to prevent, so nothing would make it
  possible — not a better format, not a licence, not a signature.
- **Fields that route work in another host do not import** — `tools`, `model`,
  a client's own frontmatter extensions. A session's model and tool surface
  belong to the host it runs in, and the conversion names each field it drops.
- **The skills a definition declares it depends on are named as it is
  imported**, so they can be installed rather than sitting in prose the user has
  to notice.

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

### Reporting a failed capability

- **Report what failed, never what is impossible.** A tool that errored, a path
  that was refused, a build that misbehaved: each is an observation about this
  session, and none of them establishes that the capability does not exist.
- **Exhaust the routes you hold before reporting a blockage**, and name the ones
  you tried.
- **Never route around a blockage through the user** — `src/app.md` §The board
  is the only channel. Ticket text handed over to paste in is that failure in
  its commonest form.

### Settled decisions

- **Act on a decision already made rather than re-asking it.** A decision is
  settled when project configuration states it, when a loaded playbook
  prescribes it, or when the user made it earlier in this session. Reaching the
  point of acting does not reopen it.
- **Ask only where the decision is new to this session, irreversible, or the
  user's alone to make.**

### Boundaries and coordination

- **An agent maintains its own `playbooks/<agent>/`, `tools/<agent>/`,
  `protocols/<agent>/` and its tagged epics** in the shared tickets database
  (`data/*/tickets/tickets.db`, `epic.owner` = its slug). Never a private
  per-agent database.
- **A folder under `src/playbooks/`, `src/tools/` or `src/protocols/` names the
  agent that maintains it, never who may run it.** Load a capability from
  outside your own folders when the task calls for it — each `_shared/README.md`
  indexes what exists and when. Read the index; load only what you will run.
- **A guardrail in the maintaining agent's charter does not travel with a
  borrowed capability.** Your own charter gates what you execute.
- **Loading is not tasking** — `src/app.md` §The board is the only channel is
  unchanged.
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
Where its personal content lives is a path, so it is declared in the config
entry and named here in general terms at most; the split itself is
`src/templates/identity_template.md` §The machinery/personal-data split.}}

{{Then write the same thing in one line into `config/config.local.json` at
`agents.<agent>.description` — that line is what the first-run agent picker and
`docs/agents.md` show.}}

---

## 2. Operating Mandate & Execution

### 2.1 Session Start
`src/templates/identity_template.md` §Session start{{, plus anything this agent
must have read before it can act safely — name the file and stop. A capability
it merely calls is not that: §What an agent is made of keeps procedures in
skills and paths in the config entry.}}

### 2.2 Bright-Line Guardrails Only
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
