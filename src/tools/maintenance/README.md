# maintenance — Folder README

Human-facing description of this folder's role in the system.
No user-specific data.
All paths resolved from `config/config.local.json`, never hardcoded.

---

## 1. Purpose and Scope

Scheduled upkeep utilities. Currently that is diagram generation and nothing
else.

**Backups are not this system's job.** The Mac's own Time Machine backs up the
whole disk to the external drive whenever it is connected. This folder holds no
backup mirror, no drift detector, and no mirror-log digest; do not add one. If a
source genuinely falls outside Time Machine's coverage, the fix is Time
Machine's exclusion list (`/Library/Preferences/com.apple.TimeMachine.plist` →
`SkipPaths`), not a second backup tool.

---

## 2. Path Variables (from config.local.json)

RUNTIME_ROOT
CONFIG_ROOT
DATA_ROOT
LOG_ROOT
DIAGRAM_OUTPUT

`drives.external1` is still a live config key, but only because
`src/tools/file_management/` reads the Photos tree on that drive. No
maintenance tool touches it.

---

## 3. Tool Overview

### build_diagrams.py

Generates Mermaid diagram files (`.mmd`) from config.local.json. Pure Python —
no `mmdc`/node dependency.

Outputs: DIAGRAM_OUTPUT

Scheduled by `~/Library/LaunchAgents/com.<user>.diagram-snapshot.plist`,
monthly on the 1st at 09:00, logging to LOG_ROOT then
"diagram_snapshot.log" / ".err".

### run_diagrams.sh

Shell wrapper for build_diagrams.py. Takes no argument — build_diagrams.py
defaults to config.local.json relative to its own location. Pass a path only to
override.

---

## 4. How to Run

    cd <RUNTIME_ROOT>/tools/maintenance
    ./run_diagrams.sh

---

## 5. Human Audit Checklist

Confirm diagram output lands in DIAGRAM_OUTPUT.
Confirm the launchd job still points at a file that exists.
// launchd fails silently when a job's target script has moved.
Update this README when a maintenance tool is added or removed.
