# Bristol

A Kanban board on your desktop whose cards are the work you hand to Claude,
shipped with a set of ready-made agents.

You keep your work on a board of cards: to-do, doing, done. Open a Claude
session pointed at this folder, say "continue," and the agent reads the board,
takes the top card in its queue, does the work on your real files, and writes
back what it did. Next time you open the board, the card has moved.

## Before you install

**A Claude subscription that includes Cowork, and the Claude desktop app.**
Cowork is what lets Claude read and write files in a folder you choose. Without
it there is no agent — you get a working Kanban board and nothing else. Also
macOS and Python 3.10 or later.

## Install

1. **Get Cowork.** Check the Claude plan comparison; it is not on the free tier.
2. **Install the Claude desktop app** and sign in. Cowork is a mode inside it,
   not in the browser.
3. **Clone this repository and install its dependencies.** The board needs
   PySide6 and nothing else; the optional toolkit under `src/tools/` has its own
   file, `requirements-tools.txt`.

   ```bash
   git clone <this-repo> bristol_tickets
   cd bristol_tickets
   pip install -r requirements.txt
   ```

4. **Run Bristol Tickets.** The first launch opens a setup wizard: it asks for
   an instance name, where your data lives, which agents you want, and
   optionally a Markdown notebook and a Zotero folder.

   ```bash
   python3 src/tools/bristol/app.py
   ```

5. **Point Cowork at this folder** and start a session.

[docs/install.md](docs/install.md) covers the whole chain, including the three
optional tools that need something pip cannot install.

## Quickstart

```bash
python3 src/tools/bristol/app.py                           # open the board
python3 src/tools/bristol/make_launcher.py                 # put it in your Dock
python3 src/tools/config_tools/read_config.py active_agent # who the next session runs as
```

Then, in Cowork with this folder selected, say `continue`.

## Rebuilding and reinstalling

Your data lives outside the app bundle — in `data/` and `config/` in this
repository — so upgrading never touches it.

**Running from source** (`python3 src/tools/bristol/app.py`, or the launcher
`make_launcher.py` writes): `git pull` and relaunch. There is nothing to
rebuild.

**Running a frozen `BristolTickets.app`:**

```bash
rm -rf ~/Applications/BristolTickets.app          # or wherever you installed it
cd src/tools/bristol
rm -rf build dist
python3 setup.py py2app
```

Then drag `dist/BristolTickets.app` back to `~/Applications`. Full detail, and
the choice between the two, in
[src/tools/bristol/BUILD_APP.md](src/tools/bristol/BUILD_APP.md).

## The two surfaces

Both act on the same database and the same configuration, and each sees the
other's changes on its next read.

- **Bristol Tickets** (`src/tools/bristol/`) — the desktop app. Read the board,
  create and edit cards, drag them between columns, attach links and images,
  with no agent involved.
- **The Claude session** (`src/app.md`) — Claude reads `src/app.md`, resolves
  your config, takes on one agent identity, and works the board.

`src/tools/` holds the rest of the standalone utilities, each independently
runnable.

## Documentation

Start at [docs/index.md](docs/index.md).

- [install.md](docs/install.md) — the prerequisites, in the order they have to
  happen.
- [sessions.md](docs/sessions.md) — the loop you actually live in.
- [board.md](docs/board.md) — tabs, columns, cards, links, images, reports.
- [agents.md](docs/agents.md) — the shipped agents and what each needs.
- [configuration.md](docs/configuration.md) — every key and its default.
- [architecture.md](docs/architecture.md) — how the app, the database and the
  agent files fit together.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

Bristol Tickets is drawn with Qt for Python (PySide6), under the LGPLv3. Running
from source installs it onto your own machine and nothing further attaches. A
distributed `BristolTickets.app` carries a compiled copy inside the bundle, so
the build ships
[ACKNOWLEDGEMENTS.md](src/tools/bristol/ACKNOWLEDGEMENTS.md) in its Resources,
naming the licence and how a recipient replaces the bundled libraries.
