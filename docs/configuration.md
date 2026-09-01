# Configuration

One file holds every choice an installation makes: `config/config.local.json`.
The setup wizard writes it, Bristol Tickets' Settings tab edits parts of it, and
you can edit the rest by hand. It is git-ignored and never published.

`config/config.example.json` is the tracked template — every key the system
expects, filled with obvious placeholders. Copy it if you are setting up by
hand.

## Reading and editing it

```bash
python3 src/tools/config_tools/read_config.py active_agent
python3 src/tools/config_tools/read_config.py important_paths.tickets_db
```

Any dotted key works. `jq` works too — it is ordinary JSON, deliberately, so it
stays diffable and hand-editable. Editing it in a text editor is fine;
Bristol Tickets round-trips the whole document when it saves, so a key it
does not recognise survives.

## Why paths live here rather than in the code

Nothing under `src/` names a real path, a username, or a personal filename, even
as a string literal — that is what makes the repository publishable. The code
refers to your data by generic relative paths like `data/*/tickets/tickets.db`,
where the `*` is your instance folder, and resolves everything through this
file. Anything that cannot be genericised is passed as an environment variable
declared in an agent's `env` block.

Three folders, three rules: `src/` is published, `config/` is git-ignored,
`data/` is git-ignored.

---

## Keys

### `active_agent`

**Required. Default `chief_of_staff`.** The agent slug every runtime uses. Set
it on the board's Settings tab rather than by hand.

A host that takes per-project instructions can override it for its own sessions with an
`agent_override: <slug>` line in its instructions. The override is read-only and
never writes back. `none`, absent, or an unrecognised slug all fall through to
this key.

### `board`

**Required.** How the board behaves. Edited in Bristol Tickets' Settings tab.

| Key | Default | Meaning |
| --- | --- | --- |
| `new_ticket_stage` | `active` | Where a new card lands when `add-task` names no `--stage`: `active` (the To Do column) or `backlog`. It governs every new card, whoever files it and whoever it is for; an explicit `--stage` always wins. |

### `session`

**Required.** How an agent session runs and closes. Edited in Bristol Tickets' Settings
tab.

| Key | Default | Meaning |
| --- | --- | --- |
| `work_whole_queue` | `true` | `true` or `false`. When a session is told to continue, `true` works its queue top to bottom and halts on room; `false` works the next action and stops there. |
| `suggested_commit` | `true` | `true` or `false`. When a session ends having written files inside a git working tree, whatever stopped it, it ends with a copy-paste commit block for them. |

Each value is read at the moment it bites — the scope when a session is told to
continue, the commit offer as the session closes — so a change takes effect on
the next session that reaches that point.

### `appearance`

**Required. Default `warm`.** How Bristol Tickets looks. Edited in its Settings
tab, where the choice applies as it is picked and Save writes it here.

| Key | Default | Meaning |
| --- | --- | --- |
| `scheme` | `warm` | The colour scheme, as a family or a scheme name. |

A family means "follow the OS light/dark setting within it":

| Value | Meaning |
| --- | --- |
| `warm` | The warm orange family, following the OS. |
| `cool` | The cool neutral family, following the OS. |
| `warm_light` / `warm_dark` | Warm orange, pinned. |
| `cool_light` / `cool_dark` | Cool neutral, pinned. |

An unrecognised value falls back to `warm`. Adding a scheme is a data change in
`src/tools/bristol/ui/theme.py`; what each key in one means is
`src/tools/bristol/ui/README.md`.

### `sizing`

**Required.** What a card's S/M/L/XL estimate is measured against.

| Key | Meaning |
| --- | --- |
| `usage_window` | Your plan's budget in plain words. Agents read this string rather than assuming any vendor's limits. |
| `notes` | Free text. |

The scale itself does not vary per installation.

### `important_paths`

**Required.** Repository-relative paths to the databases.

| Key | Meaning |
| --- | --- |
| `tickets_db` | `data/<instance>/tickets/tickets.db`. Required — every session reads it. |
| `personal_db` | `data/<instance>/personal/db/personal.db`. Only meaningful with the `personal_db` block below. |

### `skills`

**Optional.** Where a third-party Agent Skill is installed.

| Key | Meaning |
| --- | --- |
| `install_dir` | `data/<instance>/skills`. Read by `src/tools/skill_tools/skills.py`. Absent means only `src/skills/` is loadable. |

### `agents`

**Required.** One entry per agent, keyed by slug.

| Key | Meaning |
| --- | --- |
| `identity` | Required. Repository-relative path to the charter. Read at every session start. |
| `description` | The one line the setup wizard's agent list and `docs/agents.md` show. |
| `key_context_files` | Files this agent reads on sight. Declarative. |
| `key_data_paths` | The data folders this agent owns. The setup wizard creates these. |
| `env` | Environment variables this agent's tools expect. |
| `notebook_access` | `{ "read": bool, "write_zones": [ … ], "archive_moves": bool }` — which zones of your notebook this agent reaches. The zone names are `workspace` and `inbox`; an empty list is an agent that reads your notebook and never writes in it. |
| `skills` | The skills attached to this agent, by name, in the order a session matches them. A skill named by no agent is available to every agent. Set it with `skills.py attach` and `detach` rather than by hand. |

An agent whose tools need a value no other agent has declares its own key beside
these. `teaching_assistant` has one, `lesson_pipeline.stages`, which routes each
stage of lesson production to whoever runs it;
`src/skills/lesson-pipeline/SKILL.md` states the legal values
and which stage takes none.

