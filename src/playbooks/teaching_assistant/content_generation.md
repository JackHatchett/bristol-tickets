# content_generation — teaching_assistant playbook

Stage 2 of `lesson_pipeline.md`: turn an approved lesson plan into a course's
lesson, exercise and quiz files, then bring every course metadata file in line
with what was generated. Read `lesson_pipeline.md` first — it owns the stages,
the plan schema, engine routing and the gates. Stages 3 and 4 run after this,
always.

## Preconditions

- **An approved plan exists** at `<course>/plans/lesson_NN_plan.md` with
  `status: approved`. Where it is missing, incomplete or still `draft`, stop and
  finish stage 1; **never generate from no plan**.
- **The target course's folder exists**, resolved via `/config`, one
  Markdown-notebook project per course.

## Procedure

1. **Load the approved plan** and confirm `status: approved` and that its File
   targets, objectives and outline are present. **The plan, not chat scrollback,
   is the spec you write from.**
2. **Generate three files** in the course's folder, at the plan's File-target
   paths, with zero-padded two-digit lesson numbers throughout:
   - `lessons/lesson_NN_topic.md` — 2 to 4 `:::checkpoint` markers at natural
     break points, **never in Summary or What's Next**
   - `exercises/exercise_NN_topic.md` — for skill courses (terminal, git), use
     `:::drill` markers: ordered commands, expected output, verification
   - `quizzes/quiz_NN_topic.md`
3. **Add a row for the new lesson to `syllabus/syllabus.md`.**
4. **Update `syllabus/progress.json`** (schema v2, `lessons[]` objects): set
   `lesson_generated`, `exercise_generated` and `quiz_generated` to `true` for
   this lesson and write the three filenames.
   - **Write content facts only.** Those four fields describe what exists on
     disk. **Never write work state here** — not `current_lesson`,
     `lesson_complete`, `studied`, `mastery` or `course_complete`. Where a
     lesson stands is a board fact; writing it here creates a second tracker
     that will disagree with the board. Advance the ticket, not
     `current_lesson`.
   - **Verify each filename resolves before writing it.** The `lesson_file`,
     `exercise_file` and `quiz_file` values must be the actual filenames landing
     on disk in step 2, never derived from the topic or slug — a topic-derived
     guess drifts silently the moment a written filename differs from the topic
     wording, and any tool trusting `progress.json` then hits a missing file.
5. **Mark the three files as generated in `PROJECT_MANIFEST.md`.**
6. **Render the HTML reading page** —
   `tools/teaching_assistant/html_renderer/render.py <course> <NN>`, per
   `html_render.md`. The Markdown is the source of truth; the HTML is generated
   from it, and both are kept.

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

- **The plan is missing or still `status: draft`** → stop; finish and approve
  stage 1 first.
- **The course folder is absent, or `progress.json` is missing or malformed** →
  stop and surface it rather than guessing a structure.

## Audit

**Whether `PROJECT_MANIFEST.md` and `progress.json` still match what is on disk
for each course.** They are metadata mirrors; the Markdown files are the source
of truth.
