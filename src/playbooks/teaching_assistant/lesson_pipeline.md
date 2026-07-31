# Lesson Pipeline — teaching_assistant (master spec)

Modular, config-routed lesson production. Four stages, each a discrete step
with a fixed interface between them, so every stage is reproducible from the
persisted artifact and the config rather than from whoever ran the last stage.
The review and QA stages are mandatory and engine-agnostic: an external
engine can be arithmetically correct and still ship markup defects that are
invisible on eyeball and caught only by the render/grep pass.

## The four stages

| # | Stage | Engine | Input | Output |
|---|-------|--------|-------|--------|
| 1 | **Plan** | **always teaching_assistant** (never delegated) | course state (`syllabus.md`, `progress.json`, epic curriculum-map) | an approved **lesson plan** file |
| 2 | **Write materials** | config-routed (teaching_assistant/Claude, or the external `course_materials` role) | the approved plan | `lesson_NN`, `exercise_NN`, `quiz_NN` drafts |
| 3 | **Lint / fix / edit** | config-routed (may differ from stage 2) | the drafts | corrected drafts |
| 4 | **QA + render** | **non-AI, deterministic, always runs** | the drafts | validated files + rendered HTML |

The **plan is the interface.** Every stage consumes the artifact the previous
stage persisted — never chat scrollback, never an in-memory prompt. That is
what lets a different engine (or a different head) pick up any stage.

Stage 1 must live inside teaching_assistant: planning is where curriculum
judgment and the no-improvising guarantee live. Stages 2 and 3 are the
delegable ones. Stage 4 is deterministic and runs regardless of who wrote —
the L03 defects are exactly what it exists to catch.

## Stage 1 — Plan (the interface artifact)

Produce a **lesson plan** as a persisted file, not an ephemeral prompt.

**Storage:** `<course>/plans/lesson_NN_plan.md` (zero-padded NN, one per
lesson, alongside `lessons/` and `exercises/`). Course folder resolves via
`/config` (`env.TEACHING_ASSISTANT_COURSES_DIR`), same as every other course
file.

**Schema (fixed sections — parseable by header, human-editable):**

```
# Lesson NN Plan: [Title]

## Meta
- course: <course-slug>
- lesson: NN
- planner: teaching_assistant
- status: draft | approved        # stage-2 gate: must be `approved`
- approved_by:                    # user or teaching_assistant; blank until signed off

## Objectives
- <learning objective>  (2–5)

## Section outline
1. <ordered section title — the lesson's spine>

## Worked-example targets
- <concept -> the worked example that must appear>

## Traps to drill
- <common misconception / defect the exercise+quiz must probe>

## Game hooks
- <CS/Python-track connection>   # omit for terminal/git/math courses

## File targets
- lessons/lesson_NN_topic.md
- exercises/exercise_NN_topic.md
- quizzes/quiz_NN_topic.md

## Style pointers
- <deviations from content_generation.md's default house style, if any>
```

**Gate:** stage 2 may not start until `status: approved`. Approval is the
user's sign-off (or teaching_assistant's own when the user has delegated it for
a run). This replaces the old "external co-planner's prompt" as the thing that
authorizes generation — see the guardrail rewording below.

## Stage 2 — Write materials

Generate the three files **from the plan** per
`content_generation.md` (that playbook is now Stage 2's execution detail:
file shapes, markers, metadata sync). Writer engine is chosen by config
(`stages.materials`, below). If the engine is external, the plan is the payload
and the hand-off follows `protocols/teaching_assistant/copilot_bridge.md`; if
it's teaching_assistant, this agent writes them directly. Either way the output
is drafts on disk, not a finished lesson.

## Stage 3 — Lint / fix / edit (always runs)

A review pass over the drafts: markup defects, voice/style drift, cross-lesson
consistency. Engine is config-routed (`stages.lint`) and **may differ from
stage 2** — the external engine writes and this agent lints, or the reverse.
Always runs, whoever wrote stage 2.

## Stage 4 — QA + render (always runs, non-AI)

Deterministic validation, no engine choice: check markers present and balanced
(even `**`, even backticks, `:::checkpoint`/`:::drill` well-formed, no leftover
tokens), then run `tools/teaching_assistant/html_renderer/render.py <course>
<NN>` (see `html_render.md`). Runs on every lesson regardless of who wrote or
linted it. Stray markup survives both a writer and a linter; this is where it
gets caught.

## Config-driven routing

Per-stage engine selection lives in config under the agent:

```
agents.teaching_assistant.lesson_pipeline.stages = {
  "plan":      "teaching_assistant",   // pinned; changing it is a design error
  "materials": "teaching_assistant",   // or "course_materials" (external role)
  "lint":      "teaching_assistant"    // may differ from materials
}
```

Stage 4 has no key — it is always the deterministic renderer/validator.

**Engine identifiers** are either `teaching_assistant` (this Claude agent writes
it) or a **role key from `stack.external_agent_roles`** — for the external
engine, use `course_materials`, which config resolves to the current tool
(swappable). Reference the role, never a hardcoded
product name: the user swaps the external tool often. The config is the whole
interface: any caller that can read `lesson_pipeline.stages` and reach the
configured engines runs the identical pipeline.

**Session override (mirrors app.md's `agent_override`-over-`active_agent`):**
the invoking head may supply a session-scoped `lesson_pipeline_override` naming
per-stage engines for this session only. It takes precedence over config,
is read-only, and never writes config — so offline/Python runs are unaffected.
Interactive path: after the plan is approved, ask the user *who writes today* —
this agent, or the configured external engine; their answer sets the session
override for stage 2. If external, emit the hand-off prompt + the file list —
both derived deterministically from the plan.

## Why this shape

- **Plan-gated.** What authorizes generation is an **approved plan**, not who
  produced it. The planner lives inside teaching_assistant, so a gate on an
  external prompt would gate nothing; a gate on the plan keeps the
  no-improvising guarantee while letting either engine write.
- **Nothing here is chat-specific.** Every stage is defined by
  `lesson_pipeline.stages` in config, so any caller dispatches the same stages
  to the same engines.
- **Mandatory back half.** Stages 3 and 4 always run, engine-agnostic, because
  the failure they catch (silent markup defects) is invisible to the writer.

## Cross-links
- `content_generation.md` — Stage 2 execution detail (file shapes, metadata sync).
- `html_render.md` — Stage 4 renderer.
- `protocols/teaching_assistant/copilot_bridge.md` — external-engine hand-off for stages 2/3.
- `src/agent_identities/teaching_assistant.md` — the plan-gated bright line (§2.5).
- `src/app.md` — the `agent_override` pattern this session override mirrors.
