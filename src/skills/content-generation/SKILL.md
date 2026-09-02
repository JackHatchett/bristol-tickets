---
name: content-generation
description: Turns a finished lesson plan into the course's lesson, exercise and quiz files, and brings the course's own records in line with them. Use once a lesson plan is complete and the materials have to be written.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: teaching_assistant
  bristol.scripts: src/tools/teaching_assistant/html_renderer/render.py
---
# content-generation

Stage 2 of `src/skills/lesson-pipeline/SKILL.md`: turn a complete lesson plan
into a course's lesson, exercise and quiz files, then bring every course
metadata file in line with what was generated. Read
`src/skills/lesson-pipeline/SKILL.md` first — it owns the stages, the plan
schema, engine routing and the gates. Stages 3 and 4 run after this, always.

## Preconditions

- **A complete plan exists** at `<course>/plans/lesson_NN_plan.md`, every
  section filled. Where it is missing or has an unfilled section, stop and
  finish stage 1; **never generate from no plan**.
- **The target course's folder exists**, resolved via `/config`, one
  Markdown-notebook project per course.

## Procedure

1. **Load the plan** and confirm its File targets, objectives and outline are
   present. **The plan, not chat scrollback, is the spec you write from.**
2. **Generate three files** in the course's folder, at the plan's File-target
   paths, with zero-padded two-digit lesson numbers throughout:
   - `lessons/lesson_NN_topic.md` — 2 to 4 `:::checkpoint` markers at natural
     break points, **never in Summary or What's Next**
   - `exercises/exercise_NN_topic.md` — for skill courses (terminal, git), use
     `:::drill` markers: ordered commands, expected output, verification
   - `quizzes/quiz_NN_topic.md`
3. **Add a row for the new lesson to `syllabus/syllabus.md`.**
4. **Update `syllabus/progress.json`** (schema v3, `lessons[]` objects): set
   `lesson_generated`, `exercise_generated` and `quiz_generated` to `true` for
   this lesson and write the three filenames.
   - **Write content facts only.** Those fields describe what exists on disk.
     **Never add a field saying where anyone stands** — no `current_lesson`, no
     `lesson_complete`, no `studied`, no `mastery`, no `course_complete`. Where
     the fleet stands on a course is a card, and where the learner stands is the
     `learning` domain of `personal.db`. Advance the ticket.
   - **Verify each filename resolves before writing it.** The `lesson_file`,
     `exercise_file` and `quiz_file` values must be the actual filenames landing
     on disk in step 2, never derived from the topic or slug — a topic-derived
     guess drifts silently the moment a written filename differs from the topic
     wording, and any tool trusting `progress.json` then hits a missing file.
5. **Render the HTML reading page** —
   `tools/teaching_assistant/html_renderer/render.py <course> <NN>`, per
   `src/skills/html-render/SKILL.md`. The Markdown is the source of truth; the HTML is generated
   from it, and both are kept.
6. **Mirror the study guide.** `docs/studying.md` is the source; the copy beside
   the courses in the notebook is a copy of its body. Where the two differ,
   rewrite the notebook copy from the repository one, keeping the notebook
   copy's frontmatter, and confirm the Courses Hub note still links to it. The
   guide describes the shape of a course rather than listing courses, so a new
   course never edits it.

## File shapes

- **Lesson**: `# Lesson NN: [Title]` → Learning Objectives → core concept
  sections → a game-flavored connection for CS and Python tracks only, never
  forced onto terminal, git or math → Summary → What's Next.
- **Exercise**: Overview → 5 to 8 problems of increasing difficulty with an
  answer key → Verification.
- **Quiz**: Instructions → 5 multiple-choice (4 options, 1 correct) → 3
  short-answer → 1 proof or derivation → answer key.

**Style**: professor-style prose, dense, examples-first — not a tutorial and not
a listicle. Define jargon inline on first use with a plain-language analogy.
Unicode math notation, never LaTeX. Code must be valid, runnable, and standard
library only unless the lesson says otherwise.

## Logging

**Record a completed lesson batch on the board** — close the card, or add one
short `add-issue-log` comment to it.

## Failure modes

- **The plan is missing or has an unfilled section** → stop; finish stage 1
  first.
- **The course folder is absent, or `progress.json` is missing or malformed** →
  stop and surface it rather than guessing a structure.

## Audit

**Whether `progress.json` still names what is on disk for each course.** It is
a manifest of the Markdown files, and the Markdown files are the source of
truth.
