---
name: data-safety
description: The rules every write to the book library obeys, including quitting Zotero first and what each field is allowed to hold. Use before anything writes to the library, and when a change to its shape is being weighed.
license: MIT
compatibility: Needs python3 and a local Zotero data directory.
metadata:
  bristol.kind: playbook
  bristol.maintainer: librarian
---
# data-safety

The rules that apply to any write against the book library, whichever tool or
path triggers it. The library is Zotero, so these gates are about
`zotero.sqlite`. They bind whenever anything under `tools/zotero/` is about to
write, whenever `tools/personal_db/render_snapshot.py --domain books` is about
to run, and whenever a structural change is being considered.

**Zotero must be quit before any write.** Zotero holds the database open and
keeps state in memory, so a write behind a live Zotero is silently lost or
corrupts the file. Every writer calls `require_zotero_closed()` and exits with
an instruction instead. **Never work around that check, disable it, or make an
exception.**

## What is and is not the library

Zotero holds more than the library: the aspirational reading-list collections
run to thousands of titles the user has neither read nor owns. **An item belongs
to the library only if it is in "Books I've Read" or carries an ownership tag.**
Counting list-only titles as unread library would redefine every metric the
snapshot reports. **Item type is not the test either** — the magazines are
`magazineArticle`, so filtering on `book` alone silently drops them.

The shipped collection layout, whose names a user may change in `/config`:

| Collection | Means |
|---|---|
| Books I've Read | The read set. Membership is the `Read` field, and it says nothing about ownership. |
| Owned | A subset built from the `Shelved` tag. |
| Reading Lists | A parent; each list is its own collection under it, and never adds to Books I've Read. A list is aspirational; the read collection is a fact about the user. |
| Loaned | Books currently out, alongside their other memberships. |

Non-bibliographic values — Copy, Price paid, Genre, `personal.db id` — live in
Zotero's `extra`, one `Key: value` per line.

## Schema — core fields

The authoritative map is the FIELD MAP block at the top of
`tools/zotero/zotero_export.py`; this table is the human summary.

| Field | Required | Notes |
|-------|----------|-------|
| Author | Yes | Zotero creators, `Last, First`. A mononym or institution is a single-field name (`fieldMode=1`), not `Ovid, ` |
| Title | Yes | Full title including subtitle |
| Publisher | No | Full publisher name |
| Edition | No | The format/medium field — extra `Copy: …`, else Zotero's `edition` |
| Signed | No | The tag `Signed copy` |
| Genre | No | extra `Genre: …` if present, else the item's genre tags joined |
| Pub Date | No | Zotero `date`; the snapshot takes the year |
| Page Count | No | `numPages`, or `pages` for `magazineArticle`, which has no numPages field |
| Price Paid | No | extra `Price paid: …`; blank for unknown, gift or subscription |
| Read | No | Membership of the "Books I've Read" collection |
| Shelved | No | The tag `Shelved` — ownership. `Not shelved` is its explicit negative |

**Edition convention:**

| Format | Value |
|--------|-------|
| Audiobook, unabridged | `Audiobook - Unabridged` |
| Audiobook, abridged | `Audiobook - Abridged` |
| Kindle / ebook | `Kindle` |
| Physical hardcover | `Hardcover`, or a specific edition where known |
| Physical paperback | `Paperback` or `Trade Paperback` |

**Apply the format convention to new digital and audio entries only.** Older
entries use `Edition` for physical-edition information ("1st Reprint Thus")
rather than format; both uses coexist, and an existing value is preserved as
written.

## Safety gates

1. **Never overwrite an existing backup.** Every write creates a new dated
   version; where one already exists for that date, append a suffix (`_1`, `_2`).
2. **Back up before any bulk or destructive change** — copy `zotero.sqlite` to
   the configured snapshot location first. That location may sit outside the
   data root, so resolve it from `/config` rather than assuming a sub-folder.
   `zotero_common.backup_to_scratch()` gives a within-run rollback point in the
   session scratchpad, which is not the backup this gate means.
3. **A structural change needs the user's approval before executing** — a new
   item type, a renamed collection, anything that changes what a field means.
4. **Never rename the working copy.** It is always the live `zotero.sqlite`;
   dated copies are backups.
5. **Give a one-off special snapshot a descriptive name**, not a date — a
   migration source, a named checkpoint.
6. **Rows written by these tools carry `version=0, synced=0`**, exactly what
   Zotero records for a local edit it has not pushed. Never invent a version
   number; that is the server's to assign.

## Sync targets

There are none, and there is no sync command. The Zotero data directory and the
rolling xlsx snapshots both sit on the internal disk, which the system's own
backup software copies to the external drive. No tool in this project copies
them anywhere. Zotero's own sync to zotero.org is the user's setting rather than
a tool's business. **Resolve every path from `/config`**, and never assume a
path from an old session is current.

## Tools

- `tools/zotero/` — `zotero_common.py` (write layer and the closed-Zotero gate),
  `zotero_export.py` (reads a copy, safe with Zotero open),
  `build_reading_lists.py`, `build_reading_list_notes.py`
- `tools/personal_db/render_snapshot.py --domain books`

## Logging

**A structural change is recorded** — a schema decision, a re-migration, a
sync-target change — as a task via `ticket_write.py add-task`, or as a comment
on the relevant card via `add-issue-log`.

## Failure modes

- **The backup step fails or the backups directory is unreachable** → stop
  before the write rather than writing against an unconfirmed backup state.
- **A writer reports "Zotero is running"** → quit Zotero and re-run. Never open
  the live file for writing yourself.
- **A structural change is requested with no explicit go-ahead** → describe what
  it would take and wait.

## Audit

- **Whether backups are accumulating**, which is the sign the gate is honored,
  or whether write scripts are silently skipping it.
- **Whether the xlsx and Zotero disagree.** The xlsx is generated and never an
  input, so a hand edit to it is already lost.
- **Whether items are accumulating in Zotero's Duplicate Items pane**, which is
  where a title-only match that could not merge ends up.
