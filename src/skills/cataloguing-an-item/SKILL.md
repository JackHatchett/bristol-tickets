---
name: cataloguing-an-item
description: Turns a named video game, film, album, piece of software or article into a complete, sourced Zotero record in a collection of its own. Use when something that is not a book should go into the library, when a batch of them should, or when a record already there is missing fields.
license: MIT
compatibility: Needs Zotero installed on the same machine, python3, and web access to the databases the procedure lists.
metadata:
  bristol.kind: playbook
  bristol.maintainer: librarian
  bristol.scripts: src/tools/config_tools/read_config.py src/tools/zotero/build_records.py
  bristol.subtitle: Catalogue a game, film or album in Zotero
---

# cataloguing-an-item

Input: what the thing is, and which release or edition the record is about.
Operation: the procedure below. Output: one Zotero item of the type its kind
maps to, in the collection that kind belongs to.

A book has an ISBN, so Add Item by Identifier reaches it and
`src/skills/add-book/SKILL.md` is its route. Nothing else here has one, so the
record is assembled from published sources instead. Safety gates on any Zotero
write: `src/skills/data-safety/SKILL.md`.

## Which kinds exist

`python3 src/tools/zotero/build_records.py --types` prints them: the payload
keys each kind carries, which are required, and which Zotero item type it
becomes. That map is `src/tools/zotero/item_types.json`, and a kind the library
should hold but the map does not is a card for `chief_of_staff` rather than an
edit made here.

A video game's field-by-field template, including the conventions no other kind
shares, is `references/citation_template.md`.

## Preconditions

- **`ZOTERO_DATA_DIR` resolves to a real Zotero data directory.** Where it does
  not, stop and report the exact path checked rather than choosing one.
- **Zotero is quit before the write in step 5.** Steps 1 to 4 write nothing and
  run with Zotero open.
- **The collection is given by a configuration key, never by a literal name.**
  `python3 src/tools/config_tools/read_config.py zotero.collections` lists the
  keys; a payload carries the key as `collection_key`. A kind with no key yet is
  a new collection, which is a structural change the user approves first.

## The sources, and what each one is for

Consult a kind's sources in the order given. A later source corrects an earlier
one only where it is more specific about the same release; where two disagree
about a fact neither qualifies, record neither and say so.

**Video game**

| Source | What it settles |
| --- | --- |
| The Adventure Game Database — `adventuregamedb.com/g/<slug>` | Identity: title, year, developer, publishers, platforms, and the tag vocabulary. The slug is the full title lowercased with every run of non-alphanumerics as one underscore and apostrophes dropped. |
| MobyGames — `mobygames.com` | The release: which platform got what and when, floppy against CD, credits, the publisher that is not the developer. |
| Wikipedia | The cross-check the first two usually lack: an exact release date, the engine, and where the company published from in the year of release. |
| Home of the Underdogs — `theunderdogs.org/games/<slug>/` | An editorial write-up, where it has a page. Not required; the revived site covers a fraction of what the original did. |
| The Internet Archive — `archive.org` | Where a playable copy is preserved, which is the archive pair. |

**Film**

| Source | What it settles |
| --- | --- |
| The Movie Database — `themoviedb.org` | Identity: title, release date, director, production companies, runtime. |
| Wikipedia | The distributor, where it was made, and the release this record is about where a film had more than one cut. |
| The Internet Archive — `archive.org` | Where a copy is preserved, for a film out of copyright or otherwise archived. |

**Album**

| Source | What it settles |
| --- | --- |
| MusicBrainz — `musicbrainz.org` | Identity: title, artist, first release date, and which release group a pressing belongs to. |
| Discogs — `discogs.com` | The pressing: label, catalogue number, format, country and year of the copy the record is about. |
| Wikipedia | Where it was recorded, and the personnel a release does not credit on its sleeve. |

**Software**

| Source | What it settles |
| --- | --- |
| The project's own site or repository | Identity, version, licence and the platforms it runs on. This is the primary source; nothing else outranks it about the program itself. |
| Wikipedia | The developer as an organisation, the release history, and the lineage a project page states nothing about. |
| The Internet Archive — `archive.org` | Where a version no longer distributed is preserved. |

**Article**

| Source | What it settles |
| --- | --- |
| The publication's own page | Everything the record needs: title, author, date, publication, volume, issue, pages, DOI. |
| Crossref — `search.crossref.org` | The DOI and the canonical bibliographic record, where the publication's page is thin or paywalled. |
| The Internet Archive's Wayback Machine | A stable URL for a page that has moved, which is the archive pair. |

**Name in `catalog` whichever source the identity came from**, which is normally
the first of these that held the thing.

## Procedure

1. **Fix which release or edition the record is about before gathering
   anything.** One record is one thing, and the fields that name a release — a
   game's `system` and `version`, a film's cut, an album's pressing, a
   program's version — name the one played, watched, heard or run rather than
   the earliest. Every other one becomes an `Also released for:` line, so the
   choice decides where half the facts land.

