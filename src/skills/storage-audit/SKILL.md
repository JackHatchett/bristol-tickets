---
name: storage-audit
description: Goes through every place the user keeps files and reports what can be freed, with the findings recorded as a card. Use monthly, or whenever a drive is filling up.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# storage-audit

The recurring pass over every storage location the user keeps, to find what can
be freed. Run it monthly, or whenever a drive is filling.

## Triggering the audit

- **Check the board at session start for the last storage-audit card.** Flag the
  audit when the most recent one closed more than thirty days ago.
- **Record each completed audit as a card** carrying what was found, what was
  cleaned, and the space freed per service.

## What only the user can do

Most of these locations have no delete API. **Audit and report sizes; the user
performs the deletion**, except where a location is named below as scriptable.

## Locations

### Mail

Large attachments accumulate silently and count against the account's shared
quota.

- Search for attachments over a few megabytes, review, delete, then empty Spam
  and Trash.
- The provider's own storage page usually offers a guided cleanup across mail,
  drive and photos together.
- Cadence: quarterly, or once the shared quota passes 70%.

### Cloud drive

Old drafts, duplicate exports and project staging files.

- Sort by size, delete large unused files, then empty the trash rather than
  waiting out its retention window.
- **Treat the existing folder layout as settled** — audit for size only, never
  reorganize it.
- **Audit a third party's personal or health-related files for size only.**
  Never open or summarize their contents.
- Cadence: quarterly.

### Photo service

Original-quality uploads count against the shared quota.

- Use the service's "free up space" utility to drop already-backed-up originals
  from the device, and check its trash.
- Route anything inbound that belongs in long-term storage to the configured
  backup drive.
- Cadence: quarterly.

### Secondary cloud storage

Mirror accumulation, review folders left behind after a migration, and version
history.

- **Confirm the primary backup drive is current before deleting a mirror
  folder.**
- Empty the recycle bin and check the version-history setting.
- Scriptable in part; UI deletes stay with the user.
- Cadence: quarterly.

### Platform cloud storage

Drive accumulation, old device backups, and photos where enabled.

- Manage storage from system settings: delete old device backups, and review the
  downloads folder resolved from `/config`.
- Cadence: annually.

### Local disk

Downloads, caches, device backups and developer-tool data.

- Use the system's own storage recommendations, then clear Downloads and Desktop
  of migration artifacts and temp files.
- List the largest cache and backup directories; the user decides each delete.
- Cadence: monthly for Downloads and Desktop, quarterly for caches and device
  backups.

### Configured backup drive

Review folders, intake backlogs and old archive content.

- Spot-check a review folder before deleting it.
- Process the intake queue into its organized destination, and check the archive
  tree for obvious duplicates.
- Cadence: quarterly, when the drive is mounted.

## Quotas

Every quota here varies by plan, so read the current figure from the service
rather than this file. Mail, cloud drive and the photo service typically share
one quota; secondary cloud storage, platform cloud storage and the local disk
each have their own.
