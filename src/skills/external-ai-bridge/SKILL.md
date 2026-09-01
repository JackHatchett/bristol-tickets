---
name: external-ai-bridge
description: The contract for handing a piece of work to an AI outside this session — a Gem, an in-editor assistant, a local model — and getting back an answer that can be checked. Use when work is going out to another AI, and when its answer comes back.
license: MIT
metadata:
  bristol.kind: protocol
  bristol.maintainer: chief_of_staff
---
# external-ai-bridge

The archetype every per-agent specialization builds on: the contract for
handing work to a stateless external AI — a Gem, an in-editor coding assistant,
a local LLM, a second model briefed for one job — and getting a reviewable
answer back. Each agent's own delta is a file under `references/`, named for
that agent.

## 0. Ground truth

- **The guardrails an external AI must respect are the owning agent's own
  charter** (`src/agent_identities/<agent>.md`) and, where content is ratified,
  that agent's gatekeeping skill. Neither this archetype nor any thin bridge
  restates a guardrail; both cite it.
- **Data paths resolve via `/config`**, never hardcoded — KB snapshots, handoff
  folders, logs.
- **This archetype wins on the common contract; a specialization wins on its own
  domain delta.**

## 1. The common contract

An external AI is a stateless, non-authoritative collaborator. Six invariants
hold regardless of agent, vendor or domain:

1. **Stateless and non-authoritative.** It has no memory of prior sessions
   beyond what it is re-briefed, and nothing it produces is a fact. Its output
   is a proposal until the owning agent files it.
2. **Briefed, not connected.** It works from a snapshot, a prompt or
   pointed-at files, never a live link to the source of truth. The snapshot is a
   copy, and keeping it current is the owning side's job.
3. **Cannot write to the source of truth.** It never writes canon, the board, an
   applications tracker, a file manifest or a voice card. **Nothing it returns
   is work state**, and the owning agent lands work state nowhere but the board.
4. **Returns one clean, structured, self-contained block** — a fenced text
   block, a JSON file, or a direct write-back on shared disk. No preamble or
   commentary mixed in; the block must capture cleanly on copy.
5. **The owning agent reviews and files the return.** Every proposal is
   reconciled against the whole project and ratified — by the agent, and by the
   user where the change is structural — before it lands. **Well-formed means it
   parsed, never that it is accepted.**
6. **Sync discipline.** When a source file changes, the owning side re-briefs or
   re-uploads. **Drift between the snapshot and the source is a maintenance bug,
   not an acceptable variance.**

### 1a. Memory model

A thin bridge names which one it uses; that choice drives its sync trigger.

| Memory model | How it is briefed | Refresh trigger | Reference bridge |
|---|---|---|---|
| **Persistent KB, manual refresh** | Curated files uploaded once to the tool's own knowledge store; they persist across chats. | Re-upload the affected file when its source changes. | `career_coach/gemini_gem_bridge.md`, `game_designer/gemini_gem_bridge.md` |
| **Stateless, re-pointed each request** | No persistent store; the needed files and prompt are handed in fresh every session. | None — each brief is current by construction. | `teaching_assistant/copilot_bridge.md`, `writers_room/second_model_bridge.md` |
| **Local-LLM session** | Contract lives in the runtime's system-prompt field; static reference is pinned or embedded; live files are read and written from shared disk. | Live files read fresh each session; static pins re-embedded on change. | `career_coach/local_fallback.md` |

### 1b. Return format

A thin bridge names which one it uses, in rising order of formality:

- **Pasted text block** — a fenced, delimited block the user copies back into
  the owning session. Lowest ceremony; right when a human is the transport.
- **Direct write-back on shared disk** — the external runtime shares the
  filesystem and writes the files itself. No transport step, and **safe only
  while exactly one side drives at a time.**
- **Clean prompt or work-order block** — the deliverable is a brief the owning
  agent then executes. The return is an instruction rather than content.
