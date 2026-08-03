# Test Control

A desktop app for manual QA. Blueprint test cases are drafted once; each run
clones them into an independent session ledger where every step is marked pass
or fail and defects are noted against the row.

```
cd src/tools/test_control
python3 app.py
```

Needs PySide6 (`pip3 install PySide6 --break-system-packages`). A fresh database
opens seeded with one suite, two cases and one run; replace them from the
Blueprint Template Editor.

## Layout

- **`app.py`** — resolves the database path, applies the schema, seeds a fresh
  database, and opens the window.
- **`ui/main_window.py`** — `TestControlWindow`, taking an already-provisioned
  connection. Four tabs:
  1. **Execution Dashboard** — run a cloned session: pick a checklist row,
     toggle each step, write defect notes, commit the row.
  2. **Session Clones Manager** — clone the current blueprints into a new
     session; rename or delete a session.
  3. **Blueprint Template Editor** — add, edit and delete the permanent
     blueprint cases and their steps.
  4. **Analytics Room** — pass and fail counts, and completion rate.

The `app.py` plus `ui/` shape mirrors `bristol`. The two share nothing else.

## Database

`data/<instance>/test_control/test_control.db`, resolved as `ticket_tools`
resolves `tickets.db`: the parent of a `data/*/tickets/tickets.db` match, else
the first existing `data/<instance>/`, else `AGENT_INSTANCE_SLUG` or
`default_user`. `TEST_CONTROL_DB=/path/to/file.db` overrides it outright.

- **Blueprint tables** — `control_milestone`, `control_suite`, `control_case`,
  `control_case_step`.
- **Session tables** — `control_run`, `control_run_item`,
  `control_run_step_item`. A clone copies every current case and step into rows
  of its own, so editing a blueprint never changes a run already under way.
- **Deleting a blueprint cascades to its steps** and leaves cloned rows intact.
- **Nothing here reads or writes `tickets.db`.** Manual QA and the agent board
  are different concerns in different files.
