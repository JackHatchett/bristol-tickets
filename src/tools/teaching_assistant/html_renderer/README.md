# HTML Renderer — teaching_assistant reading surface

Turns a lesson's three Markdown files into one **self-contained**,
**deterministic** HTML file — no external dependencies, no CDN, no build
step. Standard library Python only, so it also runs as-is under a future
open-source teaching engine (tool-neutral, portable).

## Files

- `template.html` — the canonical shell: Georgia serif, 740px column, light +
  dark theme, collapsible `<details>` reveals, checkpoint / drill / answer
  styling. Tokens: `{{COURSE_DISPLAY_NAME}}`, `{{COURSE_NAME}}`,
  `{{LESSON_NUMBER}}`, `{{LESSON_TITLE}}`, `{{CONTENT_WITH_CHECKPOINTS}}`,
  `{{EXERCISES}}`, `{{QUIZ}}`, `{{RENDER_DATE}}`.
- `render.py` — deterministic Markdown→HTML converter + driver.

## Usage

```bash
cd src/tools/teaching_assistant/html_renderer
python3 render.py <course> <NN>     # one lesson + rebuild that course's index
python3 render.py <course> all      # every generated lesson + index
python3 render.py <course> --index  # rebuild index only
# override the courses root (see below) for one call:
python3 render.py <course> <NN> --base /path/to/courses
```

Output lands in `<courses_root>/<course>/html/`: `<course>_lesson_<NN>.html`
and `index.html`. Titles and filenames come from the course's
`syllabus/progress.json`, which is the source of truth **for the lesson file
manifest only** — what exists on disk and what it is called.

It is **not** a source of truth for work state. `progress.json` also carries
some status-shaped fields, and this renderer paints a few of them as badges.
That is display in a generated artifact, and it is the only sanctioned use.
No agent may read those fields back to decide what is done or what comes next
— that is a board fact, held in `tickets.db`. See
`src/playbooks/teaching_assistant/navigator.md`.

### Courses root resolution

No personal path is hardcoded in `render.py`. It resolves the courses root
in this order: `--base` flag → `$TEACHING_ASSISTANT_COURSES_DIR` env var
(see `config/config.local.json`) → `~/Projects` as a generic fallback. Set the
env var if courses actually live elsewhere (e.g. a Markdown-notebook project root).

## Marker syntax (optional, embed in the Markdown source)

All three degrade gracefully — a file without markers still renders cleanly.

**Checkpoint** (a "Pause & Think" callout):
```
:::checkpoint
Open question that requires articulation, not recall.
?? Optional framing hint — a reframe or pointer, never the answer.
:::
```

**Drill** (skill courses only — terminal, git):
```
:::drill Optional Title
$ command the learner types
$ another command
-> expected output
?? verification: how to confirm it worked
:::
```
Commands show inline; expected output is collapsed behind "Show expected output".

**Answer** (inline collapsible reveal, for exercises/quizzes):
```
:::answer
Answer content, hidden behind "Show answer".
:::
```

If an exercise/quiz file uses no `:::answer` markers, any `## Answer Key` /
`## Answers` section is auto-collapsed behind a single reveal.

## Notebook-only syntax

Two bits of source-Markdown syntax exist for the Markdown notebook, not the
reading page, and the renderer strips or converts them rather than leaking
them raw into the HTML:

- Standalone HTML comment lines (`<!-- ta-nav -->`, `<!-- ta-rel -->`) are
  dropped — they mark nav/related footers for the notebook, meaningless in
  standalone HTML.
- Wiki-links `[[path|Display]]` / `[[path]]` become plain display
  text (`Display`, or the last path segment) — the renderer has no notion of
  the notebook's other files, so it can't emit a working `href`.

## Design notes

- **Deterministic script, not hand-conversion.** Markdown→HTML conversion is
  mechanical; checkpoints and drills live in the *source* Markdown as
  markers, authored once at generation time, so any engine reproduces
  identical output.
- **Index lives in `html/`, not the course root**, to avoid dropping
  generated artifacts into the content source-of-truth root.
