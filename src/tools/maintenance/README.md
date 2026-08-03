# Maintenance

Scheduled upkeep. Diagram generation is the whole of it.

**Backups belong to the operating system.** This folder holds no backup mirror,
no drift detector and no mirror-log digest. A source falling outside the
machine's own backup coverage is fixed in that tool's exclusion list, never by a
second backup tool here.

## Tools

### build_diagrams.py

`python3 build_diagrams.py [<config.local.json>] [--check]` — writes
`agents.mmd` and `infrastructure.mmd` into
`data/<instance>/system/diagrams/`, rendering the config's agent and
infrastructure blocks as Mermaid. Pure Python; no `mmdc` or node dependency. The
config path defaults to `config/config.local.json` resolved from the script's own
location, and an explicit path overrides it. `--check` writes nothing, printing
the drifted filenames and exiting 1 when a file on disk differs from what the
config now implies.

### run_diagrams.sh

`./run_diagrams.sh [args]` — runs `build_diagrams.py` from this folder, passing
its arguments through.

## Scheduling

A launchd job may drive `run_diagrams.sh` on a cadence, logging to
`data/<instance>/system/logs/`. Point the job at a path that exists.
// launchd fails silently when a job's target script has moved.
