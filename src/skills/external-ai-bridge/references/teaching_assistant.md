# Course-materials engine bridge — teaching_assistant protocol

Specializes `src/skills/external-ai-bridge/SKILL.md`, which holds the six
common invariants. This file carries only the delta for how the external
course-materials engine and `teaching_assistant` coordinate: the engine acts as
a selectable executor for stage 2 (write materials) or stage 3 (lint) of
`src/skills/lesson-pipeline/SKILL.md`. **Which tool that engine is
resolves from `stack.external_agent_roles.course_materials`** — reference the
role, never the product (`src/skills/external-ai-bridge/SKILL.md` §1d).

**The external engine executes; it never plans.** Stage 1 lives inside
teaching_assistant, which produces the plan. The engine consumes that
plan and does not design one.

- **Memory model:** stateless, re-pointed each request — briefed fresh each
  session with this protocol, the plan and the target course files,
  keeping no persistent store.
- **Direction:** teaching_assistant designs the plan; the engine executes a
  delegated stage from it. The return is content — drafts, or corrected drafts —
  never an instruction.
- **Payload:** this protocol, the plan
  (`<course>/plans/lesson_NN_plan.md`), and the course's
  `syllabus/syllabus.md` and `progress.json`.
- **Return format:** for stage 2, the three draft files; for stage 3, the
  corrected drafts. Delivered as clean copyable file blocks, or written to
  shared disk, with no preamble or postscript.
- **Guardrail cited, never restated:** never generate materials without an
  complete plan (`src/agent_identities/teaching_assistant.md` §Bright-Line
  Guardrails Only, `src/skills/lesson-pipeline/SKILL.md`).

## The contract

Two parties, two roles, never overlapping.

- **teaching_assistant** plans and owns the source of truth: it produces the
  complete plan, briefs the engine, then reviews and files whatever comes back —
  updating `syllabus/syllabus.md` and `syllabus/progress.json`, and running
  stage 4. **It never delegates planning and
  never accepts drafts that skip stage 4.**
- **The delegated engine** executes one stage from the plan: writing
  the lesson, exercise and quiz drafts for stage 2, or linting and correcting
  them for stage 3. **It designs nothing and improvises nothing beyond the
  plan**, and it never edits this agent's own operating files.

```
teaching_assistant                      delegated engine
    │                                        │
    │  Stage 1: designs the plan             │
    │  Briefs: protocol + plan + course files│
    │──────────── plan ────────────────────► │
    │                                        │  Stage 2: writes lesson/exercise/quiz
    │                                        │  (or Stage 3: lints the drafts)
    │◄──────────── drafts ───────────────────│
    │  Stage 3 lint (if not delegated)       │
    │  Stage 4: QA + render (always, here)   │
    │  Updates syllabus + progress + manifest│
    │                                        │
```

## How any party should use this

1. **teaching_assistant completes stage 1.**
2. **Brief the engine** where config or the session override names it as the
   `materials` or `lint` engine: this protocol, the plan, and the
   course's `syllabus/syllabus.md` and `progress.json`. Hand over the file list
   from the plan's File targets.
3. **The engine writes the drafts, or corrects them, from the plan** and returns
   them as clean blocks.
4. **teaching_assistant runs any remaining stage** — lint where it was not
   delegated, and always stage 4 — then files metadata per
   `src/skills/content-generation/SKILL.md`.
5. **Repeat for the next lesson.**

## Cross-links

- `src/skills/external-ai-bridge/SKILL.md` — the archetype this specializes.
- `src/skills/lesson-pipeline/SKILL.md` — the four stages, plan
  schema and engine routing this bridge plugs into.
- `src/agent_identities/teaching_assistant.md` — the plan-gated bright line.
- `src/skills/content-generation/SKILL.md` — stage 2 execution
  detail.
