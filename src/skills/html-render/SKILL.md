---
name: html-render
description: Converts a lesson's three Markdown files into one self-contained HTML page a student can read, and never touches the Markdown. Use when a lesson's drafts are finished and want publishing as a page.
license: MIT
compatibility: Needs python3 and the repository's teaching_assistant renderer.
metadata:
  bristol.kind: playbook
  bristol.maintainer: teaching_assistant
---
# html-render

Convert a lesson's three Markdown files into one self-contained HTML reading
page through the deterministic renderer. It never modifies the source Markdown.

## Preconditions

- **`tools/teaching_assistant/html_renderer/render.py` and `template.html`
  exist.**
- **The target course's `syllabus/progress.json` is populated.**

## Procedure

1. **Author checkpoints and drills into the source first where they are
   missing.** The lesson Markdown carries 2 to 4 `:::checkpoint` markers at
   natural break points — after a section concludes, after a key definition or
   worked example, **never in Summary or What's Next**. Skill courses (terminal,
   git) also get `:::drill` blocks in the exercise file; conceptual courses
   (math, CS theory) use checkpoints rather than drills. Marker syntax:
   `tools/teaching_assistant/html_renderer/README.md`.

2. **Run the renderer:**

   ```bash
   cd tools/teaching_assistant/html_renderer
   python3 render.py <course> <NN>     # one lesson + rebuild that course's index
   python3 render.py <course> all      # every generated lesson + index
   python3 render.py <course> --index  # rebuild index only
   ```

   It resolves the course folder via `/config`, or an explicit `--base`
   override, never a hardcoded path.

3. **Open `<course>/html/<course>_lesson_NN.html` for the user** so they can
   read it immediately.

## Quality check before handing off

- No leftover `{{TOKENS}}` and no raw Markdown in the output.
- Checkpoints present, 2 to 4; skill courses also have drills.
- Exercise and quiz answers collapsed behind `<details>` reveals.
- `html/index.html` regenerated.

## Failure modes

- **The renderer errors on a missing `progress.json` entry** → surface the
  error. The fix belongs in the source Markdown or `progress.json`.
- **Never hand-build HTML or hand-insert a checkpoint at render time.** The
  renderer is deterministic specifically so any engine reproduces identical
  output from the same source.

## Audit

**Check the source Markdown and marker syntax before touching `render.py` or
`template.html`** when a rendered page looks wrong. Most rendering problems are
a source-authoring problem.
