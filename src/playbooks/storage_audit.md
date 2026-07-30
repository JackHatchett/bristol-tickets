# Storage Audit — Cleanup Inventory & Process

**Cadence:** Monthly (or anytime a drive is getting full)
**Logging:** After completing each audit, log a summary via `tools/ticket_tools/ticket_write.py add-task` against the shared tickets.db — never a markdown state file.

---

## Storage Locations to Audit

### 1. Gmail (Google)
**Why it fills up:** Large attachments accumulate silently. Gmail counts against Google One quota.
**How to optimize:**
- Open: https://one.google.com/storage → "Free up account storage" → guided cleanup of Gmail
- Or in Gmail: search `has:attachment larger:5mb` → review and delete
- Empty Spam and Trash after cleanup
**Who does it:** the user manually (Gmail MCP can help identify large threads)
**Frequency:** Quarterly, or when Google One storage > 70%

### 2. Google Drive
**Why it fills up:** Old drafts, duplicate exports, staging files from projects.
**How to optimize:**
- https://drive.google.com → Storage → sort by size → delete large unused files
- Empty GDrive Trash (auto-empties after 30 days, but manual is faster)
- Check for duplicate copies of any living tracker files
**Folder structure:** the user's Drive has its own designated top-level structure (travel, personal/health, finance, employment, legacy/archive categories, shared budget or planning docs, etc.) — do not reorganize it; treat the current layout as green-lit and out of scope for this audit beyond size checks. Any third party's personal or health-related files that appear here are out of scope entirely — audit for size only, never open or summarize their contents.
**Who does it:** the user manually (no MCP delete tool)
**Frequency:** Quarterly

### 3. Google Photos
**Why it fills up:** Original quality uploads count against Google One quota.
**How to optimize:**
- https://photos.google.com → Utilities → Free up space (removes already-backed-up originals from device)
- Check for trash (auto-empties after 60 days)
- Review shared albums — anything inbound that should route to the configured backup drive?
**Current structure:** Shared albums only (social layer). No full archive here.
**Who does it:** the user manually
**Frequency:** Quarterly

### 4. OneDrive (Microsoft 365)
**Why it fills up:** Mirror accumulation, a pending-review mirror folder not yet deleted, version history.
**How to optimize:**
- https://onedrive.live.com → right-click storage bar → Manage Storage
- Delete the pending-review mirror folder (only after confirming the primary backup drive is current)
- Empty OneDrive Recycle Bin
- Version history: Settings → Options → Version history
**Who does it:** Mix — some Claude (via scripts), some the user (UI deletes)
**Frequency:** Quarterly for general cleanup; one-time legacy-mirror cleanup is a standing follow-up until confirmed done

### 5. iCloud
**Why it fills up:** iCloud Drive accumulation, old device backups, Photos if enabled.
**How to optimize:**
- System Settings → Apple ID → iCloud → Manage Storage
- Delete old device backups (Settings → iCloud → Manage Account Storage → Backups)
- Review the iCloud Downloads folder (resolved via the configured iCloud drive root)
**Current designated use:** one small identity-documents zone (the user manages). Everything else should move out.
**Who does it:** the user manually
**Frequency:** Annually (iCloud is lean by design)

### 6. Mac Local Storage
**Why it fills up:** Downloads folder, caches, iOS backups, Xcode data.
**How to optimize:**
- System Settings → General → Storage → built-in recommendations
- Downloads folder — clear anything not needed
- Desktop — temp files, migration artifacts
- Caches — Claude can audit and list largest dirs
- iOS/iPhone backups (via Finder/MobileSync) — often huge
- Empty Trash
**Who does it:** Claude audits, the user decides on deletes
**Frequency:** Monthly for Downloads/Desktop; quarterly for caches/backups

### 7. Configured Backup Drive
**Why it fills up:** pending-review folders, photo intake backlog, old archive content.
**How to optimize (when mounted):**
- Review and delete confirmed pending-review folders after spot-checking
- Process photo intake queue → move processed items to their organized destination
- Check for obvious duplicates in the archive tree
**Who does it:** Claude (once permissions allow it), the user spot-checks
**Frequency:** Quarterly

---

## Reminder System

### Approach: Session check-in + ticket log
Claude checks the shared tickets.db at session start for the age of the last storage-audit task. If none in the past 30 days, flags it. After each audit, log a short summary (what was found, what was cleaned, freed space by service) via `ticket_write.py add-task` — never a markdown state file.

### Monthly automated check (once available)
Will check:
- Mac storage via `df -h`
- Configured backup drive capacity if mounted
- Age of the last logged audit
- Log the summary via `ticket_write.py`

### Google's built-in tool
For Gmail + GDrive + GPhotos storage combined:
**https://one.google.com/storage** → "Free up account storage" walks you through all three in one flow.

---

## Quick Reference: Storage Caps

| Service | Quota | Shared With | Current % |
|---------|-------|-------------|------------|
| Google One | varies | Gmail + GDrive + GPhotos | check one.google.com/storage |
| OneDrive / M365 | varies | OneDrive only | check live.com storage page |
| iCloud | varies | iCloud Drive + Photos + Mail + Backups | check System Settings → Storage |
| Mac SSD | varies | all local apps | check System Settings → Storage |
