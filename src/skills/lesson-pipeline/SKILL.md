---
name: lesson-pipeline
description: Runs a course lesson from plan to finished files in four fixed stages, so any stage can be re-run from what the one before it saved. Use when a new lesson is being made, or to settle which stage owns a step.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: teaching_assistant
---
# lesson-pipeline

The master spec for lesson production: four config-routed stages, each a
discrete step with a fixed interface, so any stage is reproducible from the
persisted artifact and the config rather than from whoever ran the last one.

| # | Stage | Engine | Input | Output |
|---|-------|--------|-------|--------|
| 1 | **Plan** | always teaching_assistant | course state (`syllabus.md`, `progress.json`, epic curriculum map) | a complete lesson plan |
| 2 | **Write materials** | config-routed | the plan | `lesson_NN`, `exercise_NN`, `quiz_NN` drafts |
| 3 | **Lint / fix / edit** | config-routed, may differ from stage 2 | the drafts | corrected drafts |
| 4 | **QA + render** | non-AI, deterministic | the drafts | validated files plus rendered HTML |

- **The plan is the interface.** Every stage consumes the artifact the previous
  stage persisted — never chat scrollback, never an in-memory prompt. That is
  what lets a different engine or a different head pick up any stage.
- **Stage 1 stays inside teaching_assistant.** Planning is where curriculum
  judgment and the no-improvising guarantee live.
- **Stages 3 and 4 always run, whoever wrote stage 2.** An engine can be
  arithmetically correct and still ship markup defects that survive eyeball
  review and are caught only by the render and grep pass.

## Stage 1 — Plan

**Produce the lesson plan as a persisted file**, not an ephemeral prompt.

**Storage:** `<course>/plans/lesson_NN_plan.md`, zero-padded NN, one per lesson,
alongside `lessons/` and `exercises/`. The course folder resolves via `/config`
(`env.TEACHING_ASSISTANT_COURSES_DIR`), as every other course file does.

**Schema** — fixed sections, parseable by header and human-editable:

```
# Lesson NN Plan: [Title]

## Meta
- course: <course-slug>
- lesson: NN

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
- <deviations from src/skills/content-generation/SKILL.md's default house style, if any>
```

**Stage 2 runs on a complete plan** — every section present and filled, no
placeholder left, File targets naming real paths. An incomplete plan is finished
in stage 1 rather than carried into generation.

## Stage 2 — Write materials

**Generate the three files from the plan**, per `src/skills/content-generation/SKILL.md`, which
owns the file shapes, markers and metadata sync. The writer engine comes from
config (`stages.materials`). An external engine takes the plan as its payload
and the hand-off follows `src/skills/external-ai-bridge/references/teaching_assistant.md`;
teaching_assistant writes them directly otherwise. Either way the output is
drafts on disk, not a finished lesson.

## Stage 3 — Lint / fix / edit

A review pass over the drafts for markup defects, voice and style drift, and
cross-lesson consistency. Engine comes from `stages.lint` and **may differ from
stage 2** — the external engine writes and this agent lints, or the reverse.

## Stage 4 — QA + render

Deterministic validation with no engine choice: **check markers are present and
balanced** — even `**`, even backticks, well-formed `:::checkpoint` and
`:::drill`, no leftover tokens — then run
`tools/teaching_assistant/html_renderer/render.py <course> <NN>` (see
`src/skills/html-render/SKILL.md`). Stray markup survives both a writer and a linter, so this
stage runs on every lesson regardless of who produced it.

## Config-driven routing

Per-stage engine selection lives in config under the agent:

```
agents.teaching_assistant.lesson_pipeline.stages = {
  "plan":      "teaching_assistant",   // pinned; changing it is a design error
  "materials": "teaching_assistant",   // or "course_materials" (external role)
  "lint":      "teaching_assistant"    // may differ from materials
}
```

Stage 4 has no key — it is always the deterministic renderer and validator.

- **An engine identifier is either `teaching_assistant` or a role key from
  `stack.external_agent_roles`.** For the external engine use
  `course_materials`, which config resolves to the current tool.
- **Reference the role, never a product name.** The user swaps the external tool
  often, and the config is the whole interface: any caller that reads
  `lesson_pipeline.stages` and reaches the configured engines runs the identical
  pipeline.
- **A session-scoped `lesson_pipeline_override` takes precedence over config**,
  naming per-stage engines for this session only. It is read-only and never
  writes config, so offline runs are unaffected. This mirrors `src/app.md`'s
  `agent_override` over `active_agent`.
- **Write every stage here unless config or a session override routes one
  elsewhere.** `stages.materials` and `stages.lint` are the whole answer; there
  is no per-lesson question about who writes. Where one names an external
  engine, emit the hand-off prompt and the file list, both derived from the
  plan, per `src/skills/external-ai-bridge/references/teaching_assistant.md`.

## Cross-links

- `src/skills/content-generation/SKILL.md` — stage 2 execution detail.
- `src/skills/html-render/SKILL.md` — stage 4 renderer.
- `src/skills/external-ai-bridge/references/teaching_assistant.md` — external-engine hand-off
  for stages 2 and 3.
- `src/agent_identities/teaching_assistant.md` §Bright-Line Guardrails Only —
  the plan-gated bright line.
