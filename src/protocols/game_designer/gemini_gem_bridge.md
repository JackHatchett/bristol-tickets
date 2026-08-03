# Gemini Gem Bridge — game_designer protocol

Specializes `protocols/_shared/external_ai_bridge.md`, which holds the six
common invariants. This file carries only game_designer's delta.

- **Memory model:** persistent KB, manual refresh — a design snapshot uploaded
  to a standalone Offline Collaborator Gem, or an equivalent notebook tool.
- **Direction:** the Gem proposes creative material — story beats, character,
  NPC, location and item designs, answers to open questions — none of it fact
  until the user accepts it.
- **Payload:** a generated design snapshot: worldbuilding pulled from the user's
  notebook plus mechanics and art from the repo `design/`, uploaded as Knowledge
  files. **Not the source files themselves** — the Gem can read neither source.
- **Return format:** a JSON request and return pair in the project's
  `handoffs/requests/` and `handoffs/returns/` folders.
- **Guardrails cited, never restated:** `src/agent_identities/game_designer.md`
  holds the hard rules; `playbooks/game_designer/design_proposals.md` is the
  procedure that files a return.

## One-time setup, per project

The Gem needs a tier that supports uploaded knowledge files; a notebook tool is
a workable substitute for the same role.

1. **Create a Gem named after the project** — "`<Project Title>` — Offline
   Collaborator".
2. **Paste this protocol's prime directive, module library and schema into the
   Gem's Instructions field.**
3. **Upload the project's current design snapshot as a Knowledge file.** A
   project may split its snapshot across a few files by area rather than one
   large document.
4. **Regenerate and re-upload the affected knowledge file whenever the
   worldbuilding or the mechanics and art change meaningfully.**

## The prime directive: propose, never decide

The Gem may originate as much creative material as it likes, and **everything it
originates is a proposal rather than a fact.** Every meaningful field in its
output carries one status:

| status | meaning | who can set it |
|---|---|---|
| `ESTABLISHED` | already in the notebook or repo; quoted for context, not up for change | `game_designer` only |
| `PROPOSAL` | a new idea from the Gem; needs the user's acceptance | Gem proposes |
| `APPROVED_PENDING` | the user said yes offline, and it is not documented or filed yet | Gem, recording the user's yes |
| `OPEN_Q` | a known open question, unresolved | either |
| `SIMILARITY_FLAG` | may echo an existing work; needs the anti-plagiarism check | Gem |

**Nothing is settled until the user accepts it**, after which it routes per
`design_proposals.md` and any resolved blocker is closed on the board epic.
**`APPROVED_PENDING` means the user likes it, not that it is in the notebook or
repo.**

## The module library

Each module is a repeatable task with defined inputs, steps and handoff shape.
**Read what the project actually calls its own worldbuilding and art-direction
files** rather than assuming a name; this list is the generic shape.

- **Character Design** — principal cast needing full visual consistency.
- **NPC Design** — minor characters: appearance, personality, function, optional
  dialogue seeds.
- **Inventory Item Design** — pickup items: function, look, examine text.
- **Location and Background Art** — full scenes: layout, mood, locked against
  proposed facts for that place.
- **Story Development** — beat expansion by Goal → Change → Exit: what pulls the
  player forward, what shifts, why they leave for the next beat.
- **Open-Question Resolver** — takes one of the project's open questions, offers
  several answers with trade-offs, recommends one, leaves the decision to the
  user.

**Art-producing modules route through
`tools/game_designer/art_pipeline_walkthrough.md`** for generation and cleanup
once a design needs an asset.

## REQUEST / RETURN schema

Two JSON file types move through each project's `handoffs/requests/` and
`handoffs/returns/` folders.

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
  "asset_todo": [{ "asset_id": "...", "tool_chain": ["..."], "status": "PROPOSAL" }],
  "proposed_this_session": ["flat list of every PROPOSAL / APPROVED_PENDING item"],
  "still_open": ["OPEN_Q items touched but not resolved"],
  "similarity_flags": ["any SIMILARITY_FLAG items needing the anti-plagiarism check"],
  "questions_for_game_designer": ["decisions that need a human/game_designer call"]
}
```

**Naming:** `YYYY-MM-DD_<module>_<slug>.request.json` and `....return.json`.
**Move the matching request and return pair into
`handoffs/archive/<request_id>/` once the return is filed**, so `requests/` and
`returns/` only ever show live, unfiled work.

## The round trip

1. **`game_designer` writes a REQUEST** into `handoffs/requests/` and tells the
   user which file to paste into the Gem, or names the module in chat where no
   file is needed.
2. **The user runs it in the Gem offline**; the Gem proposes and the user
   approves or revises. Nothing is locked at this stage.
3. **The Gem emits a RETURN in a copy-ready block**; the user saves it to
   `handoffs/returns/`, or pastes it back at the start of the next session.
4. **`game_designer` ingests the RETURN per `design_proposals.md`**: reconciles
   the proposals against the whole project, reviews with the user, routes
   accepted items to their home, closes any resolved blocker on the board epic,
   and archives the pair.

## Anti-plagiarism is part of this contract

**The Gem runs `tools/game_designer/anti_plagiarism_checklist.md` on everything
it proposes**, tagging anything uncertain `SIMILARITY_FLAG` rather than shipping
a near-copy. **`game_designer` runs the same checklist again before anything is
accepted**; the Gem's own check is not a substitute.

## Cross-links

- `protocols/_shared/external_ai_bridge.md` — the archetype this specializes.
- `src/agent_identities/game_designer.md` — the guardrails cited above.
- `playbooks/game_designer/design_proposals.md` — the procedure that handles a
  RETURN.
- `tools/game_designer/strategic_review.md` — a one-off external
  strategic-review consultation.
