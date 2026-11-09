---
name: building-a-beat-sheet
description: Breaks the published stories an author names into beats and merges them into one cited archetype beat sheet, filed in the notebook's beat-sheet library for its kind and linked from that library's hub. Use when a story, character or historical archetype is to be broken into beats, or a sheet in one of those libraries extended; a scene's beats are prose-drafting's.
license: MIT
compatibility: Runs where the Markdown notebook is reachable; needs python3 to read config.
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.scripts: src/tools/config_tools/read_config.py
  bristol.subtitle: Build an archetype beat sheet from stories
---
# building-a-beat-sheet

Input: a story archetype to break into beats — the kind of plot Sanderson
teaches plotting by, such as the heist or the assault on an invulnerable
fortress. Operation: the steps below. Output: one beat sheet in the library
for its kind and its line in that library's hub.

Every rule of `src/skills/note-formatting/SKILL.md` applies to the sheet. The
sections below are the sheet's own, and win for those sections by that skill's
first boundary.

## 1. Find the library

- **Choose the library by the kind of archetype**, and read its folder from
  config — `python3 src/tools/config_tools/read_config.py
  markdown_notebook.beat_sheets.<kind>_dir`:
  - `story` — the shape of a plot;
  - `character` — the arc a character travels;
  - `historical_story` — the shape of a conflict drawn from history;
  - `historical_character` — the arc a historical figure travels.
- **The hub sits beside the library's folder**, named for it with a leading
  underscore: `story_plot_archetypes/` has `_story_plot_archetypes.md`.
- **Read the hub and two sheets already there before writing**, one merged
  from several sources and one from a single source; an empty library takes
  the story library's sheets as its model.
- **A beat list assembled from several sheets for one work lives with that
  work**, in its project folder, linking the sheets it draws on. The libraries
  contain archetypes only.

## 2. Ask the author

One batch, in the session, before anything is written:

- **Ask which stories he knows that follow the archetype.** His reference
  stories are the sheet's core sources.
- **Offer four to eight candidate sources to jog his memory** — well-known
  stories of the type, each with its year and one clause on why it fits.
- **Ask which candidates he has seen, and whether he disliked any.** One he
  has not seen still serves as a source and goes on his lists (§7); one he
  saw and disliked is dropped, from the sources and from the lists.
- **Ask the clarifying questions the archetype raises**, in the same batch:
  where its boundary lies, whether it has more than one ending, and which
  neighbouring archetype it must be told apart from. Each question offers two to
  four concrete answers with one recommended, by
  `src/skills/designing-with-the-author/SKILL.md` §Who decides what.

## 3. Break each source into beats

- **A source is what the library's kind takes:**
  - a story, for a story archetype;
  - a character's arc through a story, for a character archetype — the bad spy
    redeemed by love takes the spies, not the films;
  - a historical conflict or a historical figure's life, for the two historical
    kinds, from published histories.
- **Write each source's beats in story order**, from the story itself or a
  published synopsis, critique, history or interview.
- **Cite no informal source** — `src/skills/note-formatting/SKILL.md` §Links.

## 4. Merge the beats

- **A beat is core when most sources hit it in the same relative order.**
- **Where the sources share a theme unevenly, a beat is core when it belongs to
  that theme**, though no source carries every core beat and some core beats
  come from fewer than half of them.
- **Each beat gives the sources that carry it.**
- **The beat count is what the sources carry.** There is no target count, and a
  five-beat sheet is whole.
- **A beat fewer sources hit goes under Optional Beats**, giving the source that
  carries it.
- **A run of several beats one source lays over the core is an Optional Path**
  — the escort in Kurosawa's The Hidden Fortress, laid over beats 4 to 8 of the
  assault. The path states which core beats it spans.
- **Endings that differ on the same beats are Alternate Endings in one sheet.**
- **Two archetypes that share early beats and then diverge are two sheets**,
  each listing the other in its Related Notes. Read the library for a sheet the
  new archetype diverges from before deciding which case it is.
- **A source that turns out to tell a different story is a Variation or a sheet
  of its own.** Decide which — an Alternate Ending, Optional Beats, an Optional
  Path, or its own sheet — and say which, with the reason, in the report.
