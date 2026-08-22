# fresh_clone_rehearsal — chief_of_staff playbook

Prove a stranger can install Bristol, before anything is pushed to a public
remote. Input is the committed tree; output is a pass or a list of defects fixed
in the repo. `version_control_milestone.md` owns committing.

Two ways in, and a release rehearses both: **the download**, which is how a
stranger arrives, and **the clone**, which is how a developer does.
§The download rehearsal covers the first; the numbered procedure covers the
second.

## Preconditions

- **The working tree is committed and `git status` is empty.** The rehearsal
  tests what a clone would receive, which is `HEAD` and nothing else.
- **The user is at the machine.** Three steps need a terminal, and a session
  cannot type into one — see §Who does what.

## Who does what

- **The session runs** every `git`, `sqlite3` and repo-file step, in its own
  shell, and every leak scan.
- **The user runs** anything that touches the Mac's own Python, the pointer
  file outside the mounted folders, or launches an app. A session's shell
  cannot reach `~/Library`, and computer use cannot type into a terminal.
- **The session may drive the Bristol Tickets window by clicking** once the user
  has launched it. Bristol Tickets is an ordinary application to computer use.
- **Put each user command in the clipboard** with `write_clipboard`, then ask
  for one paste. Never make the user retype a path.

## The download rehearsal

The same shape as below — a stranger's machine, a scratch folder, a real
session — against the artifact a stranger actually gets.

1. **Do steps 1 and 2 below first.** The pointer beats every other resolution,
   so a machine still holding one never opens setup.

2. **Build the release.** A user step, in Terminal:
   `python3 src/tools/bristol/make_release.py`. It fails rather than shipping a
   bundle whose payload did not stage.

3. **Unzip somewhere outside the repository and open the app.** A user step. It
   passes the Gatekeeper gate the way `docs/install.md` §The first launch says
   it will; a build that opens with no warning at all means it was launched
   from a path macOS never quarantined, and the check did not happen.

4. **Give the placement page a scratch folder** — `~/Downloads/bristol_download`
   — then complete the wizard as in step 8 below. It passes when that folder
   holds `src/`, `docs/`, the entry files, `config/config.local.json` and a
   board, and no `data/` belonging to anyone else.

5. **Check the hand-off page** names that folder and copies a line naming it.

6. **Prove an update keeps the installation.** A user step: raise `src/VERSION`,
   rebuild, and open the new app. It passes when `src/VERSION` in the scratch
   folder rises, `config/config.local.json` is byte-identical, and the board
   still holds the card step 9 made.

7. **Then steps 9 through 12 below**, against the scratch folder.

## Procedure

The clone path, for a developer.

1. **Note the four values the last step adopts.** A user step. The rehearsal
   cannot start without them.

   ```bash
   cat ~/Library/Application\ Support/BristolTickets/instance.json
   ```

   **An absent pointer is a normal state here, not a stop.** Take the four
   values from the real repository instead: `repo_root` is the clone,
   `config_path` is its `config/config.local.json`, and `data_root` and
   `instance_slug` are what that file's `important_paths.tickets_db` resolves
   back to — the folder holding the installations, and the one installation's
   folder beneath it. `instance_pointer.py` (no arguments) prints the pointer;
   `--write` reconstructs it from exactly those values.

2. **Remove the pointer, so the machine is in a stranger's state.** A user step,
   skipped where step 1 found none. The pointer is per-machine and beats
   relative discovery, so a copy launched beside it resolves the real
   installation, the wizard never opens, and every step after this one tests the
   wrong board. The last step writes a new pointer by adoption; nothing is kept
   to restore.

   ```bash
   rm ~/Library/Application\ Support/BristolTickets/instance.json
   ```

3. **Build the scratch copy from `HEAD`.** A session step. `git archive` emits
   exactly the tracked files, so no ignored file, no `config/config.local.json`
   and no `data/` content can travel.

   ```bash
   rm -rf ~/Downloads/bristol_rehearsal
   mkdir -p ~/Downloads/bristol_rehearsal
   git -C <repo> archive HEAD | tar -x -C ~/Downloads/bristol_rehearsal
   ```

   // Downloads is a mounted folder and the home directory is not, so the copy
   // goes there rather than beside the repo.

