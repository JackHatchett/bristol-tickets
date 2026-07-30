# protocols/_shared/ — cross-agent protocol archetypes

App-level protocol material owned by `chief_of_staff`, not by any single
domain agent. When two or more agents' `protocols/<agent>/` folders were each
re-stating the same coordination contract, the common core is promoted here
and the per-agent files become thin specializations that cite it — the same
"promote the shared core, thin the specializations" pattern used for
`tools/wiki_tools/` and `tools/writing_tools/`.

## What's here

- `external_ai_bridge.md` — the canonical archetype every
  `protocols/<agent>/*_bridge.md` specializes: the shared contract for handing
  work to a stateless external AI (Gemini Gem, GitHub Copilot, local LLM,
  briefed crew role) and filing a reviewable answer back. Holds the six common
  invariants, the memory-model taxonomy, and the return-format options; each
  thin bridge names its own parameters and adds only its domain delta.

## What is deliberately NOT here

- `writers_room/handoff.schema.json` stays under `writers_room/`. It is a
  discriminated union over that agent's own crew directions
  (Quartermaster/Editor/Grammatizator/Proofer) and canon-ID scheme, not a
  generic envelope other agents validate against. The archetype cites it as
  the reference example of a schema-validated return (§1b) rather than
  hoisting a domain-specific schema into the shared layer and implying a
  falsely universal contract. Promote a schema here only if a second agent
  genuinely needs to validate against the same shape.

## How an owning agent uses this

An owning agent's charter and playbooks describe the domain-specific
application; its `protocols/<agent>/*_bridge.md` points here for the reusable
contract rather than re-describing it. See any of the reference bridges linked
from `external_ai_bridge.md` §1a for the thin-specialization pattern.
