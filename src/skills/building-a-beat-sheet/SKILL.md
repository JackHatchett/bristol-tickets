---
name: building-a-beat-sheet
description: Breaks the published stories an author names into beats and merges them into one cited archetype beat sheet, filed in the notebook's beat-sheet library and linked from its hub. Use when a story archetype or plot type is to be broken into beats, or a sheet in that library extended; a scene's beats are prose-drafting's.
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
fortress. Operation: the steps below. Output: one beat sheet in the library and
its line in the library's hub.

Every rule of `src/skills/note-formatting/SKILL.md` holds for the sheet. The
sections below are the sheet's own, and win for those sections by that skill's
first boundary.

## 1. Find the library

- **Read the library's folder from config** — `python3
  src/tools/config_tools/read_config.py markdown_notebook.beat_sheets_dir`.
- **The hub is the note in that folder whose filename starts with `_`.**
- **Read the hub and two sheets already there before writing**, one merged
  from several sources and one from a single source. The library's own sheets
  are the model the new one matches.

## 2. Ask the author

One batch, in the session, before anything is written:

- **Ask which stories he knows that follow the archetype.** His reference
  stories are the sheet's core sources.
- **Offer four to eight candidate sources to jog his memory** — well-known
  stories of the type, each with its year and one clause on why it fits.
- **Ask the clarifying questions the archetype raises**, in the same batch:
  where its boundary lies, whether it has more than one ending, and which
  neighbouring archetype it must be told apart from. Each question offers two to
  four concrete answers with one recommended, by
  `src/skills/designing-with-the-author/SKILL.md` §Who decides what.

## 3. Break each source into beats

- **Write each source's beats in story order**, from the story itself or a
  published synopsis, critique or interview.
- **Cite no informal source** — `src/skills/note-formatting/SKILL.md` §Links.

## 4. Merge the beats

- **A beat is core when most sources hit it in the same relative order.** The
  sheet has as many core beats as the sources share, and no target count.
- **A beat fewer sources hit goes under Optional Beats**, giving the source that
  carries it.
- **A run of several beats one source lays over the core is an Optional Path**
  — the escort in Kurosawa's The Hidden Fortress, laid over beats 4 to 8 of the
  assault. The path states which core beats it spans.
- **Endings that differ on the same beats are Alternate Endings in one sheet.**
- **Two archetypes that share early beats and then diverge are two sheets**,
  each listing the other in its Related Notes. Read the library for a sheet the
  new archetype diverges from before deciding which case it is.

## 5. Write the sheet

- **Filename**: the archetype in snake case, inside the library folder.
- **Frontmatter**: by `src/skills/note-formatting/SKILL.md` §Frontmatter, with
  the tags `ai/answer` and `beat_sheet`, the `status` key the library's sheets
  carry, and `source_url` the source the sheet chiefly rests on.
- **H1**: the archetype's name, then a one-line summary of the whole plot with
  no closing period.
- **`## Details`** holds exactly three bullets, each with nested bullets:
  - Promise to the Reader — what the archetype promises a reader who picks it
    up;
  - Differentiators — what sets it apart from its nearest neighbours, each
    named;
  - Variations — only those of Alternate Endings, Optional Beats and Optional
    Paths that apply; the bullet is left out where none does.
- **`## Beats`** is an ordered list. Each item is the beat's name in Title Case,
  with nested bullets giving what happens in general and then what happens in
  each source.
- **`## Sources Mapped`** is a table with one row per beat and one column per
  source, each cell the source's moment for that beat or "None" with a reason.
  A sheet resting on a single source has no table.
- **`## Links`** holds the source stories. A story with a literature note in the
  notebook — a note tagged `media/` whose alias is its title — is linked to that
  note as `[[filename|Title]]`; any other story by a Markdown link to its outside
  source.
- **`## Related Notes`** closes the sheet: the hub, the sheets it shares beats
  with, and the notes on the method it was built by.

## 6. Link it from the hub

- **Add the sheet's link under the hub's section for its family of
  archetypes** — Heist, Romance, Odyssey.
- **Open a new `##` section where no family fits**, named for the family in
  Title Case.
- **A sub-bullet under the link may give the one fact a reader choosing among
  sheets needs**, such as an Optional Path drawn from another story.

## 7. Report

Give the author the sheet's file and the hub section it went under, in the
session or in the comment of the card that asked for it.

## Failure modes

- **A beat kept because one memorable source has it** → it is an Optional Beat.
- **Beats padded or cut to reach a round number** → §4; the count is what the
  sources share.
- **A sheet written before the author named his stories** → §2 comes first; the
  sources are his.
- **Two endings written as two sheets** → §4; they are Alternate Endings.
