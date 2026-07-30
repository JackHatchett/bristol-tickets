# Playbook: Add Books

## Purpose
Get books into the library. Zotero is the library — a book is added in
Zotero, and nothing outside Zotero holds book data. This playbook covers the
three add paths and which one to reach for.

## Preconditions
- `ZOTERO_DATA_DIR` resolves to a real Zotero data directory (§2.2 of
  `agent_identities/librarian.md`). If it doesn't, stop and say so rather than
  guessing a path or fabricating a write location.
- Any path that *writes* zotero.sqlite needs Zotero quit — the tools refuse to
  run while it is up, and they are right to. Reading never does.

## The three add paths

**1. By identifier — the normal case, and Zotero's own.**
Zotero's "Add Item by Identifier" (the magic-wand button) takes an ISBN, DOI,
PMID or arXiv ID and pulls a full catalogue record. This beats anything a
re-keyed CSV can produce and is the path to prefer whenever the user has the
book in hand. It is a UI action, so it belongs to the user (or to a
computer-use session), not to a script.

**2. A whole reading list —** `tools/zotero/build_reading_lists.py`.
One JSON payload per published list; the script makes the collection and fills
it, reusing a library item whenever the entry matches one. See
`tools/zotero/README.md` for the payload shape and the matching rules. Nothing
is ever added to "Books I've Read": a list is aspirational, the read collection
is a fact about the user.

**3. A reading-app export.** Zotero imports CSV/RIS/BibTeX directly
(File → Import). Goodreads, StoryGraph and LibraryThing all export CSV. Use
Zotero's importer rather than writing one — a bespoke CSV parser writing into
zotero.sqlite would duplicate what Zotero already does properly, including
duplicate detection.

### If the source is an image or a vague reference
None of the paths above take a screenshot or a description. If the user hands
you a Libby/Audible/Amazon screenshot, a photo of a shelf, or "that book about
X," resolve it first: read the image or reason out the reference, confirm title
and author with the user, then find the ISBN and use path 1. Never fabricate
metadata to fill a field — leave it blank. An item with a guessed identifier is
worse than an item with none, because the next pass will trust it.

## Field conventions
The snapshot columns map onto Zotero fields — the map lives at the top of
`tools/zotero/zotero_export.py` and is the reference for where anything the
library has always tracked (Copy, Price paid, Genre, Shelved, Signed) now sits.
`extra` is Zotero's escape hatch, one `Key: value` per line; the import put the
non-bibliographic columns there rather than inventing item types.
See `playbooks/librarian/data_safety.md` for the edition convention table and
the safety gates.

## Tools Used
- Zotero itself (Add Item by Identifier; File → Import)
- `tools/zotero/build_reading_lists.py` — a published list as a collection
- `tools/personal_db/render_snapshot.py --domain books` — regenerates the
  library xlsx from Zotero; safe to run with Zotero open

## Logging Requirements
No routine per-add logging against `roadmap.db` — this is the agent's default,
non-structural workflow, not a tracked task. Log a task only if the user asks
for something bigger than routine entry (e.g. "audit the whole Edition
column"), via `roadmap_write.py add-task` against this agent's own epic.

## Failure Modes
- No Zotero database at the resolved path → stop, report the exact path
  checked, don't fall back to writing a spreadsheet directly.
- A writer exits with "Zotero is running" → that is the tool working. Ask the
  user to quit Zotero; never work around it.
- An entry with no author does not match an existing item and never will — a
  bare title is too weak a key to merge on, so the honest outcome is a new item
  and Zotero's duplicate pane afterwards.

## Human Audit Notes
- Whether the `Edition` convention stays consistent across older and newer
  entries (a known, low-priority open item).
- Whether the xlsx view and Zotero ever visibly disagree — that would mean a
  `render_snapshot.py` run was skipped or failed silently.
