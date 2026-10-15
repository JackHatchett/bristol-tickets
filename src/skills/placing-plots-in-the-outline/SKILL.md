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

Every rule of `src/skills/note-formatting/SKILL.md` holds for the outline
notes and the custom beat sheets; the sections below are their own, and win
for those sections by that skill's first boundary. Building an archetype sheet
from published stories is `src/skills/building-a-beat-sheet/SKILL.md`; this
skill places the novel's own plots.

## 1. Find the tier

- **Put a plot on the outline of the smallest tier that holds it from first
  beat to last** — a book, a cycle of books, the series.
- **Keep a beat in the sheet of the plot it moves, tagged with its book**, so a
  cycle plot's book 1 beats stay in the cycle sheet as "(book 1)".
- **Give a plot that recurs at several tiers on one theme one sheet per tier**
  — a series romance, its cycle romance, each book's romance.
- **Treat the sheets of one theme as overlays, never as containers.** No sheet
  holds another or sits within one: a sheet carries no Within or Holds, and
  each links its parallel plots in `## Related Notes`.
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

## 3. Write the outline note

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
- **Keep only how the tier is divided under `Structure`** in `## Plot` — the
  series into cycles and books, a cycle into books, a book into its parts and
  sequences. Point-of-view rules go at the top of `## Characters`.

## 4. Write the sheet

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
- **`## Seven-Point Highlights`** lists Hook, Plot Turn 1, Pinch 1, Midpoint,
  Pinch 2, Plot Turn 2 and Resolution in that order, each as `Label - event
  (book N)`, and a label stays bare until it is filled:
  - Resolution — the plot's last beat;
  - Hook — the opposite of the Resolution;
  - Midpoint — the beat where the character who resolves the plot turns from
    passive to active;
  - the other four — filled by the author, or when a placed beat is
    recognizably one of them.
- **`## Beats`** is an ordered list in story order, each beat ending with its
  book in parentheses where the book is known:
  - **State each beat as an abstract event**, preferably as "yes, but" or "no,
    and" — the attempt succeeds at a cost, or fails and worsens;
  - **State a resolution as "yes, and" or "no, but"**, and the series' last
    beats as a conclusive yes or no;
  - **Give how the beat happens in the draft as it stands as sub-bullets**
    under it;
  - **Give a dependency or a concurrency as a sub-bullet under the beat it
    concerns, and only where it is known**: `Blocked by beat N of [[x]]`, or
    `Blocked by [[x]]` where the whole plot must resolve first, and
    `Concurrent with beat N of [[x]]`.
- **Link every character, place, object and scene with a note where a beat or
  detail mentions it.**
- **`## Related Notes`** gives the outline of the sheet's tier, the sheet's
  parallel plots, the plots its beats depend on or run with, for a scheme the
  villain's plans note, and the notebook's seven-point structure note.
- **Leave `## Beats` out of a sheet with none yet.** A named plot with only its
  details is a whole sheet.

## 5. Move what is already written

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
- **A Within or Holds bullet on a sheet** → §1; parallel plots are overlays,
  linked in Related Notes.
- **A villain's scheme filed as a character arc** → §2.
- **A foil carrying a character plot** → §3; foils carry story plots only.
- **An outline linking every character it mentions** → §3; those links belong
  in the sheets.
- **A point-of-view character with no slot for a character plot** → §3; write
  the slot as "unnamed".
- **A beat stating only what happens in the draft** → §4; the event goes
  abstract, the draft's version beneath it.
- **A Seven-Point label filled by guesswork** → §4; it stays bare.

## Audit

**Whether a new beat about any plot has exactly one sheet it plainly belongs
in, and that sheet is one link away from the outline of its tier.**
