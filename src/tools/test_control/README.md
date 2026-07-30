# test_control — Folder README

> Standalone desktop utility for managing and executing manual QA test cases via a
> twin-hierarchy (Master Blueprint Templates and Cloned Test Sessions) SQLite layout.

---

## 1. Purpose & Scope

- **Why this folder exists:** `test_control` is a lightweight, local desktop QA
  management tool. It lets you draft blueprint test cases, clone those templates into
  independent, runnable session ledgers, mark checklist rows Pass/Fail per step, and
  capture defect notes.
- **Conceptual layer:** `src/tools/test_control` — a human-facing local desktop
  utility that bypasses full agentic mediation, same as `bristol`.
- **Layout:** mirrors `bristol` for regularity — `app.py` is the entry point,
  the PySide6 window class lives under `ui/`.
- **Out of scope:** cross-agent communication, the roadmap DB, or workspace
  orchestration.

---

## 2. Contents Overview

- **`app.py`** — entry point. Resolves the DB path, provisions the schema (and seeds
  a starter suite/case/run on first run), then launches the PySide6 window.
- **`ui/main_window.py`** — `TestControlWindow`, a 4-tab workflow:
  1. *Execution Dashboard* — run a selected cloned session: click a checklist row,
     toggle step Pass/Fail, write defect notes, commit the row status.
  2. *Session Clones Manager* — instantiate a new run session by cloning the current
     Master Blueprints, rename or delete sessions.
  3. *Blueprint Template Editor* — view/add/edit/delete the permanent Master
     Blueprint test cases and their steps.
  4. *Analytics Room* — global pass/fail counts and completion rate.

---

## 3. Database

- **Location:** `agent_system/data/<instance>/test_control/test_control.db` —
  resolved the same way `roadmap_tools` resolves `roadmap.db`: `app.py` looks for
  the active instance dir via `data/*/roadmap/roadmap.db`'s parent, falls back to
  the first existing `data/<instance>/` dir, and only falls back further to
  `AGENT_INSTANCE_SLUG`/`default_user` if neither exists yet. No personal path is
  hardcoded in the tracked script.
  - Override for testing: `TEST_CONTROL_DB=/path/to/file.db python3 app.py`.
- **Schema:** `control_milestone`, `control_suite`, `control_case`,
  `control_case_step` (the Master Blueprint side), and `control_run`,
  `control_run_item`, `control_run_step_item` (the cloned-session side — each
  session clones every current case/step into its own rows so later template edits
  don't retroactively change a run already in progress).
- **Isolation from the roadmap DB:** this is a separate SQLite file from
  `roadmap.db`. Manual QA test-case tracking and the agent roadmap are different
  concerns; nothing here reads or writes `roadmap.db`.

---

## 4. System Relationships

- **Interactions with other folders:** none beyond its own `data/<instance>/test_control/`
  directory. Purely a user-driven script utility acting on its own local SQLite
  state-store.
- **Relationship to bristol:** structurally parallel (`app.py` + `ui/`) but
  functionally independent — different DB, different purpose.

---

## 5. Human Audit Checklist

- **Database maintenance:** periodically check `data/<instance>/test_control/test_control.db`
  and purge old cloned session runs you no longer need (via the Session Clones
  Manager tab, or directly) to keep file size down.
- **Layout:** if long text pushes content off-screen, check the `QScrollArea` /
  `QTextBrowser` settings in `ui/main_window.py`.
- **Blueprint integrity:** deleting a blueprint template cascades to its steps via
  `ON DELETE CASCADE`; it does not retroactively touch already-cloned session rows
  (`control_run_item`/`control_run_step_item` reference the case/step ids that
  existed at clone time).

---

## 6. Running It

```
cd agent_system/src/tools/test_control
python3 app.py
```

Requires PySide6 (`pip3 install PySide6 --break-system-packages`). On first run
against a fresh DB it seeds one starter suite, two example cases, and one run —
delete/replace these via the Blueprint Template Editor tab once you have real
cases.
