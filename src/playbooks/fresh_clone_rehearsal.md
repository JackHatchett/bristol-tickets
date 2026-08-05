# fresh_clone_rehearsal — chief_of_staff playbook

Prove a stranger can install this repository, before anything is pushed to a
public remote. Input is the committed tree; output is a pass or a list of
defects fixed in the repo. `version_control_milestone.md` owns committing.

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

## Procedure

1. **Read the instance pointer and note the installation it names.** A user
   step. The rehearsal repoints it at the scratch copy, and step 11 hands it
   back by adopting that installation rather than restoring a copy of the file.

   ```bash
   cat ~/Library/Application\ Support/BristolTickets/instance.json
   ```

2. **Build the scratch copy from `HEAD`.** A session step. `git archive` emits
   exactly the tracked files, so no ignored file, no `config/config.local.json`
   and no `data/` content can travel.

   ```bash
   rm -rf ~/Downloads/bristol_rehearsal
   mkdir -p ~/Downloads/bristol_rehearsal
   git -C <repo> archive HEAD | tar -x -C ~/Downloads/bristol_rehearsal
   ```

   // Downloads is a mounted folder and the home directory is not, so the copy
   // goes there rather than beside the repo.

3. **Scan the copy for anything personal.** A session step. A hit outside
   `LICENSE` is a defect.

   ```bash
   cd ~/Downloads/bristol_rehearsal
   grep -rIlE "/Users/|/Volumes/" .
   ls -a config data
   ```

4. **Scan the history, not only the tree.** A session step. A file removed from
   `HEAD` is still in a clone.

   ```bash
   git -C <repo> log --all --pretty=format: --name-only --diff-filter=A | sort -u | grep -E "^(config/|data/)"
   git -C <repo> log --all -p | grep -aoE "/Users/[A-Za-z0-9_.-]+" | sort -u
   ```

5. **Install the dependencies against the copy.** A user step, in Terminal.

   ```bash
   cd ~/Downloads/bristol_rehearsal && pip3 install -r requirements.txt
   ```

   A Homebrew-managed Python refuses this; `docs/install.md` holds both ways
   round it.

6. **Launch Bristol Tickets from the copy.** A user step. The session takes the
   window from here.

   ```bash
   cd ~/Downloads/bristol_rehearsal && python3 src/tools/bristol/app.py
   ```

7. **Complete the wizard, and check what it wrote.** The session clicks
   through, naming the instance something disposable and pointing the data
   folder inside the scratch copy. Then confirm `config/config.local.json`
   exists, the enabled agents' folders exist, and `tickets.db` opens empty.

   **Leave the summary page's startup box ticked.** Step 9 resolves the board
   through the pointer, so a run that declines it tests the real installation
   instead of the copy.

8. **Work one card end to end in the window** — create it, close it, Clear
   Done — and confirm a report is written.

9. **Run one session against the copy.** A user step: add
   `~/Downloads/bristol_rehearsal` as a folder in Cowork, open a new
   conversation there, and say `continue`. It passes when the session
   initializes from `src/app.md`, resolves config, loads an agent, prints a
   snapshot, and names no path belonging to the user.

10. **Fix every defect in the repo, never in the copy**, then rebuild the copy
    from step 2 and re-run. A fix made in the scratch copy is lost and proves
    nothing.

11. **Hand the pointer back by adopting the real installation, then delete the
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
  pointer was not handed back. Step 11, or re-run `instance_pointer.py --write`
  from the real repo.
- **Step 11's wizard offers to create rather than adopt** → the data folder it
  was given holds no `tickets/tickets.db`. The folder to choose is the one the
  pointer's `data_root` and `instance_slug` name together, not `data_root`
  alone.
- **`TICKETS_DB` is set in the environment** → the wizard never opens, because
  the variable suppresses first-run setup. Unset it before step 6.
- **The scratch copy resolves the real board** → it was placed inside the repo.
  Path resolution walks up to the nearest `src/app.md`, so the copy must sit
  outside.
- **A step needs more than one session** → the board carries it. Leave the card
  in `doing` at the top of its column with what remains in one comment.

## Audit

- **The copy is verified against `HEAD` by a session that did not create it.**
  `diff -r` between a fresh `git archive` extraction and the copy returns
  nothing but the files the wizard wrote.
- **The scratch copy exists nowhere at the end.** It is not a deliverable.
