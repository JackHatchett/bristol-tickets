# Install

Download the app, open it, and answer four pages. Then point an agent host at
the folder it made. Everything below the first two sections is for someone who
wants the source instead.

## 1. An agent host

An **agent host** is the AI application a session runs inside. Bristol needs one
that does three things:

- **Loads per-project instructions every session**, so `src/app.md` is read
  without you pasting it each time.
- **Reads and writes a folder you choose**, which is where this repository and
  your data live.
- **Runs `python3` in that folder**, which is how every tool here executes.

That is the entire mechanism by which an agent does anything: there is no
server, no API key in a config file, no background process. Bristol names no
vendor in any file it runs on — the host is named once, in the entry file that
host reads, and nothing else branches on it.

**Cowork**, a mode in the Claude desktop app, is the host Bristol has been run
on. It is not on the free tier; check the plan comparison. Any other host
meeting the three requirements should work and has not been tried — coding
agents that read an `AGENTS.md` are the obvious candidates.

Where the host cost falls, and what it costs you:

| The host does | Bristol without it |
| --- | --- |
| Nothing — no host at all | A working solo Kanban app. Every reference in this manual to an agent doing something does not apply. |
| Everything but per-project instructions | Works, but starting a session means typing "read src/app.md" yourself, and `agent_override` has nowhere to live. |

## 2. Pointing the host at this folder

Each host reads a different entry file, and this repository carries one for each
so the host finds `src/app.md` on its own:

| Entry file | Read by |
| --- | --- |
| `AGENTS.md` | Most coding agents and desktop AI apps |
| `CLAUDE.md` | Claude Code |
| pasted project instructions | Cowork — see `src/host_notes/cowork.md` for the text |

Each says the same two lines: read `src/app.md`, and read the note in
`src/host_notes/` that matches the host you are in. A host with a quirk worth
recording gets a note there; `src/host_notes/README.md` lists them.

## 3. The app

