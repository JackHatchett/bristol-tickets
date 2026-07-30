# Copilot Bridge (Canonical)

**Specializes `protocols/_shared/external_ai_bridge.md`.** The six common
invariants live there and are not restated here. This file carries only the
delta for how the external **course-materials engine** and `teaching_assistant`
coordinate — the engine acting as a **selectable executor** for the lesson
pipeline's Stage 2 (write materials) and/or Stage 3 (lint), per
`playbooks/teaching_assistant/lesson_pipeline.md`. Which tool that engine is
resolves from config (`stack.external_agent_roles.course_materials`; swappable,
so reference the role, not the product — see
`protocols/_shared/external_ai_bridge.md` §1d).

> **The external engine executes; it does not plan.** Planning (Stage 1) lives
> **inside** teaching_assistant, which produces the approved lesson plan. The
> `course_materials` engine, when config or the session override names it as the
> `materials` or `lint` engine, **executes from that plan** — it consumes the
> plan, it does not design one.

- **Memory model:** stateless, re-point each request — the engine is briefed
  fresh each session with this protocol + the approved plan + the target course
  files; it keeps no persistent knowledge store.
- **Direction:** teaching_assistant designs the plan; the `course_materials`
  engine executes a delegated stage from it. The return is **content** (drafts,
  or corrected drafts), not an instruction.
- **Payload:** this protocol, the **approved lesson plan**
  (`<course>/plans/lesson_NN_plan.md`), and the target course's
  `syllabus/syllabus.md` + `progress.json`.
- **Return format:** for Stage 2, the three draft files
  (lesson/exercise/quiz); for Stage 3, the corrected drafts. Delivered as clean
  copyable file blocks (or written to shared disk), no preamble or postscript.
  Stage 4 (deterministic QA + render) then always runs on teaching_assistant's
  side regardless of who wrote or linted — see the pipeline spec.
- **Guardrail cited, never restated:** the hard rule "never generate materials
  without an **approved plan**" lives in
  `src/agent_identities/teaching_assistant.md` and
  `playbooks/teaching_assistant/lesson_pipeline.md`.

## The contract

Two parties, two roles, never overlapping:

- **teaching_assistant** (this agent) plans and owns the source of truth:
  produces the approved lesson plan (Stage 1), briefs the engine, then reviews
  and files whatever comes back — updates `syllabus/syllabus.md`,
  `syllabus/progress.json`, `PROJECT_MANIFEST.md`; runs Stage 4 QA + render. It
  never delegates planning and never accepts drafts that skip Stage 4.
- **Copilot** (the delegated engine, when config/override names it) executes a
  stage **from the approved plan**: for Stage 2, writes the lesson, exercise,
  and quiz drafts; for Stage 3, lints/corrects the drafts. It returns content
  as clean copyable blocks (or writes to shared disk), no commentary mixed in.
  It designs nothing and improvises nothing beyond the plan.

```
teaching_assistant                      Copilot (delegated engine)
    │                                        │
    │  Stage 1: designs + approves the plan  │
    │  Briefs: protocol + plan + course files│
    │──────────── plan ────────────────────► │
    │                                        │  Stage 2: writes lesson/exercise/quiz
    │                                        │  (or Stage 3: lints the drafts)
    │◄──────────── drafts ───────────────────│
    │  Stage 3 lint (if not delegated)        │
    │  Stage 4: QA + render (always, here)    │
    │  Updates syllabus + progress + manifest │
    │                                        │
```

Copilot does not edit this agent's own operating files
(`src/agent_identities/teaching_assistant.md`, playbooks, tools) — it consumes
the plan and returns drafts (the "can't write the source of truth" invariant
from the archetype, applied here).

## How any party should use this

1. teaching_assistant completes Stage 1 and approves the plan.
2. If config or the session override names Copilot as the `materials` (or
   `lint`) engine, brief it with: this protocol, the approved plan
   (`<course>/plans/lesson_NN_plan.md`), and the target course's
   `syllabus/syllabus.md` + `progress.json`. Hand over the deterministic file
   list from the plan's File targets.
3. Copilot writes the drafts (Stage 2) or corrects them (Stage 3) from the
   plan and returns them as clean blocks.
4. teaching_assistant runs any remaining stage (lint if not delegated) and
   always Stage 4 (QA + render), then files metadata per
   `playbooks/teaching_assistant/content_generation.md`.
5. Repeat for the next lesson.

## Cross-links
- `protocols/_shared/external_ai_bridge.md` — the archetype this specializes.
- `playbooks/teaching_assistant/lesson_pipeline.md` — the four-stage pipeline, plan schema, and engine routing this bridge plugs into.
- `src/agent_identities/teaching_assistant.md` — the plan-gated bright line, never restated.
- `playbooks/teaching_assistant/content_generation.md` — Stage 2 execution detail.
