---
name: placing-plots-in-the-outline
description: Decides which outline a novel's plot, arc or beat belongs on - series, cycle or book - and which of a plot's tiered beat sheets takes it, then writes it there in the outline's and the sheet's shape, with its seven points worked in Dan Wells' order. Use when a plot, a character arc, a romance, a mystery or a single beat is added, moved or split, when a plot's seven points are worked, or when an outline note is restructured.
license: MIT
compatibility: Runs where the Markdown notebook is reachable.
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.subtitle: Put each plot and beat on the right outline
---
# placing-plots-in-the-outline

Input: a plot, a character arc, a romance, a mystery or a single beat of a
novel planned on Sanderson's method and Dan Wells' seven-point structure, as
tiered outline notes. Operation: the steps below. Output: the item in the
custom beat sheet that owns it, and that sheet linked from the outline of its
tier.

Every rule of `src/skills/note-formatting/SKILL.md` holds for the outline
notes and the custom beat sheets; the sections below are their own, and win
for those sections by that skill's first boundary. Building an archetype sheet
from published stories is `src/skills/building-a-beat-sheet/SKILL.md`; this
skill places the novel's own plots. The seven-point method is the notebook's
note on Dan Wells' lectures, `seven_point_story.md`.

## 1. Find the tier

- **Put a plot on the outline of the smallest tier that holds it from first
  beat to last** — a book, a cycle of books, the series.
- **Keep a beat in the sheet of the plot it moves, tagged with its book**, so a
  cycle plot's book 1 beats stay in the cycle sheet as "(book 1)".
- **Treat the tiers as parallels.** A plot that recurs at series, cycle and
  book scale is one plot repeating with real differences, one sheet per tier,
  and never a subplot of the tier above; nesting that appears is an effect of
  dependencies. No sheet holds another or sits within one: a sheet carries no
  Within or Holds, and each links its parallels in `## Related Notes`.
- **Give each tier's parallel a smaller question than the tier above, never
  the same one.** The parallel scales its parent's question down to what its
  own tier can answer. A series plot about a dynasty's fall asks why such a
  house could fall at all; its book parallel asks only who betrays it
  first, and the book's journey answers it.
- **Give a plot an arc at each tier it acts in.** A plot acting in two or more
  books of a cycle has a cycle arc and an arc in each of those books; one
  acting in a single book has only that book's arc.
- **A gap cascades down**: an arc missing at one tier is missing at every tier
  below it until it is built.
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
- **A reader's mystery is a story plot apparent to no character** — a question
  only the reader holds. It has no carrier, and the outline lists it apart
  (§4).
- **A villain's scheme is a story plot scoped to that villain**, even where the
  villain carries every beat, when the villain has no emotional arc.
- **A romance is a romance plot**, carried by every lover in it.

## 3. Keep each plot to itself until the matrix

The matrix is the plot alignment spreadsheet: one tab per outline, one column
per plot, a row per chapter. It is where plots meet.

- **Describe every plot before any plot is joined to another.** Each is a
  complete abstraction scoped to its own characters, with placeholder roles
  where it needs others.
- **A beat gives roles, not existing characters, unless the plot is scoped to
  them.** What follows from a plot's own scope stays: in a romance of two named
  lovers, each lover's part is theirs.
- **Write and ask no dependency, concurrency or cross-plot tie before the
  matrix** — in a sheet, an outline, a question to the author or a card's
  criteria.
- **Every fact and connection already written is a placeholder, and none
  constrains a new beat.** "It has to be this character because another choice
  implies it" is never a reason.
- **Weigh a fact by its load** — how many other facts and beats stand on it
  and would change with it — measured afresh from the notes whenever a change
  is weighed. An earlier statement of a dependency, a session's own included,
  is a hint to check.
- **Generalize a choice nothing stands on to its role** — "a secondary
  character deals the blow". A choice many facts stand on stays, and at the
  matrix the session asks what if someone else did it.
- **Ask the author before proposing to remove a heavily loaded fact.** Some
  carry reasons of his own; some plots are his to keep whatever their beats,
  and others are optional however baked in.
- **Presume reuse an accident unless a note documents it as a deliberate
  parallel**, and put it to the author as a proposal; he may keep it as one.
- **Keep thematic juxtaposition out of plot logic.** A note setting one
  character against another is justification, the last step of planning —
  after beats, the matrix, chapters and scenes — worked back from the end.
