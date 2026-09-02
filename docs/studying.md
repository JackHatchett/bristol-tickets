# Studying on your own

A course is written once and read many times. These pages are yours to work
through at your own pace: nothing is timed, nothing is submitted, and no agent
is in the room while you read.

There are two ways in. The first is the reading interface. The second is the
Markdown itself, which is what the interface is made of.

## What a course is made of

Every course is one folder, and every folder has the same four parts.

- **`syllabus/`** — `syllabus.md` is the running order, one row per lesson.
  `progress.json` beside it is the file manifest: which lessons exist, and
  which of their three files have been written. It says nothing about where you
  are.
- **`lessons/`** — the reading, one file per lesson.
- **`exercises/`** — the practice for that lesson, with an answer key.
- **`quizzes/`** — the check on the lesson, with an answer key.
- **`html/`** — the reading page built from those three, one per lesson, plus an
  index. It is generated: the Markdown is the source, and the page is rebuilt
  from it whenever the Markdown changes.

A course being written has gaps, and `progress.json` is where you see them. A
lesson whose files are not yet generated is simply not there yet.

## The reading interface

Open Bristol Tickets, choose the **Courses** tab, pick a course and press
**Study**. A small server starts on your own machine and your browser opens on
the lesson you last had open — the first one, the first time.

The page does four things the Markdown cannot.

- **A quiz is answered in the page.** Press an option and it says right or wrong
  at once, and shows the explanation the answer key already gives. Answering
  again replaces your answer; the score is out of the questions the page can
  mark. Short-answer questions are yours to think about, and their model
  answers stay in the collapsed key at the foot of the quiz.
- **Exercises and drills carry a done mark**, because no machine marks them.
- **Each lesson carries a studied mark.**
- **Your place is kept.** Opening a lesson records it, so the course reopens
  where you left it, and the mark you ticked last week is still ticked.

Where your place is kept matters: it is a database on your own disk, alongside
the rest of your records, not storage inside a browser. Clearing your browsing
data does not clear your course, and the same place comes back in whichever
browser you open next.

Press **Stop serving** when you are done, or just close the app — it stops the
server on its way out.

## The Markdown, in order

Nothing stops you reading the files directly, and for some courses it is the
better way: an editor you like, a phone with the folder synced, or a moment when
you would rather not open the app.

Read `syllabus/syllabus.md` first. It is the running order and the reason for
it. Then, for each lesson in that order:

1. the lesson,
2. the exercise, working the problems before opening its key,
3. the quiz, answering before opening its key.

The rendered pages under `html/` open in a browser straight off disk and are
pleasanter to read than raw Markdown. They mark a quiz and reveal explanations
exactly as the interface does. What they cannot do is remember any of it: a page
opened this way records nothing, because there is no server behind it to record
to. Your place on this route is the syllabus and your own memory of where you
stopped.

## What this is not

- **Nothing grades code or prose you write.** A quiz is marked because its
  answers are written down; an exercise is not, and the answer key is there so
  you can mark your own.
- **No agent reads where you are.** Your place is read by the interface to
  reopen a page and by nothing else. What the fleet is doing about a course —
  write lesson 8, fix a page — is a card on the board, and that is a different
  thing entirely.
- **A course is not a conversation.** Asking an agent to teach you the lesson
  costs tokens every time and re-teaches what is already written. The reading is
  free once it exists.

## Asking for more

Courses are written by the teaching assistant, and it is the only agent that
writes or edits coursework. A new course, a missing lesson, a page that reads
badly: each is a card on the board assigned to that agent, and the next session
it runs picks it up.