2. **Read the sources in the order above** and keep, for every field, which page
   stated it. A field two sources disagree on stays blank.

3. **Write the synopsis from the premise, not the plot.** Two to four sentences:
   what the thing is, what situation it opens in or what problem it addresses,
   and what makes it worth distinguishing from its neighbours. Stop before the
   ending.

4. **Fill one payload entry per item.** Payloads live in
   `data/*/personal/library_records/`, one JSON file per batch, and every entry in
   a file is the same kind:

   ```json
   {
     "type": "film",
     "collection_key": "films",
     "items": [
       {"title": "...", "director": "...", "date": "...",
        "url": "...", "catalog": "..."}
     ]
   }
   ```

   **Take the keys from `--types` and use no others.** A key the kind does not
   carry is refused rather than written, which is what catches a field borrowed
   from another kind of record.

   **Leave a field blank rather than guess it.** A guessed value is read back as
   a fact the next time anyone opens the record.

5. **Write, with Zotero quit.** The tool creates the collection if it is absent,
   creates one item per new entry, and adds each to the collection:

   ```
   python3 src/tools/zotero/build_records.py <payload.json>
   ```

   Re-running is safe: a title already in the library as an item of the same
   type is reused and only its collection membership is added.

   **Go straight to the write.** Nothing is shown to the user first and no
   permission is sought: a payload built from the sources above is either
   accepted or refused by the tool, and a refusal costs a re-run rather than a
   bad record.

   **Reach for a dry run only where this batch gives a reason to** — many
   entries at once, or a title the sources matched loosely. It reports what
   would be created and what already exists, opens the database read-only so it
   runs with Zotero still up, and is read by the session rather than handed over:

   ```
   python3 src/tools/zotero/build_records.py --dry-run <payload.json>
   ```

6. **Say which fields were left blank and what would fill them, and name any
   required field that was filled without a source separately.** That is the
   whole handover, and it reports what was written rather than what was
   proposed — the user decides whether a blank is worth chasing, and an
   assumption he cannot see is one he cannot overrule.

**Nothing is regenerated afterwards.** The `library.xlsx` snapshot is the book
domain's generated view and has columns for nothing here; running it after a
write reports the same book figures as before.

## The extra field

`extra` is Zotero's escape hatch, and the library uses it as one `Key: value`
per line. The keys that earn a line, whatever the kind:

| Key | Holds |
| --- | --- |
| `Also released for` | Every other platform, edition, cut or pressing, semicolon-separated, with years where they differ from the record's date. |
| `Adapted from` | The work this one adapts, with its author and year. |
| `Availability` | How a copy can be had now: `Abandonware`, `Sold on GOG`, `Out of print`, `Streaming`. |

**A kind whose Zotero type has no `language` field carries `Language: en`
here** — `computerProgram` is the one, because its only language field means the
language the program was written in. A film, an album and an article have a real
`language` field and the map sends `language` there.

Add a key only where the fact is bibliographic. A walkthrough, a review, a
design analysis or a full plot summary is a separate document and not a line
here.

## Tags

Tags carry what the collection does not. Take the vocabulary from the source's
own tags rather than inventing one — The Adventure Game Database's for a game,
the genre and style terms of the database that held the thing for anything
else — and keep to the ones that would be used to find it again.

## Failure modes

- **A writer exits with "Zotero is running"** → that is the gate working. Say
  the write did not go through, ask the user to quit Zotero, and run step 5
  again; never work around it.
- **No page on the first source** → try the slug rule again on the full title
  including subtitle, then fall back to the next source for identity and name it
  in `catalog`.
- **Two sources give different years** → they are describing different releases.
  Go back to step 1 and say which one the record is about.
- **A developer and a publisher that are the same company** → record it in both
  places. It is the common case for an older game and is not a duplication.
- **A payload the tool refuses** → it gives the entry and what is wrong: a
  missing required field, or a key the kind does not carry. A record with no
  title, creator, date, URL or catalog is one nobody could check afterwards,
  which is why those are required everywhere.
- **A required field has no source** → blank is not an option there: the tool
  refuses the payload, so pick the most defensible value, note it in that entry
  as an assumption and say what it rests on, and name it in the step-6 handover
  on its own rather than folding it into the blanks. It is one entry's flag, not
  a reason to stop the batch. A game's `system` is where this actually happens —
  a digital-only release or a fan game whose sources name no platform.
- **A collection name that is not in configuration** → stop. Naming a new
  collection is a structural change and is the user's.
- **A kind the map does not hold** → stop and file it for `chief_of_staff`.
  Writing the fields by hand into the nearest kind produces a record whose type
  is wrong, and nothing downstream can tell.

## Audit

- **Whether every record's `url` still resolves**, since a source page that has
  moved is a citation that no longer checks.
- **Whether items are accumulating in Zotero's Duplicate Items pane**, which is
  where a thing entered twice under different titles ends up.
- **Whether any record carries a value no source states.** One is enough to make
  the collection unciteable, because nothing distinguishes it from the rest.
