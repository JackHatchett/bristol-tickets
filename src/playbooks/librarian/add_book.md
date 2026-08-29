# add_book — librarian playbook

Getting books into the library. **Zotero is the library**: a book is added in
Zotero, and nothing outside Zotero holds book data. Safety gates and field
conventions are `playbooks/librarian/data_safety.md`.

## Preconditions

- **`ZOTERO_DATA_DIR` resolves to a real Zotero data directory.** Where it does
  not, stop and say so rather than guessing a path or fabricating a write
  location.
- **Zotero is quit before any path that writes `zotero.sqlite`.** The tools
  refuse to run while it is up. Reading never needs it.

## The three add paths

1. **By identifier — the normal case.** Zotero's Add Item by Identifier (the
   magic-wand button) takes an ISBN, DOI, PMID or arXiv ID and pulls a full
   catalogue record, which beats anything a re-keyed CSV produces. **Prefer this
   whenever the user has the book in hand.** It is a UI action, so it belongs to
   the user or a computer-use session rather than a script.

2. **A whole reading list —** `tools/zotero/build_reading_lists.py`. One JSON
   payload per published list; the script makes the collection and fills it,
   reusing a library item wherever the entry matches one. Payload shape and
   matching rules: `tools/zotero/README.md`. **Never add a list entry to "Books
   I've Read"** — a list is aspirational, the read collection is a fact about
   the user.

3. **A reading-app export.** Zotero imports CSV, RIS and BibTeX directly
   (File → Import), and the major reading apps all export CSV. **Use Zotero's
   importer rather than writing one**; a bespoke parser writing into
   `zotero.sqlite` would duplicate what Zotero already does, duplicate detection
   included.

**Resolve an image or a vague reference before using any path.** A screenshot, a
photo of a shelf or "that book about X" is not an input to the paths above: read
the image or reason out the reference, confirm title and author with the user,
find the ISBN, then use path 1. **Never fabricate metadata to fill a field** —
leave it blank, because a guessed identifier gets trusted once it is read back.

## Field conventions

The snapshot's columns map onto Zotero fields; the map at the top of
`tools/zotero/zotero_export.py` is the reference for where Copy, Price paid,
Genre, Shelved and Signed now sit. `extra` is Zotero's escape hatch, one
`Key: value` per line, and holds the non-bibliographic columns rather than a
new item type. The edition convention table is in `data_safety.md`.

## Tools

- Zotero itself — Add Item by Identifier, File → Import
- `tools/zotero/build_reading_lists.py` — a published list as a collection
- `tools/personal_db/render_snapshot.py --domain books` — regenerates the
  library xlsx from Zotero; safe to run with Zotero open

## Logging

**Routine entry is not a tracked task and gets no card.** Open one via
`ticket_write.py add-task` against this agent's epic only for something bigger
than routine entry, such as auditing a whole column.

## Failure modes

- **No Zotero database at the resolved path** → stop and report the exact path
  checked. Never fall back to writing a spreadsheet directly.
- **A writer exits with "Zotero is running"** → that is the tool working. Ask
  the user to quit Zotero; never work around it.
- **An entry with no author** → a bare title is too weak a key to merge on, so
  the honest outcome is a new item and Zotero's duplicate pane afterwards.
