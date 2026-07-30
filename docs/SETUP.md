# Setup — getting a clone of `Bristol Tickets` running locally

This fills in the `README.md` "Getting Started" stub. It's written for a
fresh clone on macOS (the only platform this has actually been run on so
far — flag it if you're setting up elsewhere and hit something
macOS-specific below).

## 1. Python

Developed against **Python 3.10**. No lower bound has been tested.

## 2. Install the Python dependencies

```bash
pip install -r requirements.txt
```

On a Homebrew-managed macOS Python, `pip` may refuse a system-wide install;
add `--break-system-packages`, or use a virtualenv instead (`python3 -m venv
.venv && source .venv/bin/activate` first).

## 3. Post-install steps `requirements.txt` can't cover

A couple of packages need an extra step beyond `pip install`, and one tool
isn't a Python package at all:

- **Playwright** (used by `src/tools/jd_scraper/`) needs its browser binary
  downloaded once:
  ```bash
  playwright install chromium
  ```
- **ocrmypdf** (used by `src/tools/document_tools/pdf_to_markdown.py`) is
  pip-installable, but it shells out to **Tesseract** and **Ghostscript** at
  runtime — pip doesn't install those:
  ```bash
  brew install tesseract ghostscript
  ```
- **`pdftotext`** (also used by `pdf_to_markdown.py`, via `subprocess`) isn't
  a pip package at all — it's part of **poppler**:
  ```bash
  brew install poppler
  ```

## 4. Gmail API credentials (only if using `jd_scraper/gmail_harvest.py`)

That script needs a Google Cloud OAuth credential file and a one-time
browser consent flow. See `src/tools/jd_scraper/README.md` for the full
walkthrough — not duplicated here since it's specific to one tool, not the
whole app.

## 5. Configuration

The contents of `config/` are git-ignored (see `.gitignore`) except for the
shipped template. Two files:

- `config/config.example.json` — the tracked template. Every key the system
  expects, filled with obvious placeholders (`/path/to/...`,
  `<your-instance>`). Blocks a given install may not need — `drives`,
  `markdown_notebook`, `personal_db`, `zotero`, `code_projects`, `projects`,
  `stack` — say OPTIONAL in their notes and can be deleted; the tools that
  read them fall back or exit with a clear message.
- `config/config.local.json` — the single structured source of truth for the
  whole system, and the file you actually run on. It resolves the generic
  paths the tracked `src/` code uses (e.g. `data/*/tickets/tickets.db`, "the
  active project") to your actual drives, directories, and agent registry. It
  also carries `active_agent` (which agent is active on launch), a
  `keyword_scan` block (settings for
  `src/tools/file_management/keyword_scan.py`), and a `stack` block (your
  personal software and tooling, which agents may need to recall).

Create it by copying the template and replacing every placeholder:

```bash
cp config/config.example.json config/config.local.json
```

Read individual fields without opening the whole file:

```bash
python3 src/tools/config_tools/read_config.py active_agent
python3 src/tools/config_tools/read_config.py important_paths.tickets_db
jq -r '.drives.external1.path' config/config.local.json   # jq works too
```

### How the repo is laid out (config routing model)

The Claude session (`src/app.md`), the standalone tools under `src/tools/`, and
external **AI consultants** (Copilot/Gemini) share one data+config layer. What
keeps `src/` publishable is the folder split:

- **`src/` — GitHub-safe.** Operational logic only: no personal data, no
  absolute user paths, no usernames, not even as string literals. It refers to
  user data by *generic relative* paths (`data/*/tickets/tickets.db`, where `*`
  stands in for the git-ignored instance folder). Personal filenames that can't
  be genericized are resolved through env vars declared in the config
  (`agents.*.env`).
- **`config/` — git-ignored.** The single `config.local.json`.
- **`data/` — git-ignored.** The instance's real data, including the
  state-bearing `tickets.db`.

Config is JSON (never YAML — an external consultant, Copilot, can't work with
YAML; never SQLite — config must stay git-diffable and hand-editable). SQLite is
reserved for high-volume keyed *state* (`tickets.db`).

### Overriding the active agent per Cowork session

`active_agent` in `config.local.json` is the default role for *every* runtime —
offline work reads it and nothing overrides it. A Cowork session additionally
honors a session-scoped override: if the launching
project instructions carry a line `agent_override: <slug>` with a value other
than `none`, that slug becomes the active agent for that Cowork session only
(see `src/app.md` Phase 2, step 1). The override is read-only — it never writes
back to config — so it can't leak into offline runs. Use it
to point a given Cowork project at a specific agent (e.g.
`agent_override: teaching_assistant`) without disturbing the system-wide
default. `none`, absent, or an unrecognized slug all fall back to
`active_agent`.

## 6. Initialize the tickets database

```bash
python3 src/tools/ticket_tools/create_tickets.py --instance <your_instance_name>
```

This creates `data/<instance>/tickets/tickets.db` with the base schema
(`theme`, `epic`, `scope`, `task`, `task_meta`, `issue_log`, `task_event`) and
seeds a starter epic. The `attachment` and `task_link` tables are created on
first use by Bristol's schema guard and by `ticket_write.py`, so a fresh DB
self-completes rather than needing a migration step. `data/` is entirely
git-ignored — this is real per-instance state, not something the public repo
ships with either.

## 7. Run something

- **The Claude session**: point a Cowork session at this folder; it reads
  `src/app.md` and takes it from there.
- **Bristol**: `python3 src/tools/bristol/app.py` — a PySide6 Kanban GUI over
  `tickets.db`.