- **Keep a candidate connection or choice in the sheet's `## Options`** (§5),
  where it bears no load.
- **At the matrix, set one plot's Resolution on another plot's Pinch** where
  the chapters allow it.

## 4. Write the outline note

- **Sort the outline's characters under four headings in `## Characters`**,
  each character once, at the heading for this tier:
  - **POV** — a point-of-view character, with a `Character -` slot and a
    `Story -` slot, each holding one or more plots, and an optional
    `Romance -` slot holding at most one;
  - **Secondary** — a character with no point of view and at least one
    character plot, whose part may be to serve other plots' beats;
  - **Static** — a round character with no arc, and no slots;
  - **Foils** — the antagonist powers whose struggle drives the plots,
    carrying story plots only, each as `Scheme -`.
- **Write a slot no plot fills yet as "unnamed".**
- **Link a plot carried by two or more characters, or by the world, under
  `## Plot`**, with one line saying what it is.
- **List the reader's mysteries together under `## Plot`**, below the other
  plots, under a `Reader's mysteries` bullet.
- **Link each sheet once in its outline.** A slot filled by a shared plot gives
  that plot's name in plain text.
- **On the series and cycle outlines, give under each plot link one line per
  book or cycle the plot reaches**, as `Book N -` or `Cycle N -`:
  - `opens -` with the plot's first beat there, and `last -` with its last;
  - one line with no label where the plot has a single beat there;
  - `ends -` with how the plot ends, in the book or cycle where it ends;
  - `last -` on the furthest placed beat where the ending has no book yet.
- **Keep wikilinks on an outline to its sheets, its sibling outlines, its
  Setting section and its opening line.** Characters, places and objects are
  linked in the sheets.
- **Keep an unnamed arc's beats on the outline, under its slot**, grouped as
  `Character - unnamed` and `Story - unnamed`, until the arc is named and they
  move to a sheet of their own.
- **List the outline's key worldbuilding in `## Setting`** under a `Key
  Worldbuilding, each a setting promise` bullet: an uncapped but minimal set of
  the worldbuilding notes that make promises at this tier, each a setting
  promise (§5), one line per sense as `Sight - [[sheet]]`.
- **Fill every sense with a major entry unique to this outline**, in this
  order:
  - Sight - a location;
  - Touch - an object;
  - Taste - a food;
  - Hearing - music;
  - Smell - a spice with a distinct smell, on every outline of every tier.
- **Religion has no slot of its own.**
- **Keep the tier's structure, and nothing else, under `Structure`** in
  `## Plot` — how the tier is divided, its point-of-view rules, how it opens
  and ends. Plots and their beats go under their own links.

## 5. Write the sheet

- **Folders**: the project's content-rules file gives them — the outline notes
  alone at the top of the plot folder, each sheet in its `<tier>/<kind>`
  subfolder, the tier `series`, `cycle_N` or `book_N` and the kind
  `character`, `story` or `romance`.
- **Filename**: the plot's name in snake case.
- **Frontmatter**: the notebook's plot-note keys — `aliases` with the H1,
  `tags` with the project's plot tag, `created`, `status`, `source_url`.
- **H1**: the plot's name; a mystery's name is its question.
- **Summary**: one line under the H1 saying what the plot is and who carries
  it, with no closing period.
- **`## Details`** holds four bullets in this order, the last two with nested
  bullets, as the archetype sheets hold theirs, with no Variations:
  - Tier — `series`, `cycle N` or `book N`;
  - Kind — `character plot`, `story plot` or `romance`;
  - Promise to the Reader — what the plot promises a reader;
  - Differentiators — what sets it apart, its contrasts with other plots and
    its standing facts.
- **`## Seven-Point Highlights`** lists the seven points in story order, each
  as `Label - event (book N)`, defined as the method defines them:
  - Hook — where the plot starts, the opposite of its Resolution;
  - Plot Turn 1 — what introduces the conflict and sets the plot in motion;
  - Pinch 1 — pressure that forces the characters to act;
  - Midpoint — the turn from reaction to action;
  - Pinch 2 — more pressure, the jaws of defeat;
  - Plot Turn 2 — the last piece that lets them win;
  - Resolution — how the plot ends.
- **Invent the points in the method's order** — Resolution, Hook, Midpoint,
  Plot Turn 1, Plot Turn 2, Pinch 1, Pinch 2 — and propose each to the author
  in that order, by `src/skills/designing-with-the-author/SKILL.md` §Who
  decides what. A label stays bare only while he has not settled it.
