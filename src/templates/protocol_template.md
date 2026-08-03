# {{PROTOCOL_NAME}} — protocol template

Builds `protocols/<owning_agent>/<contract>.md`: a **coordination contract**
describing how separate parties — agents, AI services, the user — work
together. A protocol answers "how do separate parties coordinate?", distinct
from a playbook (a procedure one session runs end to end) and a tool (a
single-purpose callable). Style contract:
`src/templates/identity_template.md` §The governing-doc style contract.

---

```markdown
# {{Protocol name}} (Canonical)

*Owned by {{owning agent — usually chief_of_staff}}. {{One line: what this contract governs.}}*

## 0. Ground truth
{{The canonical sources this protocol cites — the owning agent's charter at
src/agent_identities/<agent>.md for guardrails, config/config.local.json for data
paths and the `agents` block. Name the winner where this and the charter could
conflict.}}

## 1. {{The contract}}
{{The coordination rules themselves — roles, message shapes, hand-off format,
authority flows.}}

## 2. How any party should use this
{{Numbered steps a party follows when this contract is in play.}}

## Cross-links
- `src/agent_identities/<owning_agent>.md` — the guardrails, cited rather than restated.
- {{related protocols}}
```

---

## Rules for this template

- **The filename is `protocols/<owning_agent>/<contract>.md`** in snake_case,
  nested under the agent that owns the coordination.
- **Never restate a charter guardrail** — cite the owning agent's
  `src/agent_identities/<agent>.md`. Drift between a protocol and its charter is
  the defect this rule exists to prevent.
- **Each agent maintains its own `protocols/<agent>/` folder**, and any agent
  may load what is in it — `src/app.md` §Any capability is loadable.
- **Promote a contract two or more agents would otherwise restate into an
  archetype under `protocols/_shared/`**, and make the per-agent files thin
  specializations that cite it. **Never duplicate a contract across agents**:
  either cite a `_shared/` archetype or reconcile to one canonical source and
  have the other cite it.
- **Specializing an archetype**: open with one line naming it, do not
  re-explain its shared invariants, and state only this agent's specialization
  parameters and its domain delta. `protocols/_shared/external_ai_bridge.md` is
  the reference archetype and its §2 gives the shape.
- **Promote a schema into `_shared/` only where a second agent validates against
  the same shape.** A single-agent schema stays with its agent and is cited from
  the archetype as an example.
