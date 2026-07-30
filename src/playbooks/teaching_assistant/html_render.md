# HTML Render — teaching_assistant Playbook (Mode 3)

## Purpose
Convert a lesson's three Markdown files (lesson, exercise, quiz) into one
self-contained HTML reading page via the deterministic renderer tool. Does
not modify the source Markdown.

## Preconditions
`tools/teaching_assistant/html_renderer/render.py` and `template.html`
exist; the target course's `syllabus/progress.json` is populated.

## Procedure

1. **Author checkpoints/drills into the source first, if missing.** Before
   rendering, make sure the lesson Markdown carries 2–4 `:::checkpoint`
   markers at natural break points (after a section concludes, after a key
   definition or worked example — never in Summary / What's Next). For
   skill courses (terminal, git), add `:::drill` blocks to the exercise
   file. Conceptual courses (math, CS theory) use checkpoints, not drills.
   Marker syntax is documented in `tools/teaching_assistant/html_renderer/README.md`.

2. **Run the renderer:**
   ```bash
   cd tools/teaching_assistant/html_renderer
   python3 render.py <course> <NN>     # one lesson + rebuild that course's index
   python3 render.py <course> all      # every generated lesson + index
   python3 render.py <course> --index  # rebuild index only
   ```
   The script resolves the course's actual folder via `/config` (or an
   explicit `--base` override) — never a hardcoded path.

3. **Open the result for the user** so they can read it immediately —
   `<course>/html/<course>_lesson_NN.html`.

## Quality check before handing off
- No leftover `{{TOKENS}}` and no raw Markdown in the output.
- Checkpoints present (2–4); skill courses also have drills.
- Exercise/quiz answers collapsed behind `<details>` reveals.
- `html/index.html` regenerated.

## Tools Used
- `tools/teaching_assistant/html_renderer/render.py`
- `tools/teaching_assistant/html_renderer/template.html`

## Logging Requirements
None beyond the standard session-end board update — rendering doesn't
change course progress state by itself.

## Failure Modes
- The renderer errors on a missing `progress.json` entry → surface the
  error rather than hand-editing HTML directly; the fix belongs in the
  source Markdown or `progress.json`, not in generated output.
- Hand-building HTML or hand-inserting checkpoints at render time is never
  the fix — the renderer is a deterministic script specifically so any
  engine reproduces identical output from the same source.

## Human Audit Notes
If a rendered page looks wrong, check the source Markdown and marker
syntax before touching `render.py` or `template.html` — most rendering
issues are a source-file authoring problem, not a renderer bug.
