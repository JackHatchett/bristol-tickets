# Install

Four things have to be in place, in this order: a Claude subscription with
Cowork, the Claude desktop app, this repository and its Python dependencies, and
the first-run setup inside Bristol Tickets.

## 1. A Claude subscription that includes Cowork

**Bristol does not work without it.** Cowork is the Claude desktop
feature that lets Claude read and write files in a folder you choose and run
commands on your behalf. That is the entire mechanism by which an agent does
anything: there is no server, no API key in a config file, no background
process. The board is a board; Cowork is what makes it a queue somebody works.

Without Cowork you can still install everything below and use Bristol Tickets as
a solo Kanban app. Every reference in this manual to an agent doing something
will simply not apply.

Check the Claude plan comparison for which subscription tiers include Cowork —
it is not on the free tier.

## 2. The Claude desktop app

Install Claude for macOS and sign in with the subscription from step 1. Cowork
is a mode inside that app; it does not exist in the browser version. When you
open Cowork you will be asked to select a folder — that is where this repository
goes, so do step 3 first if you have not already.

## 3. This repository and its Python dependencies

Requires **macOS** and **Python 3.10 or later**. Other platforms have not been
run.

```bash
git clone <this-repo> bristol_tickets
cd bristol_tickets
pip install -r requirements.txt
```

On a Homebrew-managed Python, `pip` may refuse a system-wide install. Either add
`--break-system-packages`, or create a virtual environment first:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

That covers the board and the agents. Three optional tools need something pip
cannot install, and you can skip all three until you want the tool:

| Tool | Extra step |
| --- | --- |
| Job-description scraping (`src/tools/jd_scraper/`) | `playwright install chromium` |
| PDF-to-Markdown OCR (`src/tools/document_tools/`) | `brew install tesseract ghostscript poppler` |
| Gmail harvesting (`jd_scraper/gmail_harvest.py`) | A Google Cloud OAuth credential file — see that tool's own README |

## 4. First run

```bash
python3 src/tools/bristol/app.py
```

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
   *Start next session as* control above the board chooses which one you talk
   to. You can add or remove agents later by editing your configuration
   ([configuration.md](configuration.md)).
3. **Link your notes and library.** Both optional. A Markdown notebook — any
   folder of notes you edit yourself — and a Zotero data folder. Leave either
   blank to skip it.
4. **Ready to set up.** A summary of exactly what will be written, ending with
   what Finish does, and a tick box deciding whether this installation becomes
   the one Bristol Tickets opens at startup. Nothing has been written before you
   press Finish; Cancel writes nothing at all.

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

## 5. Point Cowork at the folder

In the Claude desktop app, open Cowork and select the `bristol_tickets` folder.
Claude reads `src/app.md` on its own and takes it from there. [sessions.md](sessions.md)
describes what happens next.

## Getting Bristol Tickets into your Dock

`src/tools/bristol/BUILD_APP.md` covers two ways to get a double-clickable app:
a small launcher that runs the repository source directly (edit and relaunch, no
build step), or a frozen bundle built with py2app (`python3 setup.py py2app`,
portable, rebuild after each change).

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
