---
name: syncing-the-plot-alignment-sheet
description: Carries changes between a novel's tiered plot notes and the plot alignment sheet - one column per plot, beats down the column - so that the notes hold every word and the sheet keeps the author's arrangement of where each beat sits. Use when the author asks for a sync, sends notes or a revised copy of the sheet, comments on the sheet, or when the sheet is to be rebuilt or given a new tab.
license: MIT
compatibility: Runs where the Markdown notebook is reachable; needs python3 and a Google Sheets connector.
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.scripts: src/tools/writing_tools/plot_alignment.py
  bristol.subtitle: Keep the plot alignment sheet in step with the plot notes
---
# syncing-the-plot-alignment-sheet

Input: a change to a novel's plot, arriving by one of the routes below.
Operation: the change written into the plot notes, then carried into the
sheet. Output: notes and sheet saying the same words, with every beat the
author has placed still on its row.

The sheet's location, the plot folder and each tab's outline and dividers are
config, `agents.writers_room.plot_alignment`; `plot_alignment.py` reads them.
The shape of the notes themselves is
`src/skills/placing-plots-in-the-outline/SKILL.md`.

## Who owns what

- **The notes hold every word in the sheet**: each title, promise and beat.
  A word changes in the notes first, and the sheet follows.
- **The arrangement is the author's**: which row a beat sits on, the blank
  rows and cells he leaves, and the order and width of the columns. A sync
  never moves a placed beat, a column or a row he made.

## How a change arrives

- **An edit in the notes**, made by the author or by a session on his word.
  Sync (§Sync).
- **A note of bullets in the inbox**, written away from the notes. Apply each
  bullet to the plot sheet it concerns by
  `src/skills/placing-plots-in-the-outline/SKILL.md`, ask him about any bullet
  that fits no sheet, sync, and move the note into the archive folder
  (`markdown_notebook.archive_dir`) once every bullet is in the notes.
- **A comment on a cell of the master sheet**, for a small change. Read the
  comments (`get_spreadsheet` with comments included), write each into the
  notes as above, sync, and tell the author which comments are carried, so
  each can be resolved.
- **A revision copy of the sheet**, for a big pass. Read the copy beside the
  master, column by column: a word changed, added or removed is written into
  the notes; a beat he moved keeps the copy's row. Then sync the master, carry
  each moved beat to its row in the copy, read the master against the copy,
  and move the copy to the Drive trash once the two agree.
- **Read the delta back into the notes before the master is touched**, by
  every route. A sync carries nothing from the sheet to the notes.

## Sync

1. **Read each tab the change touches**, from A1 to its last used cell, with
   the Sheets connector's `get_values`, and write the values into a JSON file
   in the scratchpad as `{"<tab>": [[row], ...]}`.
2. **Run `python3 src/tools/writing_tools/plot_alignment.py sync <file>`.** It
   matches each column to its plot by the title's link or its title, and each
   placed beat to the plot's beats by column and order down the column. It
   prints the writes and a report:
   - `set` — a cell's new text: a changed title, promise or beat, rewritten in
     place;
   - `clear` — a beat the notes no longer hold, emptied where it sits;
   - `set` for a new beat — the first empty cell below the beat before it,
     above the beat after it and inside its divider band;
   - `insert_row` — where no such cell exists: a blank row inserted across the
     whole tab at that 1-based row before the `set` that follows it, so every
     column moves down together and no alignment changes;
   - `add_column` — a plot the outline newly links, inserted after the last
     column of its group, with its title, promise and beats packed from the
     top of each band, formatted as its neighbour;
   - `remove_column` — a plot no outline links any longer.
3. **Apply the writes in the order printed**, with `update_values` for `set`
   and `clear` and `insert_dimension` for `insert_row` and `add_column`. A
   title is written as the `HYPERLINK` formula the write gives.
4. **Read the tab again and run the sync once more**; it prints no writes when
   the sheet and the notes agree.
5. **Give the author the report**: every row inserted, every column added or
   removed, and every beat whose book tag now belongs to another band than the
   one it sits in. Moving that beat is his.

## How the sheet is generated

`python3 src/tools/writing_tools/plot_alignment.py build [--tab <title>]`
prints each tab as a fresh build writes it. Rebuild a tab, or build one for a
new outline, from that output and the rules below; a rebuild replaces the
author's arrangement, so it is done only on his word.

- **One tab per outline**, given in config with its divider bands.
- **A column is every plot sheet the outline links** under Characters, Plot
  and Setting, in link order, from that outline's own tier folder.
- **Columns fall into groups**, left to right, a blank column between groups,
  and a group with no plot left out: Character Arcs, Character Stories,
  Romances and Stories, each first with parallels and then without, then
  Setting Promises.
  - A character arc is a sheet in the tier's `character` folder; a romance one
    in its `romance` folder.
  - A character story is a story sheet linked under Characters; a story is one
    linked under Plot; a setting promise is one linked under Setting.
  - A plot has a parallel when a sheet of the same kind at another tier links
    it, or it links one, in Related Notes.
- **Row 1 gives the group's name**, merged across the group, white bold on
  dark slate, and the group's columns are grouped so they collapse together.
- **Row 2 gives the plot's title** as `=HYPERLINK("obsidian://open?vault=…&
  file=…", "<title>")` to its note, bold on light grey.
- **Row 3 gives the plot's Promise to the Reader**, small grey italic.
  Rows 1 to 3 are frozen.
- **Beats run from row 4**, one per row, in the sheet's order, links shown as
  their text and sub-bullets left out.
- **A beat that is one of the sheet's Seven-Point Highlights opens with its
  label and a colon** — `Hook:`, `Plot Turn 1:`, `Pinch 1:`, `Midpoint:`,
  `Pinch 2:`, `Plot Turn 2:`, `Resolution:` — and conditional formatting
  colours a cell by that prefix.
- **A book plot with no beats of its own takes the beats its cycle or series
  parallel tags with that book**, the tag dropped and the parallel's title in
  brackets after two spaces.
- **A tab with divider bands** — the cycle tab by book, the series tab by
  cycle — gives each band a dark grey row bearing its label, then as many rows
  as its fullest column needs. A beat goes to the band its book tag belongs
  to; an untagged beat follows the beat before it; a column with no tag at all
  goes under No Book Given, the last band.
- **Columns are 210 pixels wide**, text wrapped and set at the top of the cell.

## Failure modes

- **A beat rewritten in the sheet and not in the notes** → §How a change
  arrives; the next sync puts the notes' words back.
- **Beats repacked to the top of a column after a change** → §Sync; a new beat
  takes the gap below its predecessor, or a whole-tab row.
- **A copy deleted before the master agrees with it** → §How a change arrives.

## Audit

**Whether the sync run after the writes prints none, and every beat the author
had placed sits on the row it sat on before.**
