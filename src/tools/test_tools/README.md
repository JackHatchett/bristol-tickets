# Test Tools

The CLI side of testing, as `ticket_tools` is the CLI side of `bristol`. The
manual-QA database and its GUI are `test_control/`.

## Unit tests

`unit/` tests the rules that move and close cards, function by function:
`src/tools/bristol/finishing.py`, `epic_closure.py`, `clear_done.py` and
`src/tools/ticket_tools/ticket_write.py`. Each test gets a board built from
`src/tools/bristol/schema.sql` in a temporary folder, so the real `tickets.db`
is never opened. `pyproject.toml` points pytest here.

```
python3 -m pytest
```

- **CI runs it under coverage** of `src/tools/bristol` and
  `src/tools/ticket_tools`, and the run ends on one total line:

  ```
  python3 -m pytest --cov=src/tools/bristol --cov=src/tools/ticket_tools \
      --cov-report= --cov-fail-under=10.7
  ```

  The floor, 10.7%, is the share the tests ran when coverage was first
  measured. A change that leaves a smaller share of that code tested fails the
  push; raising the floor follows tests that raise the share.

- **`unit/conftest.py`** — the fixtures: `db_path` and `conn` for a fresh
  board, `cli` for running `ticket_write.py`'s commands against it, and
  `add_epic`, `add_card` and `card` for seeding and reading rows.

## Runtime smoke checker

Builds each PySide6 GUI's real widgets on Qt's `offscreen` platform, catching
import errors, signal/slot mismatches and construction-time exceptions. It
paints nothing, so layout and appearance still need a real display.

```
bash run_smoke.sh                 # every target
bash run_smoke.sh bristol         # one or more named targets
```

- **`run_smoke.sh`** — provisions the headless environment, then runs `smoke.py`
  with the arguments it was given. A passthrough where PySide6 and a display are
  present; on Linux without them it installs PySide6 and extracts the GL/EGL
  libraries Qt needs into a cache under `TMPDIR`, without root.
- **`smoke.py`** — the runner. `TARGETS` lists every target by name, and each
  target runs in its own subprocess.
- **`smoke_targets/`** — one module per target, `check_<target>.py`, defining
  `check_<target>()`: it returns the lines a pass prints and raises
  `SmokeFailure` (`smoke_targets/failure.py`) on a failed check. Add a target by
  writing its module and listing its name in `TARGETS`.
- **`bristol` also times what a person waits on**, on a seeded board of
  `SPEED_BOARD_CARDS` cards: opening the window, a Refresh, a theme change in
  Settings, a top-bar agent choice and a full Settings reload, each against its
  limit in `SPEED_LIMITS`. A timing over its limit fails the target with the
  time it took.
- **`board_flows` drives the core board flows through the real window**: a
  card created, edited, moved between columns and reordered within one, two
  cards linked and the link seen from both, an image attached, a title
  searched, a card closed to done, an agent chosen in the top bar and seen in
  Settings, and a setting read back by a rebuilt window. Each step is checked
  on the board database and on the widgets, and a failure gives the flow and
  the step. The board, its images and the configuration are built in a
  temporary folder with `HOME` and `XDG_CONFIG_HOME` pointed there, and a run
  that changed the installation's `config/config.local.json` fails. It builds
  widgets, so it needs PySide6, as `bristol` does.
- **`governing_docs` asserts what a reader cannot count**: the resident core
  against its word cap, stated in `src/templates/identity_template.md`'s style
  contract. It touches no GUI, so it runs without Qt.
- **`payload` asserts a download installs and updates without loss**: the tree
  a built `.app` carries goes onto disk, an update replaces the machinery and
  leaves the board and the configuration untouched, and an abandoned setup
  takes back only what it placed. It is plain file copying, so it runs without
  Qt.
- **`skill_declarations` asserts every script a native skill declares is on
  disk**, reading `metadata.bristol.scripts` from each `SKILL.md`. A missing
  script is reported by tool with every skill that declares it, because a
  renamed tool is one edit and what the person fixing it needs is the whole
  list. It reads Markdown only, so it runs without Qt.
- **`agent_tools` asserts an agent's two files cannot drift apart**: creating
  writes the charter and the config entry together, a refused edit writes
  neither, an edit reaches both, the charter file can be moved, and a fresh read
  finds what was entered. It also asserts every shipped charter reads back as
  the file it is, that every key every entry contains reaches a field or `extra` so
  an edit cannot drop one, and that neither agent tool imports anything reaching
  a network or a model. It runs in a scratch clone and touches no GUI, so it
  runs without Qt.
- **`published_files` asserts the machinery carries no installation**: this
  git-identity's name and email, the home path declared at `drives.local_home`,
  and any `/Users/<name>` literal are absent from every tracked file except
  `LICENSE`, which exists to name a person. It touches no GUI either.
- **`public_docs` asserts the public documents describe the tree**: every
  repository path and `python3` script that `README.md`, `CONTRIBUTING.md`,
  `src/tools/bristol/BUILD_APP.md` and each page under `docs/` give is on disk,
  a path an installation makes for itself (`data/`, `config/config.local.json`)
  aside; every charter under `src/agent_identities/` has a section in
  `docs/agents.md` and an entry in `config/config.example.json`; and every count
  of the shipped agents those documents give is the number of charters. It
  touches no GUI.
- **`qt_headless.py`** — the GUI-agnostic helpers: `offscreen_app()` and
  `tool_on_path(tool_name)`.


## Screen comparison

`screen_compare.py` compares Bristol Tickets' Board and Settings against
approved captures, pixel by pixel. It builds the real window on the platform it
runs on, on a seeded board and a configuration of its own, in each theme and
mode it is given, and grabs each screen with `QWidget.grab`. Run on the Mac the
app is used on, the captures have that machine's fonts and pixel ratio.

```
python3 screen_compare.py                          # every theme, light and dark
python3 screen_compare.py --theme warm --mode dark
python3 screen_compare.py approve                  # every capture that differed
```

- **The approved captures live in qa_engineer's QA folder**, under
  `data/<instance>/qa/screens`, named `<screen>-<theme>-<mode>.png`.
- **A capture past `THRESHOLD` is reported** with its screen, theme, mode and
  share of pixels changed; its fresh capture waits beside the approved one as
  `<name>.new.png`, with `<name>.diff.png` drawing the changed pixels in red.
  With nothing changed it prints one line saying so.
- **`approve` makes the fresh captures the approved ones**: all that wait, or
  those named.
- **The installation's configuration is never read or written**, so the user's
  theme and mode stay as he left them; a run that changed
  `config/config.local.json` reports it and exits 2.