4. **Scan the copy for anything personal.** A session step. A hit outside
   `LICENSE` is a defect.

   ```bash
   cd ~/Downloads/bristol_rehearsal
   grep -rIlE "/Users/|/Volumes/" .
   ls -a config data
   ```

5. **Scan the history, not only the tree.** A session step. A file removed from
   `HEAD` is still in a clone.

   ```bash
   git -C <repo> log --all --pretty=format: --name-only --diff-filter=A | sort -u | grep -E "^(config/|data/)"
   git -C <repo> log --all -p | grep -aoE "/Users/[A-Za-z0-9_.-]+" | sort -u
   ```

6. **Install the dependencies against the copy.** A user step, in Terminal.

   ```bash
   cd ~/Downloads/bristol_rehearsal && pip3 install -r requirements.txt
   ```

   A Homebrew-managed Python refuses this; `docs/install.md` holds both ways
   round it.

7. **Launch Bristol Tickets from the copy.** A user step. The session takes the
   window from here.

   ```bash
   cd ~/Downloads/bristol_rehearsal && python3 src/tools/bristol/app.py
   ```

8. **Complete the wizard, and check what it wrote.** The session clicks
   through, naming the instance something disposable and pointing the data
   folder inside the scratch copy. Then confirm `config/config.local.json`
   exists, the enabled agents' folders exist, and `tickets.db` opens empty.

   **Give the notebook page a folder inside the scratch copy too.** An unset
   notebook resolves to no reports directory, and the report step then passes
   by writing nothing.

   **Leave the summary page's startup box ticked.** Step 10 resolves the board
   through the pointer, so a run that declines it tests the real installation
   instead of the copy.

9. **Work one card end to end in the window** — create it, close it, Clear
   Done — and confirm the report landed in that notebook folder.

10. **Run one session against the copy.** A user step: point an agent host at
   `~/Downloads/bristol_rehearsal`, open a new conversation there, and say
   `continue`. It passes when the session initializes from `src/app.md`,
   resolves config, loads an agent, prints a snapshot, and names no path
   belonging to the user.

11. **Fix every defect in the repo, never in the copy**, then rebuild the copy
    from step 3 and re-run. A fix made in the scratch copy is lost and proves
    nothing.

12. **Hand the pointer back by adopting the real installation, then delete the
    copy.** The user launches Bristol Tickets from the real repository and the
    session drives **File → Setup…**: name the installation step 1 recorded,
    choose its data folder, adopt it, and Finish with the startup box ticked.
    Adoption writes the pointer and nothing else. Deleting the copy is a
    session step.

    ```bash
    rm -rf ~/Downloads/bristol_rehearsal
    ```

## Failure modes

- **The user's real Bristol Tickets opens the scratch board afterwards** → the
  pointer was not handed back. Step 12, or re-run `instance_pointer.py --write`
  from the real repo.
- **Step 12's wizard offers to create rather than adopt** → the data folder it
  was given holds no `tickets/tickets.db`. The folder to choose is the one the
  pointer's `data_root` and `instance_slug` name together, not `data_root`
  alone.
- **`TICKETS_DB` is set in the environment** → the wizard never opens, because
  the variable suppresses first-run setup. Unset it before step 7.
- **The scratch copy resolves the real board** → either the pointer is still in
  place (step 2), or the copy was placed inside the repo. Path resolution
  consults the pointer before it walks up to the nearest `src/app.md`, so the
  pointer must be gone and the copy must sit outside.
- **A step needs more than one session** → the board carries it. Leave the card
  in `doing` at the top of its column with what remains in one comment.

## Audit

- **The copy is verified against `HEAD` by a session that did not create it.**
  `diff -r` between a fresh `git archive` extraction and the copy returns
  nothing but the files the wizard wrote.
- **The scratch copy exists nowhere at the end.** It is not a deliverable.
  `~/Downloads/bristol_download` and the built `dist/` go the same way.
