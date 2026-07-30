# External-AI Bridge (Canonical archetype)

*App-level, owned by `chief_of_staff`. The single archetype every
`protocols/<agent>/*_bridge.md` specializes: the shared contract for handing
work to a stateless external AI (a Gemini Gem, GitHub Copilot, a local LLM, a
briefed crew role) and getting a reviewable answer back.*
*Unifies protocols that each re-stated this same boilerplate — no agent's
actual handoff mechanics change here, only where the common contract is
written down.*

## 0. Ground truth (do not duplicate)

The guardrails an external AI must respect are the **owning agent's own
charter** (`src/agent_identities/<agent>.md`) and, where content is ratified,
that agent's canon/gatekeeping playbook. Neither this archetype nor any thin
bridge restates a guardrail — they cite it. Data paths (KB snapshots, handoff
folders, logs) resolve via `/config`, never hardcoded. If a specialization and
this archetype disagree on shape, this archetype wins on the common contract;
the specialization wins on its own domain delta.

## 1. The common contract (true of every external-AI bridge)

An external AI is a **stateless, non-authoritative collaborator**. Six
invariants hold regardless of which agent, vendor, or domain:

1. **Stateless / non-authoritative.** It has no memory of prior sessions
   except what it is re-briefed, and nothing it produces is a fact. Its output
   is a proposal until the owning agent files it.
2. **Briefed, not connected.** It works from a snapshot, prompt, or
   pointed-at files — never a live link to the source of truth. The snapshot
   is a copy; keeping it current is the owning side's job (see invariant 6).
3. **Cannot write to the source of truth.** It never writes canon, the
   tickets DB, an applications tracker, a file manifest, or voice cards.
   Those are the owning agent's to write. Nothing an external AI returns is
   work state, and the owning agent never lands its return as work state
   anywhere but the board.
4. **Returns a clean, structured, self-contained block.** Its answer comes
   back as one copy-pasteable unit (a fenced text block, a JSON file, a
   schema-validated envelope, or a direct write-back on shared disk — see the
   return-format taxonomy in §1b). No preamble or commentary mixed in; the
   block must capture 100% cleanly on copy.
5. **The owning agent reviews and files the return.** Every proposal is
   reconciled against the whole project and ratified (by the agent, and where
   structural, by the user) before it lands. "Well-formed" only means it
   parsed — never that it is accepted.
6. **Sync discipline.** The external AI's briefing/KB is a snapshot, not a
   live connection. When a source file changes, the owning side re-briefs or
   re-uploads. Drift between the two is a maintenance bug, not an acceptable
   variance.

### 1a. Memory model — the three shapes an external AI's briefing takes

A thin bridge names which one it uses; that choice drives its sync trigger.

| Memory model | How it's briefed | Refresh trigger | Reference bridge |
|---|---|---|---|
| **Persistent KB, manual refresh** | Curated files uploaded once to the tool's own knowledge store (Gemini Gem / NotebookLM). Persist across chats. | Re-upload the affected knowledge file when its source changes. | `career_coach/gemini_gem_bridge.md`, `game_designer/gemini_gem_bridge.md` |
| **Stateless, re-point each request** | No persistent store; the needed files/prompt are handed in fresh every session (GitHub Copilot with repo access, briefed per session). | N/A — nothing persists to go stale; each brief is current by construction. | `teaching_assistant/copilot_bridge.md`, `writers_room/gemini_crew_handoff.md` |
| **Local-LLM session** | Contract lives in the runtime's **system-prompt field**; static reference is pinned/embedded; live files are read/written fresh from shared disk. | Live files read fresh each session; static pins re-embedded on change. | `career_coach/local_fallback.md` |

### 1b. Return format — how a proposal comes back

A thin bridge names which one it uses. In rising order of formality:

