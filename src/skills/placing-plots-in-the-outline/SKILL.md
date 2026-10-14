---
name: placing-plots-in-the-outline
description: Decides which outline a novel's plot, arc or beat belongs on - series, cycle or book - and which of a plot's tiered beat sheets takes it, then writes it there in the outline's and the sheet's shape. Use when a plot, a character arc, a romance, a mystery or a single beat is added, moved or split, or when an outline note is restructured.
license: MIT
compatibility: Runs where the Markdown notebook is reachable.
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.subtitle: Put each plot and beat on the right outline
---
# placing-plots-in-the-outline

Input: a plot, a character arc, a romance, a mystery or a single beat of a
novel planned on Sanderson's method, as tiered outline notes. Operation: the
steps below. Output: the item in the custom beat sheet that owns it, and that
sheet linked from the outline of its tier.

Where the outline notes and the custom beat sheets live is the project's
content-rules file. Every rule of `src/skills/note-formatting/SKILL.md` holds
for both; the sections below are their own, and win for those sections by
that skill's first boundary. Building an archetype sheet from published
stories is `src/skills/building-a-beat-sheet/SKILL.md`; this skill places the
novel's own plots.

## 1. Find the tier

- **Put a plot on the outline of the smallest tier that holds it from first
  beat to last** — a book, a cycle of books, the series.
- **Keep a beat in the sheet of the plot it moves, tagged with its book**, so a
  cycle plot's book 1 beats stay in the cycle sheet as "(book 1)".
- **Give a plot that recurs in miniature one sheet per tier** — a series
  romance, its cycle romance, each book's romance. The larger sheet lists the
  smaller as one beat and under Holds; the smaller gives the larger under
  Within.
- **Place a beat of such a chain by the question it moves.** "Will they get
  together this book?" is the book sheet; "Whom will she choose?" the cycle's;
  "Will their love last?" the series'. A beat moving two questions goes in
  both sheets, each worded for its own plot.
- **A plot that only feels like a book's plot is still the tier where it
  resolves.** A cycle quest whose first beats fill a book stays a cycle plot,
  and the book's own plot is whatever resolves in the book.

## 2. Find the kind

- **A character plot is an inner change** — a need overcome, a will won back.
- **A story plot is an action or a mystery**, the latter titled as its
  question: Who Is the Warlock?
- **A villain's scheme is a story plot scoped to that villain**, even where the
  villain carries every beat, when the villain has no emotional arc.
- **A romance is a romance plot**, carried by every lover in it.
- **Give every point-of-view character, at every tier they hold a point of
  view in, one character plot and one story plot, and at most one romance.**
  A slot no plot fills yet reads "unnamed".

## 3. Write the outline note

- **Link a plot carried by one character under that character's name in
  Characters**, as `Character -`, `Story -`, `Romance -` or `Scheme -`.
- **Link a plot carried by two or more characters, or by the world, under
  Plot**, with one line saying what it is.
- **Link each sheet once in its outline.** A point-of-view slot filled by a
  shared plot gives that plot's name in plain text.
- **Keep wikilinks on an outline to its sheets, its sibling outlines, its
  Setting section and its opening line.** Characters, places and objects are
  linked in the sheets.
- **Keep an unnamed arc's beats on the outline, under its slot**, grouped as
  `Character - unnamed` and `Story - unnamed`, until the arc is named and they
  move to a sheet of their own.
- **Keep structure on the outline** — the books of a cycle, viewpoint rules,
  how a book opens and ends. Structure is the frame the plots hang on, and no
  sheet owns it.

## 4. Write the sheet

- **Filename**: the plot's name in snake case, in the project's plot folder.
- **Frontmatter**: the notebook's plot-note keys — `aliases` with the H1,
  `tags` with the project's plot tag, `created`, `status`, `source_url`.
- **H1**: the plot's name; a mystery's name is its question.
- **Summary**: one line under the H1 saying what the plot is, with no closing
  period.
- **`## Details`** holds, in this order and only where they apply: Tier; Kind;
  Within; Holds; Carried by; the archetype sheets near it; then the plot's
  standing facts — its premise, its resolution, its contrast with another plot.
- **`## Beats`** is an ordered list in story order, each beat ending with its
  book in parentheses where the book is known, and with nested bullets for
  detail.
- **Link every character, place, object and scene with a note where a beat or
  detail mentions it.**
- **`## Related Notes`** gives the outline of the sheet's tier, and for a
  scheme the villain's plans note.
- **Leave `## Beats` out of a sheet with none yet.** A named plot with only its
  details is a whole sheet.

## 5. Move what is already written

- **Move a beat with its wording**, and its facts with it; a fact the move
  would lose goes into the sheet's Details.
- **Keep a villain's plans note as the nested order of the villain's schemes**,
  the backstory where they weave together, with each scheme the story plays
  out linked in place to its sheet.
- **Keep the archetype re-cut for the author.** A sheet lists the archetype
  sheets near it; reordering its beats to an archetype waits on his word.
- **Name a new plot with the author.** Where he gave no name, offer two to four
  with one recommended, by `src/skills/designing-with-the-author/SKILL.md`
  §Who decides what, and write the recommended one meanwhile.

## Failure modes

- **A book 1 beat of a cycle plot moved to the book outline** → §1; it stays
  in the cycle sheet, tagged "(book 1)".
- **One sheet holding a series romance and its book romance** → §1; one sheet
  per tier.
- **A villain's scheme filed as a character arc** → §2.
- **An outline linking every character it mentions** → §3; those links belong
  in the sheets.
- **A point-of-view character with no slot for a character plot** → §2; write
  the slot as "unnamed".

## Audit

**Whether a new beat about any plot has exactly one sheet it plainly belongs
in, and that sheet is one link away from the outline of its tier.**