- **JSON request and return pair** — two files moving through
  `handoffs/requests/` and `handoffs/returns/`, machine-filable, carrying an
  explicit per-field status taxonomy.

### 1c. Direction

The one axis this archetype does not normalize, because it is the point of each
bridge. An external AI may **propose** creative options, **design** a work order
the owning agent executes, **execute** code or assets, or **scout** raw
material for the owning agent to distil. **Each thin bridge states its direction
in one line**, and nothing here overrides it.

### 1d. Which external tool

- **Reference the role, never a product name.** The tool an agent routes to
  lives in `stack.external_agent_roles`, a role-to-current-tool binding, and
  swapping it must touch one config value rather than any charter or protocol.
  Each `collaborator` is a `stack.ai_collaborators` entry.
- **Never write bare "Copilot."** Three unrelated products share the word — a
  chat assistant, an in-editor coding assistant, and a local notebook
  assistant — so the bare noun names nothing.
- **An external tool is an advisory consultant, never in the chain of command.**
  Its output is overrulable with reason.

| Role (config key) | Owner | For |
|---|---|---|
| `inline_coding` | `game_designer` | hand-writing and editing project code in the editor, not chat |
| `course_materials` | `teaching_assistant` | writing and linting lesson materials from an approved plan (pipeline stages 2 and 3) |
| `notebook_qa` | any | notebook-only Q&A and retrieval, with no repo or system context |
| `notebook_prompt_library` | `chief_of_staff` | maintaining the notebook assistant's own custom prompts — the same tool as `notebook_qa`, a different job |

### 1e. When to route the user to an external tool

The trigger and the target are deliberately split:

- **The trigger lives in the owning agent's charter**, in its coordination
  section, as one line of the form *"on a `<task-type>` task, hand it to the
  configured `<role>` agent (`stack.external_agent_roles.<role>`)."* The agent
  recognizes the trigger from the work in front of it and tells the user in one
  line.
- **The target lives in config.** Which tool a role currently is sits in
  `stack.external_agent_roles`, so the user swaps tools by editing config and
  every charter's trigger keeps working.
- **Never add a per-agent responsibilities file.** The charter is that list
  already, and a second copy drifts. The only durable artifact here is the
  config role table.

Reference triggers, each in the named charter:

- **`game_designer`** → the next action is writing or editing project code →
  the configured `inline_coding` agent.
- **`teaching_assistant`** → a `materials` or `lint` stage routed out → the
  configured `course_materials` engine, resolved by `lesson_pipeline.stages`.
- **Any agent** → notebook-only retrieval → the configured `notebook_qa` agent.
- **`chief_of_staff`** → a prompt in the assistant's library is being added,
  corrected or indexed → the configured `notebook_prompt_library` agent, per
  `src/skills/notebook-prompt-library/SKILL.md`.

## 2. How a thin bridge specializes this

A `references/<agent>.md` is short. It:

1. **Opens with one line naming the archetype it specializes**, and does not
   re-explain the six invariants.
2. **States its four parameters**: memory model (§1a), direction (§1c), payload
   (what the external AI is briefed with, and where that snapshot lives under
   `data/*`), and return format (§1b).
3. **Adds only genuinely domain-specific content** — the concrete handoff block
   or schema, the agent's status taxonomy, its module or mode library, an
   operational quirk. That delta is what the archetype cannot hold.
4. **Cites the owning charter for guardrails and the owning gatekeeping skill
   for how a return is filed**, restating neither.

## Cross-links

- `assets/protocol_template.md` — how to write a contract with an outside
  party.
- `references/career_coach.md`, `references/career_coach_local_fallback.md`,
  `references/chief_of_staff.md`, `references/game_designer.md`,
  `references/teaching_assistant.md` and `references/writers_room.md` — one
  agent's delta each.
- `src/skills/notebook-prompt-library/SKILL.md` — the procedure behind
  `references/chief_of_staff.md`.
