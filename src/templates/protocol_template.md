# {{PROTOCOL_NAME}} — protocol template

> Builds `protocols/<owning_agent>/<contract>.md` — a **coordination contract**: how separate
> parties (agents, AI services, the user) work together. Python analogue: `typing.Protocol` — a
> structural interface independent of vendor or model. A protocol answers *"how do
> separate parties coordinate?"* — distinct from playbooks (procedures run end-to-end by one
> session) and tools (single-purpose callables). Protocols **reference** the owning agent's
> charter (`src/agent_identities/<agent>.md`) for its guardrails and invariants; they never
> restate them.

---

```markdown
# {{Protocol name}} (Canonical)

*Owned by {{owning agent — usually chief_of_staff}}. {{One line: what this contract governs.}}*

## 0. Ground truth (do not duplicate)
{{The canonical sources this protocol references — the owning agent's own charter at
src/agent_identities/<agent>.md (rules/guardrails), config/config.local.json (data paths,
Agent Registries), etc. "If anything here conflicts with the charter, the charter wins."}}

## 1. {{The contract}}
{{The actual coordination rules — roles, message shapes, hand-off format, authority
flows. Whatever this protocol is FOR.}}

## 2. How any party should use this
{{Numbered steps a party follows when this contract is in play.}}

## Cross-links
- `src/agent_identities/<owning_agent>.md` — the hard rules (guardrails) cited, never restated.
- {{related protocols}}
```

---

## Rules for this template

- Filename is `protocols/<owning_agent>/<contract>.md` (snake_case), nested under the agent
  that owns the coordination (e.g. `protocols/writers_room/gemini_crew_handoff.md`).
- **Never restate a charter guardrail** — cite the owning agent's `src/agent_identities/<agent>.md`.
  Drift between a protocol and the canonical charter is the #1 protocol defect; citing instead
  of copying is the fix.
- Each agent owns and version-controls its own `protocols/<agent>/` folder. When two or more
  agents' protocols would re-state the same coordination contract, promote the common core to an
  **archetype under `protocols/_shared/`** and make the per-agent files thin specializations that
  cite it — the same "promote the shared core, thin the specializations" pattern used for
  `tools/wiki_tools/` and `tools/writing_tools/`. Do not duplicate a contract across agents; either
  cite a `_shared/` archetype or reconcile to one canonical source and have the other cite it.
- **Specializing a `_shared/` archetype:** open with one line naming the archetype the file
  specializes, do not re-explain its shared invariants, then state only this agent's specialization
  parameters and genuinely domain-specific delta. `protocols/_shared/external_ai_bridge.md` is the
  reference archetype (every `protocols/<agent>/*_bridge.md` specializes it); see any bridge it
  links for the thin-specialization pattern. Promote a schema or contract into `_shared/` only when
  a second agent genuinely reuses the same shape — a single-agent schema stays with its agent and
  is cited from the archetype as an example rather than hoisted (see `protocols/_shared/README.md`).
