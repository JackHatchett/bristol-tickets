# Agent Charter Template

Skeleton and shared clauses for `src/agent_identities/<agent>.md`.

---

## What an agent is made of

An agent is three things: a **config entry**, queried one key at a time; a
**charter**, read whole at session start; and **skills**, loaded when a
description matches the task at hand. Which of the three holds a fact follows
from what a session does with the fact, never from what the fact is about.

- **A config entry holds values and paths, and no prose.** Its fields are the
  table below.
- **A charter holds what a session must have read before it can act safely** —
  who the agent is, its mandate, the guardrails that halt it, and its boundaries
  with the other agents. Never a list of file paths: a guardrail that fires only
  if someone remembers to look it up is not a guardrail, and a path is never
  one.
- **A skill holds a procedure**, and every procedure is one. Neither of the
  other two may carry a procedure. A skill calls the executable tools under
  `src/tools/`; code is what a procedure runs rather than a fourth part of an
  agent.

**What each part costs is why the test is what it is.** A charter is Markdown a
session reads whole before it does anything, so it costs its entire length every
session, used or not. A config entry is JSON no session reads whole —
`read_config.py` takes one dotted key — so a key costs nothing until something
asks for it. A fact a session must have read before it can act safely is
therefore Markdown, because a lookup that might not happen is not a guardrail; a
fact it looks up when a task needs it is a config key, because paying for it
every session buys nothing.

**Every agent's config entry has these fields**, and an agent whose tools need a
value no other agent has declares its own key beside them:

| Field | Holds |
| --- | --- |
| `identity` | The charter's repository-relative path. Required. |
| `description` | The one line the agent picker and `docs/agents.md` show. |
| `key_context_files` | Files this agent reads on sight. |
| `key_data_paths` | The folders it reaches, each with the access it carries. |
| `env` | The environment variables its tools expect. |
| `notebook_access` | Which zones of the Markdown notebook it reaches. |
| `skills` | The skills attached to this agent, in the order they are matched. |
| `active_project` | Optional: the project a session opens on, where the agent holds more than one. |

A fact about an agent that is neither must-have-read nor one of these values is
a procedure, and a procedure is a skill.

**What the loader supplies, and what it cannot.** A session lists the installed
skills at start and matches a task against their descriptions, so a charter that
gives a procedure's path is a second copy of something the loader already
knows, and the loader is the source. Section by section:

| Charter section | Supplied by the loader |
| --- | --- |
| Identity & System Role | No. What an agent is for is not a procedure and nothing routes to it. |
| Session Start | Only in part. A file the agent must have read before it acts is listed here, because a match happens when a task arrives and this has to happen before one does. |
| Sources of truth and data rules | No. Where content lives is a config value; which of two copies is authoritative is the agent's own rule. |
| Bright-Line Guardrails Only | No. A guardrail reached by a match is not a guardrail. |
| Boundaries & Coordination | No. Which folders an agent owns, and where another agent's authority starts, is authority rather than capability. |
| Playbooks, Tools, Protocols | Yes, entirely, which is why no charter has such a section. |

**A procedure added to the system is reachable the moment it carries a
description**, and no charter is edited for it. That is the whole of what the
change buys, and it is why a charter that listed files had to stop.

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

## When one job is two agents

A role is added because the work divides, never because the title exists. Any
one of three tests makes a job separate from the agent carrying it:

- **A different mandate** — the new job answers for a different thing, the way
  building what a card decided differs from deciding it.
- **A different guardrail** — a rule that must halt the new job would have to be
  written into the existing charter as an exception to it.
- **Work that must not review itself** — one agent holding both the authorship
  and the judgement of the same output.

**Work failing all three tests is a capability rather than an agent**, and it
reaches the fleet as a skill an existing agent attaches.

**A separate job becomes its own agent, never a section added to an existing
charter.** One agent identity runs per session — `src/app.md` — and that is kept
rather than relaxed: a charter loads whole and resident, so two of them in one
session are two mandates and two guardrail sets with nothing saying which wins.
Adding roles around the rule is how it goes without ever being repealed.

**`chief_of_staff` is one job carrying one more.** Architecture, board
governance, system maintenance and authority over fleet behaviour pass no test
between them: one mandate whose subject is the system itself, one guardrail set,
and an authority a second agent cannot hold without two agents editing the same
governing documents. The one it also carries is a separate job —
**execution**, whose mandate is to build to a decision rather than to make one.
**Review** is `qa_engineer`'s, because what is written here must not be judged
by whoever wrote it. Every other agent in the fleet is one job by these tests.

**The cost of switching agents decides none of this.** A switch is one config
write — `active_agent`, from Bristol Tickets' Settings picker or
`write_config.py` — and a new session, and what it loses is the conversation
rather than the state: the board carries everything a session recorded, and
nothing carries what it did not. A switch that feels expensive is a reason to
make switching cheaper, never a reason to merge two mandates into one agent.

