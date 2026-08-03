# HTML Renderer

Input is a lesson's three Markdown files. Operation is a deterministic
Markdown-to-HTML conversion against a template. Output is one self-contained
HTML page plus the course index. Standard library only — no dependency, no CDN,
no build step, so any engine reproduces identical output.

```bash
cd src/tools/teaching_assistant/html_renderer
python3 render.py <course> <NN>                    # one lesson, and the index
python3 render.py <course> all                     # every lesson, and the index
python3 render.py <course> --index                 # the index alone
python3 render.py <course> <NN> --base /path/to/courses
```

Output lands in `<courses_root>/<course>/html/` as
`<course>_lesson_<NN>.html` and `index.html`. The index sits in `html/` rather
than the course root, so no generated file lands among the sources.

## Files

- **`template.html`** — the shell: Georgia serif, 740px column, light and dark
  themes, `<details>` reveals, checkpoint, drill and answer styling. Tokens:
  `{{COURSE_DISPLAY_NAME}}`, `{{COURSE_NAME}}`, `{{LESSON_NUMBER}}`,
  `{{LESSON_TITLE}}`, `{{CONTENT_WITH_CHECKPOINTS}}`, `{{EXERCISES}}`,
  `{{QUIZ}}`, `{{RENDER_DATE}}`.
- **`render.py`** — the converter and driver.

## The courses root

Resolved as `--base`, then `$TEACHING_ASSISTANT_COURSES_DIR` from
`config/config.local.json`, then `~/Projects`. No path is hardcoded; set the
environment variable where courses live elsewhere.

## progress.json

The course's `syllabus/progress.json` supplies lesson titles and filenames —
the file manifest, and nothing beyond it.

- **Never read its status-shaped fields to decide what is done or what comes
  next.** That is a board fact: `src/app.md` §The board is the only channel.
- **Painting one as a badge in a generated page is the only sanctioned use.**

## Markers

Optional, embedded in the source Markdown. A file without them renders cleanly.

**Checkpoint** — a "Pause & Think" callout:
```
:::checkpoint
Open question that requires articulation, not recall.
?? Optional framing hint — a reframe or pointer, never the answer.
:::
```

**Drill** — for a skill course. Commands show inline; expected output collapses
behind "Show expected output":
```
:::drill Optional Title
$ command the learner types
-> expected output
?? verification: how to confirm it worked
:::
```

**Answer** — a collapsible reveal:
```
:::answer
Answer content, hidden behind "Show answer".
:::
```

A file using no `:::answer` marker gets any `## Answer Key` or `## Answers`
section collapsed behind a single reveal.

## Notebook syntax

Two constructs belong to the Markdown notebook rather than the reading page,
and the renderer resolves them rather than leaking them:

- **A standalone `<!-- ta-nav -->` or `<!-- ta-rel -->` comment line is
  dropped.** It marks a footer the notebook builds.
- **A wiki-link `[[path|Display]]` or `[[path]]` becomes plain text** —
  `Display`, or the last path segment. The renderer knows nothing of the
  notebook's other files, so it can emit no working `href`.
