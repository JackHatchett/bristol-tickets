---
name: explainer-notes
description: Turns one topic into a small set of linked notes in the Markdown notebook - a hub and three to seven single-idea notes, the whole set one sitting's reading. Use when someone wants to understand a topic rather than study it, and wants to keep what they learn.
license: MIT
compatibility: Runs where the Markdown notebook is reachable; needs python3 to resolve its location.
metadata:
  bristol.kind: playbook
  bristol.maintainer: teaching_assistant
  bristol.scripts: src/tools/config_tools/data_paths.py
---
# explainer-notes

Input: one topic. Operation: the procedure below. Output: a hub note and three
to seven single-idea notes in the Markdown notebook, linked to each other and to
the notes already there.

**An explainer is not a course.** Nothing here produces learning objectives,
exercises, quizzes, checkpoints or a rendered page —
`src/skills/content-generation/SKILL.md` owns those, and a subject that wants
them wants a course.

## What the set is sized to

- **The whole set is one sitting: 2,500 to 4,500 words.** Count it with a word
  count rather than judging it by feel.
- **A single note is 250 to 800 words, and the hub is under 350.** A note past
  the ceiling holds two ideas; a note under the floor is a sentence that belonged
  in another note.
- **Cut whatever the reader did not come for.** Completeness is a course's
  virtue. Here the measure is whether a curious reader wanted the sentence, and
  a true sentence nobody wanted is the commonest thing to cut.

## Choosing which notes exist

- **Every note answers a question the prompted topic raises.** The topic is the
  boundary of the set, and each note is one of its angles.
- **Drop a candidate that would deserve a note even if the topic had never come
  up.** That is the test for a thread that has left the topic, and it is what
  ends a set rather than growing one.
- **Say in one clause why each note is in this set**, in the hub. A note whose
  clause has to reach for a connection is outside the boundary.
- **Give no note to a passing mention.** A name that appears once, in one
  source, with nothing resting on it, belongs in a sentence.
- **Fold two candidates that are one idea under two names into one note.**
- **Prefer the angle the reader would not have thought to ask for** over a
  second summary of the topic from a different height. The set exists to be
  worth more than the answer in chat.

## What one note holds

- **One idea, and the note is named for it.** Depth belongs to the note that
  owns the concept — `src/skills/splitting-an-explanation/SKILL.md`.
- **The filename is lowercase with underscores**, matching the notebook's own
  notes; the heading above the text is written for a person and need not match
  it.
- **The frontmatter is the notebook's own header** — `aliases`, `tags`,
  `created`, `status`, `source_url` — and every alias a reader might link the
  note by goes in `aliases`.
- **At least two outbound links**, to the hub and to at least one sibling or an
  existing notebook note. A note nothing links to and that links nothing is
  invisible.
- **A source is cited where its claim is made**, as an ordinary Markdown link
  carrying the title, never a bare address parked at the bottom.

## Linking into what is already there

- **Search the notebook for an existing note on a concept before writing one.**
  An explainer that restates a note the user already wrote has done the one
  thing this skill exists to prevent.
- **Link an existing note by its filename.** A link resolves across folders, so
  a note in the workspace reaches one the user authored without copying it.
- **Write nothing into the folders the user authors.** Which zones take a write
  is `src/skills/notebook-proposal/SKILL.md`.
- **The hub links every note in the set, and every note links back to the hub.**

## A claim that is a week old

Current events are this skill's normal case, and a course's never.

- **Date every claim that is time-bound**, in the sentence rather than the
  frontmatter.
- **Name the account a contested claim comes from** — whose report, whose
  investigation, whose reporting — and keep those apart rather than merging them
  into one voice.
- **Carry both positions where accounts disagree**, each with its date and its
  source, and mark the disagreement as unresolved rather than picking a winner.
- **Say in the sentence when a claim rests on a single source.**
- **Separate what is settled from what is disputed** within a note, so a reader
  can tell which half they are reading.

## Where the set goes

- **Resolve the notebook's explainers location through
  `src/tools/config_tools/data_paths.py`**, and create it at the
  moment of the write.
- **One directory per topic, named for the topic**, holding the hub and its
  notes and nothing else.

## Procedure

1. **Read the topic's primary accounts first**, and enough of them that the
   disagreements are visible rather than averaged.
2. **Name the angles**, applying §Choosing which notes exist, and settle on
   three to seven.
3. **Search the notebook for each angle** before writing anything, and record
   which existing notes the set will link instead of duplicating.
4. **Write the notes**, then the hub from the notes.
5. **Count the words** for the set and for each note, and cut to the sizes in
   §What the set is sized to.
6. **Follow every link in the hub**, and every link out of each note, and fix
   the ones that resolve to nothing.

## Failure modes

- **The set reads like an encyclopaedia entry** → step 5 was skipped, or the
  cut kept what was true rather than what was wanted.
- **A note repeats a note the user already wrote** → step 3 did not happen.
- **Every note summarises the topic from a different height** → no angles were
  chosen; §Choosing which notes exist.
- **The last note is about a neighbouring subject** → the boundary test was not
  applied to it.
- **One confident narrative where the sources disagree** → §A claim that is a
  week old, and it is the failure that makes an explainer worse than no note.

## Audit

**Whether a reader who followed the set can say what is still unsettled about
the topic.** A set that leaves them certain about a contested subject was
written from one source, however many it cites.