Download `BristolTickets-<version>.zip` from
[the releases page](https://github.com/JackHatchett/bristol-tickets/releases),
unzip it, and drag **Bristol Tickets** to your Applications folder. It carries
everything: the board, the agents, and the Python it runs on. There is nothing
to clone and nothing to install.

Requires **macOS**. Other platforms have not been run.

### The first launch, and what macOS says about it

Bristol Tickets is not signed with an Apple developer certificate, so the first
time you open it macOS says:

> **"BristolTickets" Not Opened.** Apple could not verify "BristolTickets" is
> free of malware that may harm your Mac or compromise your privacy.

That is macOS reporting that nobody has paid Apple to vouch for this app — not
that anything was found in it. To open it anyway:

1. Click **Done** on that message.
2. Open **System Settings → Privacy & Security** and scroll to the Security
   section. It says *"BristolTickets" was blocked to protect your Mac.*
3. Click **Open Anyway**, and confirm with your password or Touch ID.

You do this once. Every launch after it is an ordinary double-click.

## 4. First run

Opening the app for the first time runs setup.

### Where Bristol lives

The first thing it asks is which folder to put Bristol in — `~/Bristol` unless
you say otherwise. That folder is the whole system: the agent files, your
configuration, your data, your board. You will point your agent host at it, so
somewhere you can find again is the right answer. Choosing a folder that already
holds a Bristol installation takes that one on rather than overwriting it.

A run from source skips this question: the folder is the one you cloned.

### The wizard

With no configuration present, Bristol Tickets opens a setup wizard instead of
an empty board. Four pages:

1. **Name this installation.** An installation name — lower case, no spaces,
   prefilled with your operating system's short user name — and the folder its
   data lives in. The name becomes a directory under `data/`, and everything
   personal to you lives inside it.
2. **Choose your agents.** The seven shipped agents with a one-line description
   each. Tick the ones you want; the others are never created. `chief_of_staff`
   is always installed, because it is the only agent allowed to change how any
   of them work. Checking a box installs an agent rather than selecting it; the
   *The next session starts as* setting on the Settings tab chooses which one
   you talk to. You can add or remove agents later by editing your configuration
   ([configuration.md](configuration.md)).
3. **Link your notes and library.** Both optional. A Markdown notebook — any
   folder of notes you edit yourself — and a Zotero data folder. Leave either
   blank to skip it.
4. **Ready to set up.** A summary of exactly what will be written, ending with
   what Finish does, and a tick box deciding whether this installation becomes
   the one Bristol Tickets opens at startup. Nothing has been written before you
   press Finish, and Cancel takes back the folder this run placed — one that
   already held something of yours is left as it stands.

### Creating, or adopting what is already there

A data folder holding no board is **created**. Finish makes the data folders
each enabled agent declares, provisions `tickets.db` with the schema, and writes
`config/config.local.json` from the shipped template with your answers filled
in.

A data folder that already holds `tickets/tickets.db` is **adopted**. Setup says
so as you leave the first page and offers to take it on. Nothing inside it is
changed: no schema runs against that board, and `config/config.local.json` is
left as it stands. Pages 2 and 3 are skipped, because adoption needs no answer
they collect.

Either way, the last thing Finish writes is the instance pointer — a small file
outside the repository naming the installation this machine opens, so a
relocated app can still find its data. The summary page names the installation
Bristol Tickets opens today and the one it opens afterwards, and the tick box on
that page decides whether that hand-over happens. Clear it to set an
installation up, or adopt one, without changing what the app opens; an adoption
with it cleared writes nothing at all.

**File → Setup…** re-runs the wizard from a running Bristol Tickets, and
adopting is how you point it back at an installation you already have. Replacing
an existing configuration asks first; adoption never reaches that question.

### Connecting an agent

The last thing setup shows is where your folder went and the line to paste into
an agent host that takes typed project instructions, with a button to copy it. A
host that reads `AGENTS.md` or `CLAUDE.md` needs none of that: it finds them in
that folder on its own.

## Updating

Download the newer release and open it. It brings the machinery in your folder
up to that release and leaves `config/` and `data/` alone, so your board, your
settings and everything you have written survive untouched. There is nothing to
uninstall first.

## 5. Open a session on the folder

In your agent host, select your Bristol folder and start a conversation. The
agent reads `src/app.md` on its own and takes it from there.
[sessions.md](sessions.md) describes what happens next.

---

## Running from source instead

Everything above is the download. The source is the same system with the build
step in your hands: take it if you want to change Bristol, not to use it.

Requires **macOS** and **Python 3.10 or later**.

```bash
git clone https://github.com/JackHatchett/bristol-tickets.git bristol_tickets
cd bristol_tickets
pip install -r requirements.txt
python3 src/tools/bristol/app.py
```

That is PySide6, and it covers the board and the agents. On a Homebrew-managed
Python, `pip` may refuse a system-wide install; either add
`--break-system-packages`, or make a virtual environment first:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Setup runs the same way, minus the question about where Bristol lives — the
clone is that folder.

### The optional toolkit

Everything else under `src/tools/` is a toolkit the agents reach for — photo
processing, job-description scraping, OCR — and none of it is needed to run the
board. Install it when you want one of those tools:

```bash
pip install -r requirements-tools.txt
```

Three of them then need a step pip cannot perform:

| Tool | Extra step |
| --- | --- |
| Job-description scraping (`src/tools/jd_scraper/`) | `playwright install chromium` |
| PDF-to-Markdown OCR (`src/tools/document_tools/`) | `brew install tesseract ghostscript poppler` |
| Gmail harvesting (`jd_scraper/gmail_harvest.py`) | A Google Cloud OAuth credential file — see that tool's own README |

### Building the release

```bash
python3 src/tools/bristol/make_release.py
```

Runs the publication checks, builds the bundle with the project tree staged
inside it, writes the zip and its checksum, and prints the command that
publishes them. `src/tools/bristol/BUILD_APP.md` covers what it does and the
lighter live-source launcher for iterating.

## Running the board from a different location

Bristol Tickets finds its database in a fixed order: the `TICKETS_DB`
environment variable, then the instance pointer at `~/Library/Application
Support/BristolTickets/instance.json`, then a local pointer file, then by
walking up the source tree looking for `data/*/tickets/tickets.db`. Running from
inside the repository needs no pointer at all. Write one when you build a
standalone app, which is relocatable and cannot see the repository:

```bash
python3 src/tools/config_tools/instance_pointer.py --write   # create it
python3 src/tools/config_tools/instance_pointer.py           # print it
```

## Setting up by hand instead

If you would rather not use the wizard:

```bash
cp config/config.example.json config/config.local.json
# edit config.local.json, replacing every placeholder
python3 src/tools/ticket_tools/create_tickets.py --instance <your-instance-name>
```

`create_tickets.py` errors rather than overwriting if the instance already
exists. Every key in the config file is documented in
[configuration.md](configuration.md).
