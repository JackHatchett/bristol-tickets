---
name: checking-a-bristol-change
description: What a change to Bristol Tickets has to pass before its card may close — the smoke targets that run wherever the session is, the route for the two that build Qt widgets, and the change that has to be looked at on the machine the app runs on. Use when a change to Bristol Tickets is being checked.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3, and for the two Qt targets a shell that has PySide6 or can install it.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/test_tools/smoke.py src/tools/test_tools/run_smoke.sh src/tools/config_tools/data_paths.py src/tools/config_tools/read_config.py
---
# checking-a-bristol-change

Input: a change to Bristol Tickets. Operation: the runs below. Output: what each
run produced, in the closing comment of the card the change belongs to.

`src/skills/verifying-a-card/SKILL.md` owns the rule that a card names its check
before it may close, and what a closing comment carries. This owns what the
check is when the thing changed is Bristol Tickets.

## What runs wherever the session already is

- **Run the six targets that build no widget** — `python3
  src/tools/test_tools/smoke.py agent_tools payload config_resolution
  governing_docs skill_declarations published_files`. They read files, copy
  trees and provision databases, so `python3` is the whole requirement.
- **Any `SMOKE FAIL` line is the result**, whatever passed above it.
- **A change to a governing document, a skill or a tool is checked here and
  nowhere else.** Nothing it touches draws a window.

## What needs Qt

- **`bristol` and `test_control` build the application's real widgets** on Qt's
  offscreen platform, which catches an import error, a signal/slot mismatch and
  a construction-time exception. Both need PySide6.
- **Where the shell already has PySide6, run `bash
  src/tools/test_tools/run_smoke.sh bristol test_control`.** It provisions the
  headless environment, installing PySide6 and the GL libraries Qt needs where
  they are absent, and passes its arguments to `smoke.py`.
- **Choose the shell before the install, never after.** `run_smoke.sh` installs
  into whichever shell invokes it, so a shell that must not gain PySide6 — its
  host note says whether it is one — is a shell that never calls it.
- **A shell that must not or cannot install takes the archive route.**

## The archive route

Input: the working tree. Operation: the steps below. Output: the two Qt targets'
output, from a shell that has Qt.

1. **Archive `src` and `config` into the declared staging location.**

   ```
   STAGING="$(python3 src/tools/config_tools/data_paths.py --ensure --path \
       "$(python3 src/tools/config_tools/read_config.py bristol_data.folders.staging)")"
   tar czf "$STAGING/bristol_smoke.tgz" -C <project root> src config
   ```

   Those two are what these targets read: the tools the widgets are built from,
   the schema a board is provisioned from, and the configuration both resolve
   through. Nothing under `/data` — a target wanting a board provisions its own.

2. **Never write the archive to a path typed by hand.**
   `bristol_data.folders.staging` is the one place it goes, resolved through
   `src/tools/config_tools/data_paths.py`, and what sits there is a declared
   container rather than a file left behind — `src/app.md` §What a file may say.

3. **Carry the archive to a shell that has PySide6 or may install one.** How a
   file crosses between two shells is the host's, and its note says.

4. **Extract it there, install, and call `smoke.py` directly.**

   ```
   mkdir -p <scratch>/bristol && tar xzf <archive> -C <scratch>/bristol
   pip install PySide6 --break-system-packages
   cd <scratch>/bristol && QT_QPA_PLATFORM=offscreen \
       python3 src/tools/test_tools/smoke.py bristol test_control
   ```

   `run_smoke.sh` is not the entry point here: it installs where it is invoked,
   and the install is the deliberate step above.

5. **Re-archive and re-carry after every edit.** The extracted copy is a
   snapshot, and a pass against a stale one reports on code the user does not
   have.

6. **Leave the archive at the staging location and write nothing outside it.**
   The next run overwrites it, which is what a container is for.

## What a visible change additionally needs

- **Check a visible change against Bristol Tickets running on the user's own
  machine**, with whatever the runtime offers for seeing a window there. Say so
  and stop where it offers nothing, rather than substituting a render of a
  different platform.
- **An offscreen render settles geometry at most.** It draws the wrong control
  set, fonts and pixel ratio, so a Qt target passing says the widgets build and
  says nothing about how they look.
  // The install chased for a look at the app has cost more sessions than it
  // has saved.
- **A change nothing can see — storage, a migration, which card is next — is
  checked by the smoke targets and no further.**
- **Change the user's own settings to test one, and put them back.** Proving a
  choice survives a restart takes a real write to the real configuration, and
  the session that made the write is the one that reverses it and says so.

## Failure modes

- **The six headless targets claimed for a widget change** → they build no
  widget, and the two that do were not run.
- **A Qt run against an archive older than the last edit** → it reports on code
  that is not the code being closed on.
- **PySide6 installed into the shell the route exists to keep it out of** → the
  route was followed backwards.
- **The archive written beside the project, or into a folder of the user's own**
  → the staging location is declared so that no run has to choose one.
- **An offscreen screenshot offered as the look of a change** → it is the wrong
  platform's controls, and the user's machine is where the answer is.

## Audit

**Whether the two Qt targets ran against the tree as it stands now**, and
**whether anything a run created sits outside the declared staging location.**
