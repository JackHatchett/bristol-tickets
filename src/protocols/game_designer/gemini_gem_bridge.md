# Gemini Gem Bridge — game_designer protocol

**Specializes `protocols/_shared/external_ai_bridge.md`.** The six common
invariants (stateless, non-authoritative, briefed-not-connected, can't write
the source of truth, returns a clean block, sync discipline) live there and
are not restated here. This file carries only game_designer's delta.

- **Memory model:** persistent KB, manual refresh — a design snapshot uploaded
  to a standalone "Offline Collaborator" Gem (or a NotebookLM notebook).
- **Direction:** the Gem *proposes* creative material — story beats,
  character/NPC/location/item designs, open-question answers — none of it fact
  until the user accepts it (worldbuilding the user documents in the notebook;
  mechanics/art `game_designer` files in the repo).
- **Payload:** a generated design snapshot — worldbuilding pulled from the
  user's notebook, plus mechanics/art from the repo `design/` (not the files
  themselves — the Gem can't read either source), uploaded as Knowledge files.
- **Return format:** JSON request/return pair in the project's
  `handoffs/requests/` and `handoffs/returns/` folders (schema below).
- **Guardrails cited, never restated:** `src/agent_identities/game_designer.md`
  holds the hard rules; `playbooks/game_designer/design_proposals.md` is the
  procedure that actually files a return.

## One-time setup (per project, when the user wants this collaborator)

The Gem needs a paid Gemini tier that supports uploaded knowledge files
(Gems with knowledge need Gemini Advanced/Pro-equivalent access) — if the
user would rather not pay, a NotebookLM notebook is a workable but clumsier
substitute for the same role. Setup, once per project:

1. Create a new Gem, named after the project (e.g. "`<Project Title>` —
   Offline Collaborator").
2. Paste this protocol's briefing content (the prime directive, module
   library, and schema sections below) into the Gem's Instructions field.
3. Upload the project's current design snapshot as a Knowledge file (a
   generated pull of worldbuilding from the notebook + mechanics/art from the
   repo `design/` — not those files themselves, since the Gem can't read
   either source). Gems allow multiple knowledge files; a project may split its
   snapshot into a few files (e.g. one per area) rather than one giant document.
4. Whenever the worldbuilding or mechanics/art change meaningfully, regenerate
   and re-upload the affected knowledge file(s) — the sync discipline from the
   archetype, applied to this Gem's KB.

## The prime directive — propose, but never decide

The Gem may originate as much creative material as it likes, but everything
it originates is a proposal, never a fact. Every meaningful field in its
output carries one of these statuses:

| status | meaning | who can set it |
|---|---|---|
| `ESTABLISHED` | already in the notebook/repo; quoted for context, not up for change | `game_designer` only |
| `PROPOSAL` | a new idea from the Gem; needs the user's acceptance | Gem proposes |
| `APPROVED_PENDING` | the user said yes offline, but it isn't documented/filed yet | Gem (records the user's yes) |
| `OPEN_Q` | a known open question; not resolved | either |
| `SIMILARITY_FLAG` | the Gem thinks this may echo an existing work — needs the anti-plagiarism check | Gem |

Nothing is settled until the user accepts it; then it is routed per
`playbooks/game_designer/design_proposals.md` (worldbuilding → the user
documents it in the notebook; mechanics/art → `game_designer` files it in the
repo) and any resolved blocker is closed on the board epic. `APPROVED_PENDING`
means "the user likes it" — still not in the notebook/repo until documented/filed.

## The module library — what the Gem can run

Each module is a repeatable task with defined inputs, steps, and a defined
handoff shape. A project's own worldbuilding (notebook) and art-direction
files supply the domain content each module reasons over — read what the
project actually calls those files rather than assuming a name; this list is
the generic shape, reusable across any game project:

- **Character Design** — principal cast needing full visual consistency.
- **NPC Design** — minor/one-scene characters: appearance, personality,
  function, optional dialogue seeds.
