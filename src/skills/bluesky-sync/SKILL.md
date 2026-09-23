---
name: bluesky-sync
description: Keeps the user's Bluesky posts in the Markdown notebook as one page per day he posted, linked to that day's journal page where one exists. Use when the copy has to be run or caught up, when a day's page is wrong or missing, when the shape of those pages should change, or when the daily schedule that runs it needs setting up or fixing.
license: MIT
compatibility: Runs where the Markdown notebook is reachable and the machine can make outbound HTTPS requests; needs python3 and nothing installed.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/bluesky/sync.py src/tools/bluesky/install_schedule.py src/tools/test_tools/smoke.py
---
# bluesky-sync

Input: an account's public post records. Operation: group them into
conversations, cut each back to what the account was part of, and write one
Markdown page for each day the account posted. Output: those pages in the
notebook, each linked to that day's journal page where one already exists.

The programs, their options and every configuration key are
`src/tools/bluesky/README.md`. What a page looks like and why is the project
note the epic's cards link to. This owns what a session does.

## The copy is a program, not a task

- **Run it; do not reproduce it.** Reading records and writing Markdown by hand
  produces a page that differs from the one the schedule will write over it.
- **Never put a language model between the record and the page.** The transform
  is mechanical, and a model would paraphrase the user's own words, produce a
  different page each run, and cost something per day for doing so.
- **The one-time copy and the recurring copy are one command with a different
  window.** There is no separate importer to write, and writing one would create
  a second path that nobody exercises.

## A page is generated, never edited

- **Correct what generates a page, then run it again.** An edit to the page
  itself is gone the next time its day falls inside the window.
- **A shape change is a change to `src/tools/bluesky/render.py`**, and
  `src/app.md` §Content is yours; behavior is chief_of_staff's decides who may
  make it.
- **Leave the journal alone beyond the one line.** The journal's daily notes are
  files the user authors; the only write into them is the link, inserted at its
  anchor if absent and never otherwise.

## The owner's own posts

- **Each is a quote carrying a block identifier**, `^bsky-<record key>`, so one
  post embeds in another note as `![[bluesky_YYYY-MM-DD#^bsky-<record key>]]`.
  A post standing alone is a block quote with the identifier on its own line
  after it; a post inside a conversation is one bullet holding the quote, its
  line breaks kept as `<br>`, with the identifier at the end of that bullet.
- **An embed of a post inside a conversation carries the replies nested under
  it.** Obsidian embeds a list item together with its children, and an
  identifier placed anywhere else inside a list item does not resolve. That is
  the intended behaviour, chosen over flattening conversations and over repeating
  the owner's posts in a section of their own.
- **The identifier is the post's record key**, which never changes, so an embed
  survives every rebuild. Never number posts by position on the page.
- **Nothing on a page is bold** — `src/skills/note-formatting/SKILL.md`
  §Emphasis. Asterisks inside a post's own text are its author's and stay.

## Running it

- **A catch-up covering the last week is `--days 7`.** Widen the window rather
  than naming a day: a run covering several days costs seconds and picks up
  anything an earlier failure missed.
- **A whole-history pass is `--all`**, and it is the same command.
- **Use `--budget` where the host will not hold a long command**, and resume
  from the day it gives with `--from`. `--skip-existing` skips days already
  written, which is for filling gaps rather than for rebuilding.
- **Rebuild without `--skip-existing` after any change to how a page is
  built.** Skipping existing days leaves the old shape in place for every day
  that already has one.

## When a day is missing or wrong

Work down this list; the earlier causes are far more common.

1. **The day has no posts.** No page is correct, and this is most days for most
   accounts.
2. **Every conversation that day was dropped.** A thread is dropped when the
   account appears nowhere in the tree that comes back. A reply hidden or
   detached by whoever started the thread does that, and so does a deleted root;
   both are answered by fetching the account's own post and climbing.
3. **The window did not reach the day.** `--days` counts back from now.
4. **The page is there and its contents are stale.** A page is rewritten only
   when its contents would differ, so a page that did not change is a page whose
   inputs did not change.

## A post with no conversation

- **A post the store holds reaches its day whatever became of its thread.** A
  reply whose conversation was never kept is written as a section of its own,
  from the record itself, in the day's own order.
- **Such a post implies no conversation it cannot show** — its own words, and
  nothing else.
- **A post judged prune is left out here as anywhere**, so the notebook keeps
  what it keeps.

## The pictures

- **A run keeps each picture's bytes beside the store**, named for the blob it
  is, and records every blob it has asked about so nothing is fetched twice.
- **A blob the data server no longer serves is recorded as gone**, and the run
  carries on: what was lost before the copy existed is lost, and that page keeps
  its words.
- **A page embeds the kept copy** rather than a content network's address, which
  is what makes the page outlive the account.

## The schedule

- **Install it on the machine that will run it**, with
  `python3 src/tools/bluesky/install_schedule.py --install`, which calls the
  installer every daily job uses, `src/tools/_shared/install_schedule.py`. The installer takes
  the interpreter, the repository and the log location from where it runs, so
  installing from a sandbox that reaches the user's folders through a bridge
  writes that sandbox's paths into a schedule the machine cannot follow.
- **Ask the user to run that one line** where the session cannot —
  `src/skills/manage-tickets/SKILL.md` §Session closure, point 8 shapes the ask,
  and the card's block reason is `capability`.
- **A run's own output is the log the schedule points at**, and reading it is
  how a failed night is found.

## Failure modes

- **A page written by hand** → it is overwritten on the next run covering its
  day, and the effort is lost. Change what generates it.
- **A rebuild run with `--skip-existing`** → the change reaches only days that
  had no page.
- **The schedule installed from the wrong machine** → every path in it belongs
  to a machine that is not there, and it fails silently every morning.
- **A missing day chased as a bug before the account is checked** → most days
  have no posts, and no page is the correct outcome for them.
- **A credential offered and accepted** → nothing here signs in. A password, an
  app password or an API key is a sign that something other than the public
  record is being read.

## Audit

- Every day the account posted has exactly one page, and no other day has one.
- Running the copy twice over the same records changes no file.
- The journal's template links none of these pages.
- Every journal page carrying a link has a page on the other end of it.