---

## What of an agent can be imported

Import is settled one part at a time, and a part that can be imported is never
refused because another part cannot.

- **Skills import whole.** A third-party skill is scanned as it is fetched and
  is loadable at once when the scan is clean —
  `src/tools/skill_tools/README.md` owns the mechanism and
  `src/skills/importing-a-skill/SKILL.md` the judgment.
- **A config entry imports as associations** — which skills, which data roots,
  which environment. A list of associations grants nothing, which makes it the
  most portable part of an agent. An attachment refers to a skill and never copies
  one, so the same skill serves as many agents as list it.
- **A charter's role description imports as content to read.** A downloaded
  description of what a role does is prose, and the user adopts it into a
  charter by reading it. `skills.py convert` writes a foreign definition in as
  a skill, and a file describing a whole agent writes nothing at all until the
  run that adopts it.
- **A whole agent travels as one file** — its charter, its config entry with
  every local value taken out, and the address of each skill it lists.
  `src/tools/agent_tools/README.md` §The agent file owns the format, and
  `src/skills/importing-an-agent/SKILL.md` the judgment.
- **The mandate is granted by the user and never by the file.** Who the agent
  answers to, what halts it, and what it may not change are the grant of
  authority itself, and a person reading them is what grants it:
  `import_agent.py` prints the mandate and the guardrails and writes nothing,
  and the second run, after that reading, is the grant. Nothing would make an
  unread mandate valid — not a better format, not a licence, not a signature —
  because the question is who granted the power rather than whether the file is
  safe. This is where a mandate parts from a skill: a skill is a capability, and
  reading it is enough to judge it.
- **Fields that route work in another host do not import** — `tools`, `model`,
  a client's own frontmatter extensions. A session's model and tool surface
  belong to the host it runs in, and the conversion lists each field it drops.
- **The skills a definition declares it depends on are listed as it is
  imported**, so they can be installed rather than sitting in prose the user has
  to notice.

---

## Shared charter clauses

Stated here once. A charter cites the clause and adds only what is specific to
its own agent.

### Session start

Load this charter, then follow `src/app.md` Phases 2 and 3. Beyond the charter,
the one-line index of the installed skills, and the board snapshot, no file
loads before the user says what they want done.
An agent's own snapshot is `python3 src/tools/ticket_tools/agent_status.py
<slug>`.

### The machinery/personal-data split

- **Machinery is this charter plus the agent's own skills and tools.** It is
  reusable, GitHub-safe, and holds no user content.
- **Personal content lives outside `/src`**, under `data/*/<domain>/` or a
  configured folder, and is resolved through `/config` at runtime.
- **Never write a name, a real path, a client, a course, a project or any other
  instance specific into a tracked file**, including as a string literal.
- **A secret lives in the OS keychain and never in a file** — not in config, not
  in a tracked file, not in a git-ignored one. A tool that needs one reads it
  from the keychain at the moment it runs, and a tool that cannot do that asks
  the user rather than storing it.
- **A folder of the user's own work is data, not a repository.** Never `git
  init` one, add it to a remote, or write a git artifact into it: a folder that
  becomes a repository acquires a second history of its own, and the user did
  not ask for one.
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

Each entry of that key is a **folder grant**: a folder, and whether this agent
may write in it or only read it. The user adds and removes one in Bristol
Tickets' Agents tab, and `data_paths.py`'s `agent_folder_grants()` is what reads
them.

- **Write only in a folder whose grant says `write`.** What you would have
  written into a folder granted `read` goes to the user as a proposal instead.
- **A grant decides the folder it gives; the notebook zones decide the rest.**
  Where a grant gives a folder inside the Markdown notebook, that folder's
  access is the grant's, whichever zone it sits in.
- **The grant wins where a charter also states a folder's access**, and a
  charter written from here states none.
- **A grant says where you may write, never what a file there is for.**
  §Changing a file that is already there.
- **What a grant says about removing a file is §Removing a file.**

### Changing a file that is already there

A folder granted `write` is a folder you may add to. A file already in it was
written for a purpose, by the user or by an agent working to one, and that
purpose is not the grant's to change.

- **Add to it, correct it, and extend it within what it is.** A fact into the
  section that owns it, a figure brought up to date, a passage tightened: this
  is ordinary execution and needs no permission.
- **A change that would make it a different document goes to the user first** —
  replacing what it holds, turning it to another subject, or cutting it down to
  something with a new job. Say what the file is now, what you would make it,
  and wait. The grant does not answer this question and neither does being
  right.
- **Write a new file rather than taking one over.** Where what you have needs a
  home the folder does not hold, make one beside it and link the two; a note
  that already has a reader is not a free page.
- **A file you did not write is the user's**, whatever folder it sits in. A
  misspelling in it and a missing Related Notes section are the two exceptions,
  by `src/skills/notebook-proposal/SKILL.md` §What a read-only note takes.
- **Never repurpose a file to avoid asking.** A rewrite that leaves the
  filename standing and changes everything under it is the case this rule
  exists for: the link still resolves, the title still matches, and what the
  reader wanted is gone.

### Removing a file

An agent removes this system's own leftovers as ordinary execution. `src/app.md`
§What a file may say puts the duty on every agent — nothing that is not a real
deliverable is left behind, and you delete your own intermediates — and the
folder grant is what carries the authority to act on it.

- **A `write` grant carries removing this system's own project work from that
  folder.** A folder granted `read`, or granted nothing, carries no removal.
- **This system's own project work is a file an agent of it produced** — a
  generated note, report, export, packet, draft or intermediate — recognised
  from what the file holds and where it sits. Nothing establishes it by marker:
  no watermark, manifest or provenance file is written, read or asked for.
- **A file you cannot place is the user's.** Leave it and say in chat what you
  found and why you left it. That is the case that reaches the user; a file
  plainly your own never does.
- **Delete the files, never the folder**, wherever the user's own work lives.
  Everything outside the repository is unversioned — `/data`, the notebook, the
  user's folders — so nothing removed there comes back by checking it out
  again, and a file you edited rather than produced is the user's.
- **The notebook is decided by its zones** —
  `src/skills/notebook-proposal/SKILL.md` §The three zones. A zone an agent may
  write in is a zone it may remove this system's own output from, and a
  read-only zone stays read-only whatever else it sits inside.
- **Never report deletion as impossible, and never leave the user to clean up
  after you.** A host whose shell cannot remove a file has another route, and
  that host's own skill gives it.
- **A charter's narrower gate wins** where one defines a class of file its agent
  may not remove.

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
  settled when project configuration states it, when a loaded skill
  prescribes it, or when the user made it earlier in this session. Reaching the
  point of acting does not reopen it.
- **Ask only where the decision is new to this session, irreversible, or the
  user's alone to make.**

### Boundaries and coordination

- **An agent maintains its own `tools/<agent>/`, the skills whose
  `bristol.maintainer` gives its slug, and its tagged epics** in the shared tickets
  database (`data/*/tickets/tickets.db`, `epic.owner` = its slug). Never a
  private per-agent database.
- **A folder under `src/tools/`, and a skill's `bristol.maintainer`, give the
  agent that maintains it, never who may run it.** Load a capability from
  outside your own when the task calls for it: the skill index is one line per
  skill, and `src/tools/_shared/README.md` indexes what serves more than one
  agent. Read the index; load only what you will run.
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
entry and described here in general terms at most; the split itself is
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
stated boundary with another agent.}}
```