- **Inventory Item Design** — pickup items: function, look, examine text.
- **Location/Background Art** — full scenes: layout, mood, locked vs.
  proposed facts for that place.
- **Story Development** — beat expansion using Goal → Change → Exit per
  beat (what pulls the player forward, what shifts, why they leave for the
  next beat).
- **Open-Question Resolver** — takes one of the project's own open
  questions, offers several proposed answers with trade-offs, recommends
  one, leaves the decision to the user.

Art-producing modules all route through
`tools/game_designer/art_pipeline_walkthrough.md` for the actual
generation/cleanup steps once a design is far enough along to need an
asset.

## REQUEST / RETURN schema

Two file types move through each project's own `handoffs/requests/` and
`handoffs/returns/` folders, both JSON.

**REQUEST** (`game_designer` → Gem):
```json
{
  "handoff_type": "request",
  "request_id": "YYYY-MM-DD_<module>_<slug>",
  "created_by": "game_designer",
  "date": "YYYY-MM-DD",
  "module": "npc_design",
  "summary": "Plain-English one-liner of what's wanted.",
  "parameters": { "...": "module-specific; all changeable by the user mid-session" },
  "design_refs": ["pointers into the project's worldbuilding/design the Gem must respect"],
  "constraints": ["any hard limits for this task"],
  "wants_back": ["which RETURN blocks are expected"]
}
```

**RETURN** (Gem → `game_designer`):
```json
{
  "handoff_type": "return",
  "responds_to": "request_id it answers, or null if a free session",
  "produced_by": "Gem — <project> Offline Collaborator",
  "date": "YYYY-MM-DD",
  "session_summary": "2-4 sentences on what got done.",
  "blocks": { "...": "one key per module run this session" },
  "asset_todo": [{ "asset_id": "...", "tool_chain": ["midjourney","krita","scenario?"], "status": "PROPOSAL" }],
  "proposed_this_session": ["flat list of every PROPOSAL / APPROVED_PENDING item"],
  "still_open": ["OPEN_Q items touched but not resolved"],
  "similarity_flags": ["any SIMILARITY_FLAG items needing the anti-plagiarism check"],
  "questions_for_game_designer": ["decisions that need a human/game_designer call"]
}
```

Naming convention: `YYYY-MM-DD_<module>_<slug>.request.json` /
`....return.json`. Once a return is verified and filed
(`design_proposals.md`), move the matching request + return pair into
`handoffs/archive/<request_id>/` together — a clean `requests/`/`returns/`
pair of folders should only ever show live, unfiled work.

## The round trip

1. `game_designer` writes a REQUEST, saves it to `handoffs/requests/`, tells
   the user which file to paste into the Gem (or names the module in chat
   if no file is needed).
2. The user runs it in the Gem offline; the Gem proposes, the user
   approves/revises. Nothing is locked at this stage.
3. The Gem emits a RETURN in a copy-ready code block; the user saves it to
   `handoffs/returns/` (or pastes it back at the start of the next
   session).
4. `game_designer` ingests the RETURN per `design_proposals.md`: reconciles
   proposals against the whole project, reviews with the user, then routes
   accepted items (worldbuilding → the user documents in the notebook;
   mechanics/art → `game_designer` files in the repo), closes any resolved
   blocker on the board epic, and archives the request/return pair.

## Anti-plagiarism is part of this contract

The Gem runs `tools/game_designer/anti_plagiarism_checklist.md`'s self-check
on everything it proposes before handing it back, tagging anything
uncertain `SIMILARITY_FLAG` rather than silently shipping a near-copy.
`game_designer` runs the same checklist again before anything is accepted —
the Gem's own check is not a substitute for it.

## Cross-links
- `protocols/_shared/external_ai_bridge.md` — the archetype this specializes.
- `src/agent_identities/game_designer.md` — the hard rules (guardrails)
  cited, never restated.
- `playbooks/game_designer/design_proposals.md` — the procedure that handles
  a RETURN.
- `tools/game_designer/copilot_strategic_review.md` — a one-off external
  strategic-review consultation (a related but non-ongoing external-AI use).