- **`## Beats`** is an ordered list in story order, each beat ending with its
  book in parentheses where the book is known:
  - **State each beat as an abstract event**, preferably as "yes, but" or "no,
    and" — the attempt succeeds at a cost, or fails and worsens;
  - **State a resolution as "yes, and" or "no, but"**, and the series' last
    beats as a conclusive yes or no;
  - **Put at least two failed attempts before a success** — the try/fail
    cycle, each failure a beat of its own;
  - **Give how the beat happens as the draft stands as sub-bullets** under it,
    an option kept rather than a commitment.
- **`## Options`** follows Beats: one bullet per candidate connection or
  choice for the matrix. Nothing in Details or Beats cites it, and the matrix
  is where an option is taken or dropped.
- **Link every character, place, object and scene with a note where a beat or
  detail mentions it.**
- **`## Related Notes`** gives the outline of the sheet's tier, the sheet's
  parallels, for a scheme the villain's plans note, and the notebook's
  seven-point note.
- **Leave `## Beats` out of a sheet with none yet.** A named plot with only its
  details is a whole sheet.

### A setting promise

A setting promise is the sheet for one Key Worldbuilding entry (§4): the
promise a piece of the world makes to the reader, set up, optionally kept alive,
and resolved. Every rule above holds for it except where this says otherwise.

- **File it as a story plot** in its tier's `story` folder, named
  `promise_of_<item>`.
- **Build it on the story archetype Promise Made, Kept, Fulfilled**, the
  `promise_made_kept_fulfilled` sheet in the story library —
  `python3 src/tools/config_tools/read_config.py
  markdown_notebook.beat_sheets.story_dir`.
- **Give in Differentiators the sense it fills and the archetype**, with the
  ending it takes, Met in Full or Transformed.
- **Hold the archetype's six beats in `## Beats`**, each under the archetype's
  own label and made specific to the item.
- **Leave out `## Seven-Point Highlights`.**
- **Give in `## Related Notes` the outline of its tier and the archetype.**

## 6. Move what is already written

- **Leave a written sheet as it stands until a session next works that
  plot.** That session brings it to this skill: its points worked by §5, a
  named character the plot is not scoped to generalized by §3, and any
  dependency, concurrency or cross-plot tie in its Beats moved to Options.
- **Move a beat with its wording**, and its facts with it; a fact the move
  would lose goes into the sheet's Differentiators or under the beat.
- **Keep a villain's plans note as the nested order of the villain's schemes**,
  the backstory where they weave together, with each scheme the story plays
  out linked in place to its sheet.
- **Reorder a sheet's beats to an archetype only on the author's word.**
- **Name a new plot with the author.** Where he gave no name, offer two to four
  with one recommended, by `src/skills/designing-with-the-author/SKILL.md`
  §Who decides what, and write the recommended one meanwhile.

## Failure modes

- **A book 1 beat of a cycle plot moved to the book outline** → §1; it stays
  in the cycle sheet, tagged "(book 1)".
- **One sheet holding a series romance and its book romance** → §1; one sheet
  per tier.
- **A book parallel asking the series' question** → §1; it asks a smaller
  one.
- **A Within or Holds bullet on a sheet** → §1; tiers are parallels, linked in
  Related Notes.
- **A villain's scheme filed as a character arc** → §2.
- **A question to the author about how two plots touch, or which existing
  character takes a beat, before the matrix** → §3.
- **A beat given to an existing character the plot is not scoped to** → §3;
  the beat gives the role.
- **A new beat bent to fit an earlier connection** → §3; the connection is a
  placeholder.
- **A foil carrying a character plot** → §4; foils carry story plots only.
- **An outline linking every character it mentions** → §4; those links belong
  in the sheets.
- **A point-of-view character with no slot for a character plot** → §4; write
  the slot as "unnamed".
- **Seven-point labels filled out of the method's order, or left bare without
  a proposal** → §5.
- **A setting promise with Seven-Point Highlights** → §5; it holds the
  archetype's six beats alone.
- **An outline's Setting with a sense left empty, or no spice** → §4.
- **A success on the first try** → §5; two failures come first.
- **A beat stating only what happens in the draft** → §5; the event goes
  abstract, the draft's version beneath it.

## Audit

**Whether a new beat about any plot has exactly one sheet it plainly belongs
in, that sheet is one link away from the outline of its tier, and nothing in
it ties the plot to another before the matrix.**
