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
- **`quiz.py`** — a quiz's questions, options and correct letters, read out of
  the Markdown so the page can mark them.

**The `studied-box` script in the template is browser-local, and the study
server strips it** — `../study_server/README.md`. A page opened straight off
disk keeps its checkbox that way; a page served keeps the record in
`personal.db` instead. The server's self-check fails if that script stops being
recognizable, so it is where a template change is caught.

## The courses root

`--base` first, used as written. Otherwise
`$TEACHING_ASSISTANT_COURSES_DIR`, and otherwise
`agents.teaching_assistant.env.TEACHING_ASSISTANT_COURSES_DIR` in config.

- **The last two are declarations, and go through
  `config_tools/data_paths.py`**, which owns what a declaration means and finds
  the folder on a host that mounts the user's folders somewhere else.
- **Nothing here expands a path itself**, and there is no guessed fallback: a
  root declared nowhere is an error naming the key.

## progress.json

The course's `syllabus/progress.json` is the course's file manifest and nothing
else. Its whole content is `course`, `course_title`, `schema_version`,
`total_lessons`, and one entry per lesson holding `number`, `topic`, the three
filenames and the three `*_generated` flags saying which files exist.

- **A field saying where the learner stands does not belong here.** Where the
  fleet stands on a course is a card; where the learner stands is the `learning`
  domain of `personal.db` — `docs/architecture.md` §The study interface.
- **The rendered index links lessons and paints no status**, because there is
  none here to paint.

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

## An answerable quiz

A quiz's multiple-choice questions are rendered as options the learner presses.
The page says right or wrong at once and reveals the explanation the answer key
already gives.

- **The correct letter comes out of the source**, from the answer key, from an
  `**Answer: b**` line under the options, or from a `✓` on the option itself.
  `quiz.py` owns the shapes it reads.
- **A question the parse cannot mark keeps the rendering it had.** A
  short-answer question, a quiz with no key at all, a dialect nobody has written
  yet: each renders as prose, and no quiz renders worse than before.
- **The answer key is still rendered**, collapsed as before. It carries the
  model answers to the short-answer questions, which no machine marks.
- **Answering again replaces the answer**, and the score is the questions
  answered correctly out of those the page can mark.

## Marking what a machine cannot

Every `:::drill` on the page and the Exercises section as a whole carry a done
mark. The marks are numbered over the assembled page rather than where a drill
is rendered, because the number has to be unique across the lesson, the
exercises and the quiz.

**Recording needs the study server**, which supplies `window.bristolStudy` —
`../study_server/README.md`. A page opened straight off disk marks its quiz,
reveals its explanations and accepts its done marks, and records none of it.

## Notebook syntax

Two constructs belong to the Markdown notebook rather than the reading page,
and the renderer resolves them rather than leaking them:

- **A standalone `<!-- ta-nav -->` or `<!-- ta-rel -->` comment line is
  dropped.** It marks a footer the notebook builds.
- **A wiki-link `[[path|Display]]` or `[[path]]` becomes plain text** —
  `Display`, or the last path segment. The renderer knows nothing of the
  notebook's other files, so it can emit no working `href`.