---

## The governing-doc style contract

Every governing document under `/src` — a charter written from this template,
`src/app.md`, skills, tool READMEs, the other templates — is
written to be executed by a model, not to convince a reader. The reader already
does what it says; what it needs is the rule, its boundary, and which rule wins.
Nine rules, and the one on words below:

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
- **Negatives follow §Words.** In a governing document, the fact a positive
  leaves open includes a route an agent will otherwise reach for: "Never make
  the user the transport" earns its line, and "Do not leave the field blank"
  after "fill in the field" earns nothing.
- **Keep rationale only where the rule under-determines a case the agent will
  meet.** Explain a rule when knowing why changes what the agent does at an edge
  it will actually reach. Otherwise state the rule and stop — a rule that holds
  everywhere needs no defence.
- **State precedence wherever two rules can conflict.** Say which rule wins at the
  point of conflict, in both files if the conflict spans two. Saying which rule
  wins is a boundary, not a claim that one document outranks another; the latter
  is banned by `src/app.md` §What a file may say.
- **Refer to user data in `/src` only by generic relative path**
  (`data/*/tickets/tickets.db`). The instance folder is the `*`.
- **Cut anything that is neither a rule nor a fact.** No preamble justifying the
  file's existence, no history of how a rule came to be, no reassurance, no
  restatement of the previous paragraph in different words.

### Words

This holds for everything an agent writes — a file, a card, a comment, a note,
a line in chat — and not only for governing documents.

- **Every file is written for a person to read.** Only one already shaped
  like configuration — a list, a mapping, a table of values — may be terse.
- **Only a person names something.** A document, a rule, a card or a field
  states, defines, gives, sets, specifies or lists; a person names a child, a
  ship, a price, or someone to a post. "The card names the file" is the misuse,
  and "the card gives the file" is the sentence.
- **State what is done and how, and stop.** "The copy runs each morning at 4:20"
  is the sentence. A clause after it saying what does not happen, or spelling
  out what the sentence already implies, reads to a later session as a rule
  nobody set — a ban on exceptions that may exist, or a limit on what the fact
  covers.
- **A negative stands only where it states a fact the positive leaves open** —
  an absence a reader would otherwise assume, such as a sound a language lacks
  that a neighbouring language has.
