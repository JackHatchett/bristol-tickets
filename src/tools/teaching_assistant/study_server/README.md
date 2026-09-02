# Study Server

Input is the rendered `html/` output already sitting under each course, plus the
`learning` domain of `personal.db`. Operation is an HTTP server on the loopback
interface. Output is a course list, a lesson page carrying its own progress
controls, and the JSON API that page calls.

Standard library only, as the renderer is — no dependency, no CDN, no build
step.

```bash
cd src/tools/teaching_assistant/study_server
python3 serve.py                       # serve, land on the course list
python3 serve.py --course git_course   # land where that course was left
python3 serve.py --port 8765 --base /path/to/courses
python3 serve.py --self-check          # start, serve, write, exit non-zero on failure
python3 serve.py --list-json           # every course, its lessons and where it was left
```

The command prints the URL to open, flushed as it comes up so a parent process
reading the pipe learns the port. `--course` changes only which URL that is;
every course is served either way.

`--list-json` answers the same listing the course page shows and exits, which is
what Bristol Tickets' Courses tab reads. It exits non-zero, naming what is
missing, where the root is undeclared, absent, or holds no rendered course.

## Routes

| Route | Answers |
| --- | --- |
| `GET /` | the course list, each course showing where it was left |
| `GET /<course>/` | that course's rendered index |
| `GET /<course>/resume` | a redirect to the lesson last opened, else the first |
| `GET /<course>/<file>` | a file from that course's `html/` output |
| `GET /api/place[?course=]` | where each course was left |
| `GET /api/marks?course=&lesson=` | what is recorded against one lesson |
| `POST /api/progress` | record one thing the learner did, or clear it |

A progress write is `{course, lesson, kind, item, score, present}`. `kind` is the
learning domain's own vocabulary — `opened`, `reading`, `quiz`, `exercise` — and
`present: false` clears that row rather than writing it.

## What the server adds to a page it serves

- **The rendered file on disk is never edited.** The progress layer is added to
  the response, so re-rendering a lesson cannot lose it and nothing on disk
  depends on the server having run.
- **The page's browser-local progress is removed as it is served.** The
  template's `localStorage` checkbox is per-browser and dies with the site data;
  the served page's checkbox reads and writes `personal.db` instead.
- **Serving a lesson page records `opened`**, which is what `resume` and the
  course list read. It is the server's write rather than the page's, so the
  place is kept whether or not the browser runs the script.
- **The nav offers the previous and next lesson**, so moving on records the new
  position by loading it.
- **`window.bristolStudy.record(kind, present, item, score)`** is the same write
  the checkbox uses, for anything else in the page that has a result to record.

## Boundaries

- **The courses root is the renderer's**, resolved by importing
  `html_renderer/render.py`. There is one resolution of that location and this is
  not a second copy of it.
- **The learning domain is written through `personal_db/personal_write.py`** —
  `record`, `clear`, `marks` and `place`. No SQL is written here.
- **Bind the loopback interface.** `--host` exists for a host that names it
  differently, never to publish the server.
- **A course with no rendered lesson is not listed**, because there is nothing
  to serve.

## The self-check

`--self-check` starts the server on an ephemeral port against a throwaway
`PERSONAL_DB_DIR`, serves one lesson page, writes one progress row and reads it
back, then exits. It fails on a page that answers with a raw `{{TOKEN}}`, a page
that arrives without its progress layer or still carrying browser-local
progress, a refused write, or a write that does not read back.

// The throwaway root is why the check can run against the live installation
// without leaving a row in it.
