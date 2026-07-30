# Playbook: Book Library Safety & Schema Conventions

## Purpose
The rules that apply to any write against the book library, regardless of which
tool or path triggers it: field conventions, backup discipline, and what
requires the user's approval before executing. The library is Zotero;
these gates are about `zotero.sqlite`.

## Preconditions
Applies whenever anything under `tools/zotero/` is about to write, whenever
`tools/personal_db/render_snapshot.py --domain books` is about to run, or
whenever a structural change is being considered.

**Zotero must be quit before any write.** Zotero holds the database open and
keeps state in memory, so a write behind a live Zotero is silently lost or
corrupts the file. Every writer calls `require_zotero_closed()` and exits with
an instruction instead. That check is a gate, not an obstacle — never work
around it, never disable it, never "just this once."

## Schema — core fields
The library's own columns and where they live in Zotero. The authoritative map
is the FIELD MAP block at the top of `tools/zotero/zotero_export.py`; this table
is the human summary.

| Field | Required | Notes |
|-------|----------|-------|
| Author | Yes | Zotero creators, `Last, First`. A mononym or institution is a single-field name (`fieldMode=1`), not `Ovid, ` |
| Title | Yes | Full title including subtitle |
| Publisher | No | Full publisher name |
| Edition | No | The format/medium field — extra `Copy: …`, else Zotero's `edition`. See convention table below |
| Signed | No | The tag `Signed copy` |
| Genre | No | extra `Genre: …` if present, else the item's genre tags joined |
| Pub Date | No | Zotero `date`; the snapshot takes the year |
| Page Count | No | `numPages`, or `pages` for `magazineArticle`, which has no numPages field |
| Price Paid | No | extra `Price paid: …`; blank for unknown/gift/subscription |
| Read | No | Membership of the "Books I've Read" collection |
| Shelved | No | The tag `Shelved` — ownership. `Not shelved` is its explicit negative |

**Edition convention:**
| Format | Value |
|--------|-------|
| Audiobook, unabridged | `Audiobook - Unabridged` |
| Audiobook, abridged | `Audiobook - Abridged` |
| Kindle / ebook | `Kindle` |
| Physical hardcover | `Hardcover` (or a specific edition, if known) |
| Physical paperback | `Paperback` or `Trade Paperback` |

Older entries used `Edition` for physical-edition info (e.g. "1st Reprint
Thus") rather than format — both uses coexist; preserve existing values as
written, only apply the format convention to new digital/audio entries.
A full consistency audit of this field across older rows is a known,
low-priority open item.

## What is and is not the library
Zotero holds more than the library: the aspirational reading-list collections
are ~1,700 titles the user has neither read nor owns. An item belongs to the
**library** iff it is in "Books I've Read" or carries an ownership tag. Counting
list-only titles as "unread library" would redefine every metric the snapshot
has ever reported. Item type is not the test either — the magazines are
`magazineArticle`, and filtering on `book` alone silently drops 89 of them.

## Procedure — safety gates
1. **No overwrites of existing backups.** Every write creates a new dated
   version. If a backup for the same date already exists, append a suffix
   (`_1`, `_2`, …).
2. **Backup before any bulk or destructive change** — copy `zotero.sqlite` to
   the configured snapshot/backup location first. This location may sit outside
   the data root — resolve it from `/config`, don't assume it's a sub-folder.
   `zotero_common.backup_to_scratch()` gives a within-run rollback point in the
   session scratchpad; that is a rollback point, not the backup this gate means.
3. **Structural changes** (new item types, renamed collections, anything that
   changes what a field means) require the user's approval before executing —
   never assumed, never inferred from "it seemed like a good idea."
4. **The working copy is never renamed.** It's always the live
   `zotero.sqlite` — dated copies are backups, not the working file.
5. **One-off special snapshots** (a migration source, a named checkpoint) get a
   descriptive name, not a date.
6. **Rows written by these tools carry `version=0, synced=0`** — exactly what
   Zotero records for a local edit it has not yet pushed. Never invent a version
   number; that is the server's to assign.

## Sync targets
There are none, and there is no sync command. The Zotero data directory and the
rolling xlsx snapshots both sit on the Mac's internal disk, which Time Machine
backs up to the external drive. No tool in this project copies them anywhere; an
earlier `backup_sync.py` that mirrored them onto that same drive was duplication
of Time Machine's work and has been deleted. Zotero's own sync to zotero.org is
the user's setting, not a tool's business. Resolve every path from `/config`;
never hardcode one here and never assume a path from an old session is current.

## Tools Used
- `tools/zotero/` — `zotero_common.py` (write layer + the closed-Zotero gate),
  `zotero_export.py` (reads a copy, safe with Zotero open),
  `build_reading_lists.py`, `build_reading_list_notes.py`
- `tools/personal_db/render_snapshot.py --domain books`

## Logging Requirements
Structural changes (a schema decision, a re-migration, a sync-target change) get
recorded as a task via `roadmap_write.py add-task` (done ones stand as the
record), or noted on the relevant card via `add-issue-log --task-id
--note "..."` — never a markdown changelog in the data root.

## Failure Modes
- Backup step fails or the backups directory isn't reachable → stop before the
  write, don't write against an unconfirmed backup state.
- A writer reports "Zotero is running" → quit Zotero and re-run. Never read
  around the gate by opening the live file for writing yourself.
- A structural change is requested without the user's explicit go-ahead → don't
  execute it; describe what it would take and wait.

## Human Audit Notes
- Whether backups are actually accumulating as expected (a sign the safety gate
  is being honored) or whether write scripts are silently skipping it.
- Whether the xlsx view and Zotero ever disagree — the xlsx is generated and
  never an input; if someone has hand-edited it, the edit is already lost.
- Whether items are accumulating in Zotero's Duplicate Items pane, which is
  where a title-only match that could not merge ends up.
