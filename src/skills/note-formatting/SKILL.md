---
name: note-formatting
description: The shape every note an agent writes in the Markdown notebook takes - filename, frontmatter, Title Case, headings, spacing, no bold, wikilinks, and the Related Notes section that closes it. Use before writing or editing any note in the notebook, whatever produced it.
license: MIT
compatibility: Runs where the Markdown notebook is reachable; needs python3 to resolve its location.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/config_tools/data_paths.py
  bristol.subtitle: The shape every agent-written note takes
---
# note-formatting

Input: a note about to be written or edited in the user's Markdown notebook.
Operation: the rules below. Output: a note in the notebook's own shape.

Which folder of the notebook takes the write, and what happens when the note
belongs in one the user authors, is `src/skills/notebook-proposal/SKILL.md`.
What may be changed in a note already there — and what goes to the user first —
is `src/templates/identity_template.md` §Changing a file that is already there.
This owns the shape alone, and holds for a single note, a note inside a set, and
an edit to a note that is already there.

A **hub note** is the one note in a set that links the others and is linked back
by each of them. Every other note is an ordinary note, and the two differ here
only in §Headings and spacing.

Two boundaries, both stated here so neither has to be guessed at:

- **A skill defining the sections of a particular kind of file wins for those
  sections.** The filename, frontmatter, Title Case, spacing and links below
  still hold.
- **A note the notebook assistant emits from a prompt is
  `src/skills/notebook-prompt-library/SKILL.md` §What a prompt may emit**, which
  takes its shape from the notebook's own templates. This governs what an agent
  writes.
- **A generated daily capture of what is due carries no Related Notes
  section** — `src/tools/personal_db/contacts_due.py` writes it. It is a
  statement about one day rather than an idea with neighbours, and a second run
  that day rewrites it. The filename, the frontmatter, Title Case and the
  spacing below still hold.
- **A generated daily page carrying someone's own posts is
  `src/skills/bluesky-sync/SKILL.md`**, and three rules here do not reach it.
  Its headings are the handles of the people who wrote the posts, so Title Case
  never applies to them. It closes with no Related Notes section, because it is
  a day's record rather than an idea with neighbours. It is produced again from
  the source records rather than edited, so a correction goes into what
  generates it. The filename, the frontmatter and the link form below still
  hold.

## The file

- **Name the file in snake case** — lowercase, words joined by underscores, no
  spaces — and name a folder holding a set the same way.
- **Give the note one H1**, and write it for a person: it need not repeat the
  filename.

## Title Case

Applies to the H1, to every heading under it, and to every alias.

- **Capitalize every word except articles, coordinating conjunctions, and
  prepositions of four letters or fewer.**
- **Capitalize the first and last word whatever they are**, and both halves of a
  hyphenated compound.
- **Leave a name spelled as its owner spells it** — `iPhone`, `METR`,
  `openai` where that is the name.

## Frontmatter

- **Carry `aliases`, `tags` and `created`, in that order**, and `source_url`
  where the note has a source.
- **Make the first alias reproduce the H1 exactly.** Further aliases are the
  other names a reader would search for.
- **Tag a note written in answer to something the user asked `ai/answer`**, and
  a note telling the user what to do `ai/advice`. Those are the only two tags an
  agent applies on its own.
- **Write `created` as `YYYY-MM-DD HH:MM`.**
- **Carry the keys the notebook's own template carries**, `status` among them
  where it has one. Such a key says what the note is, not how work on it is
  going, so it is not the status label `src/app.md` §What a file may say bars:
  that rule bars a label an agent puts on content of its own accord.
- **Give `source_url` the one source the note chiefly rests on**, as a bare URL,
  and omit the key where the note cites none. Every other source is cited in the
  body per §Links.

```
---
aliases:
  - The Title of the Note
tags:
  - ai/answer
created: 2026-09-13 14:05
source_url: https://example.org/the-account-this-note-rests-on
---
```

## Headings and spacing

- **Leave one blank line between a heading and the block under it**, and one
  between blocks.
- **Make every heading below the H1 an `##`.**
- **Open with the overview** — the paragraph or two under the H1, before the
  first `##`.
- **Fill a hub note's `##` sections with bullet lists and nothing else**, each
  bullet a link or a summarizing line.
- **Fill every other note's `##` sections in the notebook's own body shape** —
  `markdown_notebook.note_body` in config, read by the session that is about to
  write a note. Spaced paragraphs where that key gives no shape: a notebook
  whose owner writes no particular way takes prose.
- **The owner's shape governs the body and nothing else.** Where it and a rule
  here disagree, what a section is filled with is his; the filename, the
  frontmatter, Title Case, the link form and the Related Notes section hold
  whatever the shape is. An agent writing in someone's notebook is not choosing
  between this skill and the person whose notebook it is.

## Links

- **Write a link to another note as `[[filename|Alias]]`** — the target by its
  filename, which resolves across folders, and the text by the alias that
  reproduces that note's title.
- **Cite a source as an ordinary Markdown link carrying its title**, in the
  sentence making the claim, never as a bare address parked at the bottom.

## Emphasis

- **Apply no bold anywhere in a note** — not in a heading, a bullet, a table or
  the body, and not as a lead clause on a bullet. Bolding in the notebook is the
  user's. The bold lead clause the governing-doc style contract uses belongs to
  files under `/src` and never travels into a note.
- **Italics are outside this rule**, and stay in use for citing a form or a
  root inline.
- **A program that writes notes follows it too** — a report, a generated page
  and a capture are notes.

## Related Notes

- **Close every note with a `## Related Notes` section**, a blank line, then a
  bulleted list.
- **Make each bullet the link and nothing else** — `- [[filename|Title]]`, the
  Title being that note's H1. The reason beside a link is the user's to write.
- **Include the hub in an ordinary note's list**, and every note of the set in a
  hub's.
- **Add the section to a note you meet without one**, as the last thing in it:
  the notes it already links to or mentions, plus the hub for an ordinary note.
  Say in the session or on the card which notes you changed. Which folders take
  this edit is `src/skills/notebook-proposal/SKILL.md` §What a read-only note
  takes.
- **Leave a section the user wrote as it stands.**
- **Strip the clauses from a section an agent wrote earlier** when you next open
  that note in a folder the agent may write in, and leave its links.

## Failure modes

- **A heading sits directly above its text** → §Headings and spacing, and it is
  the rule broken most often.
- **A link reads `[[some_filename]]`** → the alias is missing, and the reader
  gets a filename where a title belongs.
- **An alias no longer matches the H1 after a retitle** → both move together.
- **A hub section holds a paragraph** → it belongs in the note that section
  links to.
- **Every source parked under a Sources heading** → §Links.
- **Something in a note is bold** → §Emphasis; the user bolds his own notes.
- **A Related Notes bullet carries a clause after its link** → §Related Notes;
  the space after the link is where the user writes his own.

## Audit

**Whether a reader opening the note in the notebook can tell what it is, what it
rests on, and where to go next, without leaving it.**
