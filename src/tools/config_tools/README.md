# Config Tools

Three small programs that stand between the tracked, generic `/src` code and one
installation's real paths. Everything user-specific is read from the git-ignored
`config/config.local.json`; nothing here contains a username, a home directory,
or a cloud-provider path.

## The tools

### read_config.py

`python3 read_config.py <dotted.key>` prints one field from
`config/config.local.json`. Agents query single keys — `active_agent`,
`important_paths.tickets_db`, `agents.<agent>.identity` — rather than reading
the file whole. The routing model the config expresses is described for humans
in `docs/SETUP.md` §Configuration.

### instance_pointer.py

States, in one place, the order every resolver follows to find an installation:
an explicit env var, then the per-machine instance pointer, then a legacy
`.local` file, then discovery by walking up to `src/app.md`. `--write` creates
the pointer; bare invocation prints it. Running from the repo needs no pointer;
a relocatable `.app` build does.

### data_paths.py

Resolves declared locations and creates them at the moment of a write.

- `resolve(declared)` — the absolute path a declaration refers to. Reads
  config, touches no disk.
- `ensure_dir(declared)` / `ensure_parent(declared)` — the resolved directory,
  created with its parents. Call immediately before a write.
- `read_dir(declared, pattern="*")` — sorted matches, or `[]` when the
  directory does not exist.
- `ensure_db(path, schema)` — a database with its schema applied, created if
  either is absent.
- `agent_data_paths(slug)` / `ensure_agent_data_paths(slug)` — the
  `agents.<slug>.key_data_paths` an agent declares in config.

## A missing data location is created, never an error

A fresh clone ships `/src` and `/config` and no `/data`. Every location an agent
uses is declared in config long before it exists, so finding one absent is a
normal first state rather than a failure.

- **Resolve every declared location through `data_paths.py`** — never by
  building a path by hand.
- **Create at the moment of the write.** A read of a location that does not
  exist reports an empty result and carries on; it never creates and never
  raises.
- **Create the container and stop.** A new directory stays empty and a new
  database stays row-free. A placeholder file, a sample record, or a README
  explaining the folder is invented content, and inventing content is not
  provisioning.
- **An agent-owned database is provisioned from its schema on first access.**
  The shared `tickets.db` comes from `create_tickets.locate_or_provision()`;
  `personal.db` comes from `personal_db/db_common.py`'s `connect()`. Both apply
  a schema whose every statement is `IF NOT EXISTS`, and neither seeds rows.
