# Content Generation — teaching_assistant Playbook (Stage 2: Write materials)

*This is Stage 2 of `lesson_pipeline.md`. It owns the file-writing detail;
the pipeline spec owns the stages, plan schema, engine routing, and gates.
Read `lesson_pipeline.md` first.*

## Purpose
Turn an **approved lesson plan** into a course's actual lesson, exercise, and
quiz files, then keep every course metadata file in sync with what was just
generated. (Stages 3 lint and 4 QA/render run after this, always, per the
pipeline spec.)

## Preconditions
- An **approved lesson plan** exists at `<course>/plans/lesson_NN_plan.md`
  with `status: approved` (Stage 1). If it's missing, incomplete, or still
  `draft`, stop — finish/approve the plan first; never generate from no plan.
- The target course's folder already exists (resolved via `/config`, one
  Markdown-notebook project per course).

## Procedure

1. Load the approved plan (`<course>/plans/lesson_NN_plan.md`). Confirm
   `status: approved` and that its File targets, objectives, and outline are
   present before doing anything else. The plan — not chat scrollback — is the
   spec you write from.
2. Generate three files in the course's folder (paths from the plan's File targets):
   - `lessons/lesson_NN_topic.md` — 2–4 `:::checkpoint` markers at natural
     break points (never in Summary / What's Next)
   - `exercises/exercise_NN_topic.md` — for **skill courses** (terminal,
     git), use `:::drill` markers (ordered commands → expected output →
     verification)
   - `quizzes/quiz_NN_topic.md`
   Zero-padded two-digit lesson numbers throughout (`lesson_01_topic.md`, etc).
3. Update `syllabus/syllabus.md` — add a row for the new lesson.
4. Update `syllabus/progress.json` (schema v2 — `lessons[]` objects) — set
   `lesson_generated` / `exercise_generated` / `quiz_generated` to `true` for
   this lesson's entry, and write the three filenames.
   **Write content facts only.** Those four fields describe what exists on
   disk, which is what this file is for. Do **not** write work state here —
   not `current_lesson`, not `lesson_complete`, not `studied`, `mastery`, or
   `course_complete`. Where a lesson stands is a board fact, held in this
   agent's own cards in `roadmap.db`, and writing it to a JSON file creates a
   second tracker that will disagree with the board. Advance the *ticket*, not
   `current_lesson`.
   **Filename check (required, not optional):** the `lesson_file` /
   `exercise_file` / `quiz_file` values you write must be the *actual*
   filenames landing on disk in step 2, not filenames derived from the
   lesson's topic/slug. A topic-derived guess silently drifts from disk the
   moment a written filename differs from the topic wording, and any tool
   trusting `progress.json` then hits a missing file. Verify each path
   resolves before writing it.
5. Update `PROJECT_MANIFEST.md` — mark the three files as generated.
6. **Render the HTML reading page** — run `tools/teaching_assistant/
   html_renderer/render.py <course> <NN>` (see `html_render.md`). The
   Markdown is the source of truth; the HTML is generated from it and both
   are kept long-term.

## File shapes

**Lesson:** `# Lesson NN: [Title]` → Learning Objectives → core concept
section(s) → a game-flavored connection (CS/Python-track courses only,
never forced onto terminal/git/math) → Summary → What's Next.

**Exercise:** Overview → 5–8 problems, increasing difficulty, with an answer
key → Verification.

**Quiz:** Instructions → 5 multiple-choice (4 options, 1 correct) → 3
short-answer → 1 proof/derivation → answer key.

**Style:** Professor-style prose, dense, examples-first — not a tutorial,
not a listicle. Define jargon inline on first use with a plain-language
analogy. Unicode math notation, no LaTeX. Code: valid, runnable, standard
library only unless the lesson says otherwise.

## Tools Used
- `tools/teaching_assistant/html_renderer/render.py`

## Logging Requirements
Record a completed lesson batch on the board via
`tools/roadmap_tools/roadmap_write.py` — close the card, or add one short
`add-issue-log` comment to it. Not a per-course changelog file, and not a
handoff note (there is no such mechanism).

## Failure Modes
- Plan missing or still `status: draft` → stop; finish/approve Stage 1 first.
- Course folder doesn't exist or `progress.json` is missing/malformed →
  stop and surface this rather than guessing a structure.

## Human Audit Notes
Periodically confirm `PROJECT_MANIFEST.md` and `progress.json` still match
what's actually on disk for each course — these are metadata mirrors, not
the source of truth (the Markdown files are).
