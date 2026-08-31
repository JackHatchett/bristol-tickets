---
name: cataloguing-a-game
description: Turns a named video game into a complete, sourced Zotero record in a collection of its own. Use when a game should go into the library, when a batch of them should, or when a record already there is missing fields.
license: MIT
compatibility: Needs Zotero installed on the same machine, python3, and web access to the game databases the procedure names.
metadata:
  bristol.kind: playbook
  bristol.maintainer: librarian
---

# cataloguing-a-game

Input: a game title, and the release of it the record is about. Operation: the
procedure below. Output: one Zotero `computerProgram` item per game, in the
collection its type belongs to.

A game has no ISBN, so Add Item by Identifier cannot reach one and the record is
assembled from published sources instead. The field-by-field template is
`references/citation_template.md`, and it is shared by every video-game
collection rather than being specific to point-and-click. Safety gates on any
Zotero write: `src/skills/data-safety/SKILL.md`.

## Preconditions

- **`ZOTERO_DATA_DIR` resolves to a real Zotero data directory.** Where it does
  not, stop and report the exact path checked rather than choosing one.
- **Zotero is quit before the write in step 6.** Steps 1 to 5 write nothing and
  run with Zotero open.
- **The collection is named by a configuration key, never by a literal name.**
  `python3 src/tools/config_tools/read_config.py zotero.collections` lists the
  keys; a payload carries the key as `collection_key`. A game type with no key
  yet is a new collection, which is a structural change the user approves
  first.

## The sources, and what each one is for

Consult them in this order. A later source corrects an earlier one only where it
is more specific about the same release; where two disagree about a fact neither
qualifies, record neither and say so.

| Source | What it settles |
| --- | --- |
| The Adventure Game Database — `adventuregamedb.com/g/<slug>` | Identity: title, year, developer, publishers, platforms, and the tag vocabulary. The slug is the full title lowercased with every run of non-alphanumerics as one underscore and apostrophes dropped. |
| MobyGames — `mobygames.com` | The release: which platform got what and when, floppy against CD, credits, the publisher that is not the developer. |
| Wikipedia | The cross-check the first two usually lack: an exact release date, the engine, and where the company published from in the year of release. |
| Home of the Underdogs — `theunderdogs.org/games/<slug>/` | An editorial write-up, where it has a page. Not required; the revived site covers a fraction of what the original did. |
| The Internet Archive — `archive.org` | Where a playable copy is preserved, which is the archive pair in the template. |

**Name in `catalog` whichever source the identity came from**, which is normally
the first of these that held the game.

## Procedure

1. **Fix which release the record is about before gathering anything.** One
   record is one game, and its `system` and `version` name the release it
   describes — the one played or consulted, not the earliest. Every other
   platform becomes an `Also released for:` line, so the choice decides where
   half the facts land.

2. **Read the sources in the order above** and keep, for every field, which page
   stated it. A field two sources disagree on stays blank.

3. **Write the synopsis from the premise, not the plot.** Two to four sentences:
   who the player is, what the situation is, and what makes the game itself
   worth distinguishing. Stop before the puzzles and the ending.

4. **Fill one payload entry per game**, to `references/citation_template.md`.
   Payloads live in `data/*/personal/game_records/`, one JSON file per batch:

   ```json
   {
     "collection_key": "point_and_click",
     "games": [
       {"title": "...", "developer": "...", "date": "...", "system": "...",
        "url": "...", "catalog": "..."}
     ]
   }
   ```

   **Leave a field blank rather than guess it.** A guessed value is read back as
   a fact the next time anyone opens the record.

5. **Have the user read the payload before anything is written.** A dry run
   reports what would be created and what already exists, and opens the database
   read-only, so it is safe with Zotero still up:

   ```
   python3 src/tools/zotero/build_game_records.py --dry-run <payload.json>
   ```

6. **Write, with Zotero quit.** The tool creates the collection if it is absent,
   creates one Software item per new game, and adds each to the collection:

   ```
   python3 src/tools/zotero/build_game_records.py <payload.json>
   ```

   Re-running is safe: a title already in the library as a Software item is
   reused and only its collection membership is added.

7. **Say which fields were left blank and what would fill them.** That is the
   whole handover — the user decides whether a blank is worth chasing.

**Nothing is regenerated afterwards.** The `library.xlsx` snapshot is the book
domain's generated view and has no game columns; running it after a game write
reports the same book figures as before.

## Failure modes

- **A writer exits with "Zotero is running"** → that is the gate working. Ask
  the user to quit Zotero; never work around it.
- **No page on The Adventure Game Database** → try the slug rule again on the
  full title including subtitle, then fall back to MobyGames for identity and
  name it in `catalog`.
- **Two sources give different years** → they are describing different releases.
  Go back to step 1 and say which release the record is about.
- **A developer and a publisher that are the same company** → record it in both
  places. It is the common case for the era and is not a duplication.
- **A payload the tool refuses** → it names the entry and the missing field. A
  record with no title, developer, date, system, URL or catalog is one nobody
  could check afterwards, which is why those six are required.
- **A collection name that is not in configuration** → stop. Naming a new
  collection is a structural change and is the user's.

## Audit

- **Whether every record's `url` still resolves**, since a source page that has
  moved is a citation that no longer checks.
- **Whether items are accumulating in Zotero's Duplicate Items pane**, which is
  where a game entered twice under different titles ends up.
- **Whether any record carries a value no source states.** One is enough to make
  the collection unciteable, because nothing distinguishes it from the rest.
