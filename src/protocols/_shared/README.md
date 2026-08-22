# protocols/_shared/

App-level protocol material, maintained by `chief_of_staff` rather than any
domain agent. Loading is `src/templates/identity_template.md` §Boundaries and
coordination.

## Index

One line per capability, and the condition that calls for it.

- **`external_ai_bridge.md`** — the contract for handing work to a stateless
  external AI and filing a reviewable answer back: the six common invariants,
  the memory-model taxonomy, the return-format options. Load it when work leaves
  the session for another AI service, and when writing the thin
  `protocols/<agent>/*_bridge.md` that specializes it with its own parameters.

## What belongs here

- **Promote a contract here once a second agent genuinely reuses the same
  shape.** A single-agent contract stays with its agent and is cited from the
  archetype as an example.

## How an owning agent uses this

An owning agent's charter and playbooks describe the domain-specific
application; its `protocols/<agent>/*_bridge.md` points here for the reusable
contract rather than describing it again. `external_ai_bridge.md` §2 gives the
thin-specialization shape.
