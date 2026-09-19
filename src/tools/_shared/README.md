# tools/_shared/

Executable capabilities promoted out of an agent-named folder. Maintained by
`chief_of_staff`; loading is `src/templates/identity_template.md`
§Boundaries and coordination.

## Index

One line per capability, and the condition that calls for it.

- **`originality_scan.md`** — the name, device, phrase and silhouette tests over
  a document or a set of documents, reporting each passage at risk with a
  divergence. Load it when creative material may echo an existing work.
- **`keychain.py`** — a secret read from the operating system's own store at
  the moment a program needs it, and the command that puts one there. Use it
  wherever a tool needs a password, a token or a key: a secret lives in the
  keychain and never in a file, config included.
- **`install_schedule.py`** — one daily program on the schedule the machine runs
  by itself: a launch agent on macOS, a cron line elsewhere. Call it with the
  job's label, its program arguments, its log file and the time of day. Use it
  for any job that should run daily without anyone starting it, so two such jobs
  are two sets of arguments rather than two scripts that drift.

## What belongs here

- **Promote a capability here once a second agent genuinely reuses the same
  shape.** One agent's own script stays in that agent's folder.
- **A folder named for what it does is already shared** — `ticket_tools/`,
  `config_tools/`, `file_management/` and their siblings are reached by name and
  need no promotion. This folder is for a capability whose only home today is an
  agent's own folder.
