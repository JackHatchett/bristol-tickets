---
name: explainer-notes
description: Turns one topic into a small set of linked notes in the Markdown notebook - a hub and three to seven single-idea notes, the whole set one sitting's reading. Use when someone wants to understand a topic rather than study it, and wants to keep what they learn.
license: MIT
compatibility: Runs where the Markdown notebook is reachable; needs python3 to resolve its location.
metadata:
  bristol.kind: playbook
  bristol.maintainer: teaching_assistant
  bristol.scripts: src/tools/config_tools/data_paths.py
  bristol.subtitle: Explain a topic as linked notes
---
# explainer-notes

Input: one topic. Operation: the procedure below. Output: a hub note and three
to seven single-idea notes in the Markdown notebook, linked to each other and to
the notes already there.

**An explainer is not a course.** Nothing here produces learning objectives,
exercises, quizzes, checkpoints or a rendered page; a subject that wants them
wants a course, which this system does not build.

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
- **Shape the note per `src/skills/note-formatting/SKILL.md`** — its filename,
  frontmatter, headings, links and closing section. The hub is a hub note there;
  every other note in the set is an ordinary one.
- **Open on the claim in one sentence**, before its qualifications. A note that
  spends its first paragraph on background has buried what it is for.
- **Close on what the note leaves unsettled**, where anything is.
- **At least two outbound links**, to the hub and to at least one sibling or an
  existing notebook note. A note nothing links to and that links nothing is
  invisible.

## Linking into what is already there

- **Search the notebook for an existing note on a concept before writing one.**
  An explainer that restates a note the user already wrote has done the one
  thing this skill exists to prevent.
- **Write nothing into the folders the user authors.** Which folders take a write
  is `src/skills/notebook-proposal/SKILL.md`.
- **The hub links every note in the set, and every note links back to the hub.**

## Pitching it at the reader

- **Read what the notebook already says around the topic before deciding what
  needs explaining.** The notes the user has written are the evidence of what
  they already know, and better evidence than any guess about a reader.
- **Link a term the notebook already carries; define one it does not**, in a
  clause at its first use.
- **Never pitch by persona.** An age, a grade or a job title is a stand-in for
  knowing the reader, and here the reader is known.
- **Assume the reader comes back to the set weeks later.** Every note is read
  cold, on its own, by someone who has forgotten the chat that produced it.

## A claim that is a week old

Current events are this skill's normal case, and a course's never.

- **Date every claim that is time-bound**, in the sentence rather than the
  frontmatter.
- **Name the account a contested claim comes from** — whose report, whose
  investigation, whose reporting — and keep those apart rather than merging them
  into one voice.
- **Two sources restating one report are one account.** Trace each claim back to
  the account that first made it, and count accounts rather than links.
- **Cite the primary account, never a summary of it.** A write-up of a report is
  evidence of the write-up.
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
2. **Look for the case against the topic's most confident claim**, and give it a
   note where one exists and a paragraph where it does not. A set nobody argued
   with reports one side of a subject that has two.
3. **Name the angles**, applying §Choosing which notes exist, and settle on
   three to seven.
4. **Search the notebook for each angle** before writing anything, and record
   which existing notes the set will link instead of duplicating.
5. **Write the notes**, then the hub from the notes.
6. **Count the words** for the set and for each note, and cut to the sizes in
   §What the set is sized to.
7. **Read the set back against four checks**, and fix what fails rather than
   noting it: every time-bound claim carries its date, every claim resting on one
   account says so in its own sentence, every link resolves, and the hub lists
   what the set leaves unsettled.

## Failure modes

- **The set reads like an encyclopaedia entry** → step 5 was skipped, or the
  cut kept what was true rather than what was wanted.
- **A note repeats a note the user already wrote** → step 3 did not happen.
- **Every note summarises the topic from a different height** → no angles were
  chosen; §Choosing which notes exist.
- **The last note is about a neighbouring subject** → the boundary test was not
  applied to it.
- **Three links to one report counted as three accounts** → §A claim that is a
  week old, and it is how a single-source set reads as a corroborated one.
- **A note defining a term the user already has a note on** → link it instead.
- **One confident narrative where the sources disagree** → §A claim that is a
  week old, and it is the failure that makes an explainer worse than no note.

## Audit

**Whether a reader who followed the set can say what is still unsettled about
the topic.** A set that leaves them certain about a contested subject was
written from one source, however many it cites.
