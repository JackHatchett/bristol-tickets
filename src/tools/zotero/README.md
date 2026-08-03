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

Zotero exposes no local write API — the local HTTP server is read-only and the
Web API needs a key and a round trip through zotero.org. So `zotero_common.py`
opens `zotero.sqlite` directly.

That is safe only when Zotero is not running. Zotero holds the database open and
keeps state in memory, so a write behind a live Zotero is silently lost or
corrupted. Every writer here calls `require_zotero_closed()` and exits with an
instruction rather than risking it. **Quit Zotero (Cmd-Q) before running.**

Rows written here carry `version=0, synced=0` — exactly what Zotero records for
a local edit it has not yet pushed. The next sync uploads them. Never invent a
version number; that is the server's to assign.

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
  names it.
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
  naming any.
- **A book already read is ticked when its line is first written.** After that
  the note is the user's: a re-run preserves every tick and untick.
- **A re-run only appends lines new to the list**, and deletes only a line whose
  item has left the collection.

The notes directory resolves from `READING_LIST_NOTES_DIR`, then
`markdown_notebook.notes_dir` and the inbox below it; `--out-dir` overrides
both.
