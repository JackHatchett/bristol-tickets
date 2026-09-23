# tools/zotero

**Prerequisite: Zotero, installed locally.** These scripts read and write a
Zotero data directory on the same machine. Without Zotero there is no book
domain, and `librarian` still runs its other collections.

Zotero is the source of truth for book data. `personal.db` holds no book
tables; everything about a book — read, owned, loaned, on a list — is a fact
recorded in Zotero.

The model, because it is not obvious from the collection names. These are the
shipped default names; a user who renames one records the new name in
`/config`:

- **Books I've Read** means *read*, not owned. It is the read set.
- **Owned** is a subset collection of it, built from the **Shelved** tag.
  Ownership is the tag; the collection is a view of the tag.
- **Reading Lists** parents one collection per list. A list is aspirational and
  never adds to Books I've Read.
- **Loaned** holds books currently out, alongside their other memberships.
- The **library** is not "every item in Zotero" — the list collections can hold
  far more titles than the user has read or owns. An item is in the library
  iff it is in Books I've Read or carries an ownership tag.
- Item type is not the test either: a magazine is a `magazineArticle`, which
  has no `numPages` field and uses `pages` instead.

## Why direct SQLite

`zotero_common.py` opens `zotero.sqlite` directly rather than through an API.

Every writer here calls `require_zotero_closed()` and exits with an instruction
rather than writing behind a running Zotero. **Quit Zotero (Cmd-Q) before
running.**

**The gate reads a file rather than a process list.** `zotero.sqlite-journal`
beside the database is the signal, and it is read the same way wherever the
tools run.

Rows written here carry `version=0, synced=0`, the values a local edit not yet
pushed carries. Never invent a version number; that is the server's to
assign.

## Configuration

`ZOTERO_DATA_DIR` — absolute path to the Zotero data directory, resolved from
`config/config.local.json` (`zotero.env`) or the environment. Falls back to
`~/Zotero`, Zotero's own default. No user paths live in `/src`.

## zotero_export.py — the read path

Everything downstream reads through here: the `library.xlsx` snapshot
(`tools/personal_db/render_snapshot.py --domain books`) and anything else that
needs the library as rows.

A reader has no excuse to be unavailable, so this one **copies zotero.sqlite to
a temp file and reads the copy** — safe with Zotero running, and the copy is
removed on the way out including on error. The FIELD MAP at the top of the file
is the authoritative statement of where each of the library's long-standing
columns lives in Zotero; `extra` is the escape hatch for the ones Zotero's
schema has no home for, one `Key: value` per line.

```
python3 zotero_export.py            # TSV to stdout
python3 zotero_export.py --json
python3 zotero_export.py --stats    # the 14 library metrics
```

## The archival copy

A Better BibTeX **auto-export** writes the whole library to
`<PERSONAL_SNAPSHOT_BASE>/library_snapshots/zotero_library.json` in Better CSL
JSON, and BBT refreshes it whenever Zotero changes. That file is the
tool-agnostic archive: plain JSON, readable without Zotero, and it keeps the
`extra` lines (Price paid, Copy, Genre) in each entry's `note`.

It is configured inside Zotero (File → Export Library → Better CSL JSON → Keep
updated), and registered in Zotero's prefs, not here. Nothing in this folder
writes or schedules it; if it ever needs rebuilding, redo that export.

## build_records.py and item_types.json

Turns a reviewed payload into Zotero items in a named collection. A book has an
ISBN, so Add Item by Identifier reaches it; nothing else in this library does,
and everything else is assembled from published sources first and written here
last. The procedure that assembles one is
`src/skills/cataloguing-an-item/SKILL.md`, and the field-by-field template for a
video game is `references/citation_template.md` inside it.

```
python3 build_records.py <payload.json> [more.json ...]
python3 build_records.py --all
python3 build_records.py --dry-run <payload.json>
python3 build_records.py --types
```

**`item_types.json` beside the script is the whole of what the library can
catalogue**, one entry per kind of thing. An entry gives the Zotero item type,
the payload keys that become fields, the keys that become creators and with
which creator type, and which of them are required. Adding a kind is an edit to
that file and none to the script, and `--types` prints what it currently holds.
It ships with `video_game` and `software` (both `computerProgram`), `film`,
`album` (`audioRecording`) and `article` (`journalArticle`).

Payloads live in `data/*/personal/library_records/`, one file per batch:

