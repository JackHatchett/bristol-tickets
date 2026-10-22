---
name: note-formatting
description: The shape every note an agent writes in the Markdown notebook takes - filename, frontmatter, Title Case, headings, spacing, no bold, inline links and sources, and the Links and Related Notes sections that close it. Use before writing or editing any note in the notebook, whatever produced it.
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
  and omit the key where the note cites none. Every other source is cited by
  §Links.

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
- **Link a thing where the note mentions it** when it is itself the subject of
  established facts — an inventor in a history of electricity, a film named in
  a sentence. The link goes on that mention: a note by `[[filename|Alias]]`,
  anything else by a Markdown link carrying its title.
- **Cite a source the text names in the sentence that names it**, as a Markdown
  link carrying its title.
- **List the sources a note rests on without naming them in a `## Links`
  section**, placed directly above `## Related Notes` — the films behind a beat
  sheet whose beats mention Alderaan rather than Star Wars, the overview
  article and papers behind a history. Each bullet is a Markdown link carrying
  its title, with its author before it or a short description after it where
  one helps.
- **Give a part of a source no link of its own.** Alderaan is reached through
  Star Wars.
- **Cite no informal source** — Reddit, a forum, a comment thread. A fact found
  in one is used once it is verified elsewhere, and the other source is the one
  cited. In creative work an informal source may serve as uncited inspiration.
- **Write `## Links` only where a note has such sources.** Few notes do; most
  cite every source inline.

## Emphasis

- **Apply no bold anywhere in a note** — not in a heading, a bullet, a table or
  the body, and not as a lead clause on a bullet. Bolding in the notebook is the
  user's. The bold lead clause the governing-doc style contract uses belongs to
  files under `/src` and never travels into a note.
- **Italics are outside this rule**, and stay in use for citing a form or a
  root inline.
- **A program that writes notes follows it too** — a report, a generated page
  and a capture are notes.

## Wording

- **Write in American English** — center, color, armor, gray, defense, catalog,
  toward, and -ize.
- **Give a human action to a living subject**, by
  `src/templates/identity_template.md` §Words: a word means, a thermostat keeps
  a temperature, the people in a culture count.
- **State the fact in the fewest words that carry it, and stop** — "~384,000
  km away, about 30 Earths across".

## Related Notes

- **Close a note with a `## Related Notes` section wherever it has
  neighbours**, which is nearly every note: a blank line, then a bulleted list.
- **Make each bullet the link and nothing else** — `- [[filename|Title]]`, the
  Title being that note's H1. The reason beside a link is the user's to write.
- **List only notes the body does not already link, plus the key hubs for the
  topic**, which may repeat a link above. A hub whose sections already link its
  set lists none of them again.
- **Include the hub in an ordinary note's list.** A note may sit as a
  sub-bullet under the hub it belongs to.
- **Add the section to a note you meet without one**, as the last thing in it:
  the notes it mentions without linking, plus the hub for an ordinary note.
  Say in the session or on the card which notes you changed. Which folders take
  this edit is `src/skills/notebook-proposal/SKILL.md` §What a read-only note
  takes.
- **Leave a section the user wrote as it stands.**
- **Strip the clauses from a section an agent wrote earlier** when you next open
  that note in a folder the agent may write in, and leave its links.

## A list that outgrows one note

Applies to a note whose body is one table or list looked up by its first
column — a dictionary, a register of names, a list of spent concepts.

- **Keep such a list sorted by its first column**, in the alphabet its entries
  are written in: a language's own order where that language's notes give one,
  and otherwise Latin order, a marked letter straight after its plain one.
- **Split it into a hub and chunks once it passes 50 KB.** The hub keeps the
  list's filename, so every link to the list lands on the hub.
- **Make one initial letter the finest chunk.** Adjacent letters share a chunk
  while it stays under 50 KB; a chunk that passes 50 KB splits at a letter
  boundary, and a single letter past it stays one chunk. A letter the alphabet
  counts as one, such as a digraph, is a letter here.
- **Name a chunk for its letters** — `<list>_d.md`, or `<list>_d_f.md` for a
  run — and title it with the list's title and its letters, as Example
  Dictionary, D–F.
- **Give the hub the list's overview, its column key, any search block, and a
  link to each chunk in letter order.** A search block reads the rows of every
  chunk, and sits in the hub as the one exception to §Headings and spacing's
  bullet-only hub sections.
- **Give each chunk the table's header row, its rows in order, and a Related
  Notes section listing the hub.**
- **Write a row added later into its letter's chunk at its place in order.**

## Failure modes

- **A heading sits directly above its text** → §Headings and spacing, and it is
  the rule broken most often.
- **A link reads `[[some_filename]]`** → the alias is missing, and the reader
  gets a filename where a title belongs.
- **An alias no longer matches the H1 after a retitle** → both move together.
- **A hub section holds a paragraph** → it belongs in the note that section
  links to.
- **A source the text names, cited only at the bottom** → §Links; it takes
  its link where it is named, and `## Links` holds the sources the text never
  names.
- **A Related Notes list repeating the body's links** → §Related Notes; only
  the hubs may repeat.
- **A list note too slow to open, or a row out of order** → §A list that
  outgrows one note.
- **Something in a note is bold** → §Emphasis; the user bolds his own notes.
- **A Related Notes bullet carries a clause after its link** → §Related Notes;
  the space after the link is where the user writes his own.

## Audit

**Whether a reader opening the note in the notebook can tell what it is, what it
rests on, and where to go next, without leaving it.**
