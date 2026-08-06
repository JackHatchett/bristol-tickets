# Test Tools

The CLI side of testing, as `ticket_tools` is the CLI side of `bristol`. The
manual-QA database and its GUI are `test_control/`.

## Runtime smoke checker

Builds each PySide6 GUI's real widgets on Qt's `offscreen` platform, catching
import errors, signal/slot mismatches and construction-time exceptions that
`py_compile` cannot see. It paints nothing, so layout and appearance still need a
real display.

```
bash run_smoke.sh                 # every target
bash run_smoke.sh bristol         # one or more named targets
```

- **`run_smoke.sh`** — provisions the headless environment, then runs `smoke.py`
  with the arguments it was given. A passthrough where PySide6 and a display are
  present; on Linux without them it installs PySide6 and extracts the GL/EGL
  libraries Qt needs into a cache under `TMPDIR`, without root.
- **`smoke.py`** — the per-target checks, registered in `TARGETS` (`bristol`,
  `test_control`, `governing_docs`, `published_files`). Add a target by writing a `check_*` function
  returning a list of failure strings and registering it. Each target runs in its
  own subprocess.
  // Every GUI ships a top-level `ui` package, and two of them cannot coexist in
  // one interpreter.
- **`governing_docs` asserts what a reader cannot count**: the resident core
  against its word cap, stated in `src/templates/identity_template.md`'s style
  contract. It touches no GUI, so it runs without Qt.
- **`published_files` asserts the machinery carries no installation**: this
  git-identity's name and email, the home path declared at `drives.local_home`,
  and any `/Users/<name>` literal are absent from every tracked file except
  `LICENSE`, which exists to name a person. It touches no GUI either.
- **`qt_headless.py`** — the GUI-agnostic helpers: `offscreen_app()` and
  `tool_on_path(tool_name)`.