- **Pasted text block.** A fenced, delimited block the user copies back into
  the owning session (e.g. career_coach's `TRACKER HANDOFF`). Lowest
  ceremony; good when a human is the transport.
- **Direct write-back on shared disk.** The external runtime shares the
  filesystem and writes live files itself (local-LLM fallbacks). No transport
  step, but only safe when exactly one side drives at a time.
- **Clean prompt/work-order block.** The external AI's deliverable *is* a
  brief the owning agent then executes (teaching_assistant's co-planner hands
  back one lesson prompt). The return is an instruction, not content.
- **JSON request/return pair.** Two files move through
  `handoffs/requests/` and `handoffs/returns/` (game_designer). Machine-
  filable, carries an explicit status taxonomy per field.
- **Schema-validated envelope.** The most formal: a JSON envelope validated
  against a published schema before it's trusted. `writers_room`'s
  `handoff.schema.json` is the reference example — a discriminated union over
  named directions. Reach for this when the return has enough distinct shapes
  that a schema earns its keep; most bridges do not need one.

### 1c. Direction — what the external AI is for

The one axis this archetype does **not** normalize, because it is the point of
each bridge. An external AI may **propose** creative options, **design** a
work order the owning agent executes, **execute** code/assets, or **scout**
raw material (voice specimens) for the owning agent to distil. Each thin
bridge states its direction in one line; nothing here overrides it.

### 1d. Which external tool — resolved from config, never hardcoded

The specific external tool an agent routes to is **config-defined and
swappable**. It lives in `stack.external_agent_roles`, a stable **role → current
tool** binding. Agents (and this archetype) reference the **role**; the bound
tool changes often as the user tests alternatives, and swapping it must touch **one
config value, not any charter or protocol**.

Roles (current bindings in `config.local.json` → `stack.external_agent_roles`;
each `collaborator` is a `stack.ai_collaborators` entry):

| Role (config key) | Owner | For |
|---|---|---|
| `inline_coding` | `game_designer` | hand-writing/editing project code, in the editor — not chat |
| `course_materials` | `teaching_assistant` | writing/linting lesson materials from an approved plan (pipeline Stage 2/3) |
| `notebook_qa` | any | notebook-only Q&A/retrieval, no repo/system context |

**"Copilot" is ambiguous** — three unrelated products share the word (Microsoft
Copilot = chat; GitHub Copilot = in-editor coding; Obsidian Copilot = local
notebook). Never write bare "Copilot" or a hardcoded product name where a role
reference belongs; name the role and let config resolve the product. All these
tools are **advisory consultants, never in the chain of command** (the user = CEO,
Claude = CTO/architecture owner, external AIs = overrulable-with-reason).

### 1e. When to route the user to an external tool — the trigger

Detection lives in the **owning agent's charter** — but the charter names a **role, not a tool**, and states the
task-type trigger only. Two parts, deliberately split:

- **The trigger (charter):** each agent that can punt work states, in its
  charter's coordination section, a one-line rule of the form *"when you hit a
  `<task-type>` task, hand it to the configured `<role>` agent
  (`stack.external_agent_roles.<role>`)."* The agent recognizes the trigger from
  the work in front of it and tells the user in one line.
- **The target (config):** which actual tool that role is, right now, lives in
  `stack.external_agent_roles`. So the user swaps GitHub Copilot for something else
  by editing config; every charter's trigger keeps working unchanged.

This is *not* a separate per-agent "responsibilities list" file — the charter
already is each agent's scoped responsibility list, and a second copy would
drift. The only new durable artifact is the config role table; charters gain one
trigger line apiece.

Reference triggers (each lives in the named charter, pointing at a config role):
- **`game_designer`** → next action is writing/editing project *code* → the
  configured `inline_coding` agent.
- **`teaching_assistant`** → pipeline `materials`/`lint` stage routed out → the
  configured `course_materials` engine (resolved by
  `lesson_pipeline.stages`).
- **any agent** → notebook-only retrieval → the configured `notebook_qa` agent.

## 2. How a thin bridge specializes this

A `protocols/<agent>/<name>_bridge.md` should be short. It:

1. Opens with one line: *"Specializes `_shared/external_ai_bridge.md`."* — and
   does not re-explain the six invariants.
2. States its four specialization parameters: **memory model** (§1a),
   **direction** (§1c), **payload** (what the external AI is briefed with, and
   where that KB/snapshot lives under `data/*`), and **return format** (§1b).
3. Adds only genuinely domain-specific content: the concrete handoff-block
   template or schema, the agent's status taxonomy, the module/mode library,
   any operational quirk (e.g. "no lint tool here, scan the blacklist by
   hand"). This is the delta the archetype cannot hold.
4. Cites the owning charter for guardrails and the owning gatekeeping playbook
   for how a return is filed — never restating either.

## Cross-links
- `src/templates/protocol_template.md` — how to write any protocol; names this
  `_shared/` layer.
- `src/protocols/_shared/README.md` — what lives in the shared protocol layer.
- The reference specializations, one per memory model and return format, are
  linked from the tables in §1a / §1b above.
