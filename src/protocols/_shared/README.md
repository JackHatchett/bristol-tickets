# protocols/_shared/

App-level protocol material, owned by `chief_of_staff` rather than any domain
agent.

- **`external_ai_bridge.md`** — the canonical archetype every
  `protocols/<agent>/*_bridge.md` specializes: the contract for handing work to
  a stateless external AI and filing a reviewable answer back. It holds the six
  common invariants, the memory-model taxonomy and the return-format options;
  each thin bridge names its own parameters and adds only its domain delta.

## What belongs here

- **Promote a contract here once a second agent genuinely reuses the same
  shape.** A single-agent contract stays with its agent and is cited from the
  archetype as an example.
- **`writers_room/handoff.schema.json` stays with `writers_room`.** It is a
  discriminated union over that agent's own crew directions and ID scheme, not a
  generic envelope another agent validates against. Hoisting it here would imply
  a universal contract that does not exist.

## How an owning agent uses this

An owning agent's charter and playbooks describe the domain-specific
application; its `protocols/<agent>/*_bridge.md` points here for the reusable
contract rather than describing it again. `external_ai_bridge.md` §2 gives the
thin-specialization shape.
