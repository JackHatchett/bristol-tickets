# test_tools — testing abilities for the fleet

CLI / harness counterpart to the `test_control` GUI, the same way `ticket_tools`
is the CLI counterpart to `bristol`:

| concern            | GUI (human-facing)     | CLI / harness (agent-facing) |
| ------------------ | ---------------------- | ---------------------------- |
| agent tickets      | `bristol`              | `ticket_tools`               |
| manual QA testing  | `test_control`         | **`test_tools`**             |

This is the home for testing abilities in general — not only the manual
test-case database that `test_control` manages. The first ability that lives
here is a **runtime-error smoke checker** for the PySide6 GUI tools.

## Runtime smoke checker

`py_compile` proves a file parses; it does not prove the app still *runs*. The
smoke checker builds each GUI's real widgets on Qt's `offscreen` platform,
catching import errors, signal/slot mismatches, and construction-time
exceptions. It paints nothing, so it is not a visual check — layout and looks
still need a real display (the packaged Mac app).

```
bash run_smoke.sh                 # provision env if needed, check every target
bash run_smoke.sh bristol         # one or more named targets
```

- `qt_headless.py` — reusable, GUI-agnostic helpers (`offscreen_app`,
  `tool_on_path`).
- `smoke.py` — the per-tool checks, in a `TARGETS` registry. Each target runs in
  its own subprocess because every GUI ships a top-level `ui` package that can't
  coexist in one interpreter. Add a tool by writing a `check_*` function and
  registering it.
- `run_smoke.sh` — provisions the headless env. On a normal machine with PySide6
  it's a passthrough; in the Linux sandbox it installs PySide6 and fetches the
  GL/EGL libs Qt needs (no root), all throwaway since the sandbox resets.

## Relationship to the test-case DB

`test_control` owns `data/<instance>/test_control/test_control.db` (manual QA
blueprints + cloned run sessions). `test_tools` is where CLI helpers for that DB
would go if/when needed — kept separate from the runtime smoke checker on
purpose: automated "does it run" checks and human "did this pass QA" tracking
are different testing abilities that happen to share this folder.