- **Merge before multiplying.** A story whose beats the sheet's core contains,
  with an Alternate Ending, Optional Beats or an Optional Path, is a Variation
  rather than a new sheet.
- **A classic met in research that is a different archetype gets a sheet or a
  card.** A well-known story met while researching this sheet, judged a
  different archetype from it, is built as its own sheet in the same session or
  filed as a backlog card for the agent that builds the sheets; the report
  says which.
  What is judged is the stories this sheet's research meets, and no search
  goes out looking for new archetypes.

## 5. Write the sheet

- **Filename**: the archetype in snake case, inside the library folder.
- **Frontmatter**: by `src/skills/note-formatting/SKILL.md` §Frontmatter, with
  the tags `ai/answer` and `beat_sheet`, the `status` key the library's sheets
  carry, and `source_url` the source the sheet chiefly rests on.
- **H1**: the archetype's name, then a one-line summary of the whole plot with
  no closing period.
- **`## Details`** contains exactly three bullets, each with nested bullets:
  - Promise to the Reader — what the archetype promises a reader who picks it
    up; on a historical sheet, what a reader recognizes when the trigger
    appears, such as labelled factions brawling in the street or one side
    hiring mercenaries;
  - Differentiators — what sets it apart from its nearest neighbours, each
    named;
  - Variations — only those of Alternate Endings, Optional Beats and Optional
    Paths that apply; the bullet is left out where none does.
- **`## Beats`** is an ordered list. Each item is the beat's name in Title Case,
  with nested bullets giving what happens in general and then what happens in
  each source.
- **A historical beat's name is generic**: the beat, a dash, and what happens
  with the actors written as Faction A and Faction B — "Reversal - Exiled
  Faction B Almost Destroys Faction A's Base". The historical events are its
  nested bullets, each with its date.
- **`## Sources Mapped`** is a table with one row per beat and one column per
  source, each cell the source's moment for that beat or "None" with a reason.
  Every sheet merged from two or more sources has one, historical sheets
  included; a sheet resting on a single source has none.
- **`## Links`** lists the source stories, and the histories a historical
  sheet rests on. A story with a literature note in the
  notebook — a note tagged `media/` whose alias is its title — is linked to that
  note as `[[filename|Title]]`; any other story by a Markdown link to its outside
  source.
- **`## Related Notes`** closes the sheet: the hub, the sheets it shares beats
  with, the sheets of the other library on the same kind of conflict, and the
  notes on the method it was built by.
- **Link a historical sheet and a fiction sheet on the same kind of conflict
  both ways** — writing either adds it to the other's Related Notes.

## 6. Link it from the hub

- **Add the sheet's link under its library hub's section for its family of
  archetypes** — Heist, Romance, Odyssey.
- **Open a new `##` section where no family fits**, named for the family in
  Title Case.
- **A sub-bullet under the link may give the one fact a reader choosing among
  sheets needs**, such as an Optional Path drawn from another story.

## 7. Keep the watchlist and the reading list

- **Add each source the author has not seen or read as it becomes a source**,
  to the Plot Archetypes section of the watchlist for a film, show or stage
  work and of the reading list for a book. The notes, their locations and the
  bullet are `src/skills/keeping-the-media-lists/SKILL.md`.

## 8. Report

Give the author the sheet's file and the hub section it went under, any sheet
built or card filed for a classic met on the way, and any watchlist entry
added, in the session or in the comment of the card that asked for it.

## Failure modes

- **A beat kept because one memorable source has it** → it is an Optional Beat.
- **Beats padded or cut to reach a round number** → §4; the count is what the
  sources share.
- **A sheet written before the author named his stories** → §2 comes first; the
  sources are his.
- **Two endings written as two sheets** → §4; they are Alternate Endings.
- **A historical beat named for its people or places** → §5; the name is
  generic and the history sits beneath it.
- **A beat dropped because fewer than half the sources carry it, when it
  belongs to the theme they share** → §4.
- **A new sheet for a story the core already contains** → §4; it is a Variation.
- **A distinct classic met in research and left unrecorded** → §4; a sheet or
  a card.
- **A story the author disliked used as a source** → §2; it is dropped.
- **A historical sheet and a fiction sheet on one conflict, linked one way** →
  §5.