**A fact about an agent goes here or in its charter, never both.** The test and
what each field costs are `src/templates/identity_template.md` §What an agent is
made of.

Delete an agent's entry to remove it from the fleet; add one, with a charter, to
introduce your own.

### `markdown_notebook`

**Optional.** A folder of Markdown notes you edit yourself, outside the
repository. Delete the block if you do not keep one.

Access is granted by zone rather than one bit per agent. `workspace_dir` and
`inbox_dir` are writable in full; `archive_dir` takes files moved in from one of
them and nothing else; every other top-level folder is yours to author, and a
fact whose home is one of them reaches you as a summary in `agent_output_dir`.
Which zones a given agent reaches is its `notebook_access`.

| Key | Meaning |
| --- | --- |
| `notes_dir` | The notebook root. |
| `workspace_dir` | The agent workspace. Writable, and the other keys below sit inside it. |
| `inbox_dir` | Your capture inbox. Writable. |
| `assistant_prompts_dir` | The notebook assistant's custom-prompt notes. Inside `workspace_dir`, and it must match the assistant's own prompts-folder setting. |
| `archive_dir` | Where an agent may move a file from a writable zone. |
| `courses_dir` | Where `teaching_assistant` writes courses. |
| `recipes_dir` | Where `librarian` keeps recipes. Read-only, like everything you author. |
| `agent_output_dir` | Where agents drop drafts for you to review. |
| `reports_dir` | Where Clear Done writes its report. Falls back to the `BRISTOL_REPORTS_DIR` environment variable, then a local pointer file, then skips the report. |
| `plans_dir` | Where a planning document goes. |

### `zotero`

**Optional.** Needed only for `librarian`'s book domain. Absent, the Zotero
tools fall back to `~/Zotero`.

| Key | Meaning |
| --- | --- |
| `env.ZOTERO_DATA_DIR` | Your Zotero data folder. |

### `personal_db`

**Optional.** A single SQLite database of personal tracking, one table per
domain. Absent, the tools discover `data/*/personal/`.

| Key | Meaning |
| --- | --- |
| `env.PERSONAL_DB_DIR` | Where the database lives. |
| `env.PERSONAL_DB_FILENAME` | Its filename. |
| `env.PERSONAL_SNAPSHOT_BASE` | Where snapshots are written. |

### `drives`

**Optional.** Named roots outside the project. Only `external1.path` is read by
code — the photo tools, which exit with a clear message when it is absent. The
rest are reference entries agents can consult. Delete any drive you do not have.

| Key | Meaning |
| --- | --- |
| `<name>.path` | Absolute path to the root. |
| `<name>.tags` | Free-form labels. |
| `<name>.notes` | Free text. |

### `code_projects`

**Optional.** Application code held as instance data, stewarded by
`game_designer`.

| Key | Meaning |
| --- | --- |
| `root` | The folder holding every project. |
| `projects.<slug>` | One entry per project: `path`, `status`, `owner`, `notes`. |

### `projects`

**Optional.** Two lists: `local_projects`, repository-resident project folders,
and `notebook_projects`, notebook folders an agent should treat as a project
rather than as loose notes.

### `governance`

**Required.** Free-text statements about who decides what. Agents read these as
context.

| Key | Meaning |
| --- | --- |
| `real_world_roles` | Which AI is the architect of this system and which are consultants whose output is advice. |
| `code_projects_layer` | Who stewards `data/*/code_projects/` and on what terms. |
| `project_local_nicknames_caveat` | Any word one of your projects uses in a sense that differs from this file's. |

### `keyword_scan`

**Required.** Settings for the sweep that checks the tree for personal data
before anything is published (`src/tools/file_management/keyword_scan.py`).

| Key | Meaning |
| --- | --- |
| `keywords` | Your own name and usernames. |
| `exclude_suffixes` | File extensions to skip. |
| `exclude_prefixes` | Directory name prefixes to skip. |

### `tools`, `skills`

**Required.** Each holds a `root` path and a `files` list. The roots point at
`src/tools/` and `src/skills/`. `skills` also holds `install_dir`, the root a
downloaded skill lands in.

### `stack`

**Optional.** A reference block binding stable roles to whichever tool currently
fills them, so a charter names a role and this file names the tool.

| Key | Meaning |
| --- | --- |
| `external_agent_roles.<role>` | `collaborator` (the tool), `surface` (where it runs), `owner` (the agent that owns the routing decision), `trigger`, `notes`. |
| `ai_collaborators` | Which AI services you use and for what. |
| `creative_art_production`, `development`, `notes_knowledge_storage` | Free-form inventories of your tooling. |

---

## Where the code looks for your installation

Every resolver — the tickets database, the reports directory, the config file —
follows one order:

1. An explicit environment variable (`TICKETS_DB`, `BRISTOL_REPORTS_DIR`).
2. The instance pointer at `~/Library/Application Support/BristolTickets/instance.json`
   (`$XDG_CONFIG_HOME/BristolTickets/instance.json` off macOS), which names the
   data root and instance slug.
3. A legacy single-line pointer file next to the tool.
4. Discovery: walk up the source tree to `src/app.md` and search
   `data/*/tickets/tickets.db`.

Running from the repository needs no pointer; step 4 finds everything. A
standalone app is relocatable and cannot see the repository, so write one:

```bash
python3 src/tools/config_tools/instance_pointer.py --write
```

The pointer lives outside the repository, so it can never be committed.