```json
{
  "type": "film",
  "collection_key": "films",
  "items": [
    {"title": "...", "director": "Fleming, Victor", "date": "1939",
     "url": "https://...", "catalog": "..."}
  ]
}
```

A payload gives its collection by configuration key — `collection_key`, one of
the keys under `zotero.collections` — so a collection can be renamed in one
place. A literal `collection` still wins where one is given, and a payload
giving neither takes the type's own default key where it declares one
(`video_game` declares `point_and_click`). A key with no name configured is
refused, because naming a new collection is the user's.

Behaviour worth knowing:

- **`type` is an entry of the map, and an unmapped one is refused by name**
  along with the list of the mapped ones. A payload giving no type is the type
  whose `payload_key` it carries, which is what keeps a game payload written
  before the map existed running unchanged: `games` is `video_game`'s.
- **Each type's required fields are its own and a payload missing any of them
  is refused** — for a game, title, developer, date, system, url, catalog. A
  record without them is one nobody could check afterwards. Everything else is
  left blank when no source states it.
- **An entry key the type does not carry is refused rather than dropped**, so a
  field spelled for the wrong kind of thing is caught before it is written. A
  key starting with `_` is a note to a human reader and is ignored.
- **Four keys are the same on every type and are not in the map** — `date` and
  `accessed`, which carry Zotero's own date formats; `extra`, one `Key: value`
  line each; and `tags`.
- **A title already in the library as an item of the same type is reused**, and
  only its collection membership is added. Nothing is overwritten, so a payload
  can be corrected and replayed.
- **A creator slot takes one name or a list of them.** `Last, First` is a
  person; a name with no comma is stored single-field, which is how Zotero holds
  a studio or a label. A game's `developer` is stored as `programmer`, which is
  what makes a citation render it as the author, and `company` holds the
  publisher.
- **`programmingLanguage` is never written.** On a Software item that field
  means the language the program was written in; the language it is played in is
  `Language: en` in `extra`. A film, an album and an article have a real
  `language` field, and the map sends `language` there.
- `--dry-run` opens the database read-only and reports what it would create and
  what it would reuse, so a payload can be reviewed with Zotero still open.

## build_reading_lists.py

Turns a published reading list into a Zotero collection.

```
python3 build_reading_lists.py <payload.json> [more.json ...]
python3 build_reading_lists.py --all
python3 build_reading_lists.py --dry-run <payload.json>
```

Payloads live in `data/*/personal/reading_lists/`. One file per list:

```json
{
  "collection": "Modern Library 100 Best Novels",
  "source": "https://sites.prh.com/modern-library-top-100",
  "source_note": "which edition, what was included, what was left out",
  "stated_count": 100,
  "entries": [
    {"title": "Ulysses", "author": "Joyce, James"},
    {"title": "The Reivers", "author": "Faulkner, William", "date": "1963",
     "note": "goes into the item's Extra field"}
  ]
}
```

Authors are `Last, First`. A name with no comma is stored as a single-field
name, which is how Zotero itself holds "Ovid" or "Anonymous".

Behaviour worth knowing:

- **An entry the library already holds is reused, not recreated.** Matching
  needs title *and* author to agree: exact, then subtitle-stripped, then
  library-title-starts-with-list-title. An entry with no author never matches —
  a bare title is too weak a key to merge on.
- **Nothing is ever added to "Books I've Read".** A list is aspirational; the
  read collection is a fact about the user. The script refuses a payload that
  gives it.
- **Re-running is safe.** An existing collection is reused and only missing
  entries are added, so a payload can be corrected and replayed.
- `--dry-run` opens the database read-only and reports reuse and create counts,
  so a payload can be tuned with Zotero still open.

## build_reading_list_notes.py

Turns each reading-list collection into a Markdown checklist note in the
notebook's inbox, so a list is worked through without opening Zotero. Every line
carries the title, the author and a `zotero://` link to that item.

```
python3 build_reading_list_notes.py [--dry-run] [--out-dir PATH]
```

- **A reading list is any collection holding at least one book**, minus the read
  set and the ownership view. That rule keeps clipping collections out without
  listing any.
- **A book already read is ticked when its line is first written.** After that
  the note is the user's: a re-run preserves every tick and untick.
- **A re-run only appends lines new to the list**, and deletes only a line whose
  item has left the collection.

The notes directory resolves from `READING_LIST_NOTES_DIR`, then
`markdown_notebook.notes_dir` and the inbox below it; `--out-dir` overrides
both.
