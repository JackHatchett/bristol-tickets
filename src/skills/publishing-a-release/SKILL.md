---
name: publishing-a-release
description: Puts a release of Bristol Tickets on GitHub — the checks that gate it, the build that publishes it, the notes it carries, and the first-install check the install path earns. Use when a release is being cut.
license: MIT
compatibility: Needs git and the GitHub CLI available to the user in the project folder.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/bristol/make_release.py src/tools/bristol/app.py src/tools/test_tools/smoke.py src/tools/config_tools/instance_pointer.py
---
# publishing-a-release

Put a release of Bristol Tickets on the public repository. Input is a committed
tree; output is a published release carrying an installable build and notes that
say what it gives someone. `src/skills/version-control-milestone/SKILL.md` owns
committing.

## Preconditions

- **The working tree is committed and `git status` is empty.** A release ships
  `HEAD` and nothing else.
- **The user is at the machine.** Pushing, dispatching the build and writing the
  notes need their credentials, and a session cannot type into their terminal.

## Who does what

- **The session runs** every check below, every repository file edit, and the
  commits.
- **The user runs** anything needing a credential: the push, the workflow
  dispatch, and the command that writes the notes.
- **Give each user command on its own, in a copy-paste block, with what it
  does**, and wait for what it printed before giving the next.

## The number

- **Settle the number against the tags already published and the epics already
  closed, and state it to the user before anything is tagged.**
- **Raise the minor number for a release that adds a capability**, the patch
  number for one that only corrects behaviour.
- **`src/VERSION` is where a version is written**, and the tag follows it. The
  workflow reads that file for both the tag and the title.

## The checks

Session steps, run before `src/VERSION` is raised.

- **Run every check that needs no Qt.**

  ```bash
  python3 src/tools/test_tools/smoke.py published_files governing_docs \
      skill_declarations payload config_resolution agent_tools
  ```

  `src/host_notes/` says where the Qt targets run when a host cannot.

- **Scan the history, not only the tree.** A file removed from `HEAD` is still
  in a clone, and `published_files` reads the tree alone.

  ```bash
  git log --all --pretty=format: --name-only --diff-filter=A | sort -u \
      | grep -E "^(config/|data/)"
  git log --all -p | grep -aoE "/Users/[A-Za-z0-9_.-]+" | sort -u
  ```

  `config/config.example.json`, `data/.gitkeep` and a placeholder home path are
  the whole of what may appear. **Fix anything else before the release is cut.**

- **Leave `published_files` and `bristol` to the build**, which runs both itself
  and fails rather than shipping past them.

## The build

- **The release is built and published by `.github/workflows/release.yml`**, on
  a macOS runner, from the pushed tree. Nothing is built on the user's machine.
- **`python3 src/tools/bristol/make_release.py` builds the same bundle
  locally**, for a build to look at rather than one to publish.

## The notes

- **Lead with what the release gives someone who runs Bristol**, in the order
  that matters to them, and name the surface each thing appears on.
- **Claim only what is supported.** A claim about another tool says which of its
  content loads here and stops; anything wider is false the moment someone tries
  it.
- **Define every term the notes coin**, and keep each item to what a reader
  learns from it rather than what changed to produce it.
- **Close with the first-launch step**: macOS refuses an unsigned app until it
  is allowed once in System Settings → Privacy & Security, and
  `docs/install.md` carries the wording.

## When a first-install check is required

Proving a stranger can install Bristol costs the user an afternoon and removes
the machine's instance pointer while it runs, so it is run against the change
that could break an install rather than against every release.

- **Run it when the diff since the last tag touches the install path** — the
  setup wizard, `payload.py`, `setup.py`, `slim.py`, `make_release.py`, the
  entry files at the root, or `docs/install.md`.
- **Skip it otherwise**, and say on the card which files were checked for.

## The first-install check

Two ways in: **the download**, which is how a stranger arrives, and **the
clone**, which is how a developer does. §The download covers the first; §The
clone covers the second.

### The download

Against the artifact a stranger actually gets, on the user's own machine.

1. **Do steps 1 and 2 of §The clone first.** The pointer beats every other
   resolution, so a machine still holding one never opens setup.

2. **Take the built app from the release** the workflow published, or from
   `make_release.py` where the release is not cut yet.

3. **Unzip somewhere outside the repository and open the app.** A user step. It
   passes the Gatekeeper gate the way `docs/install.md` §The first launch says
   it will; a build that opens with no warning at all was launched from a path
   macOS never quarantined, and the check did not happen.

4. **Give the placement page a scratch folder** — `~/Downloads/bristol_download`
   — then complete the wizard as in step 6 below. It passes when that folder
   holds `src/`, `docs/`, the entry files, `config/config.local.json` and a
   board, and no `data/` belonging to anyone else.

5. **Check the hand-off page** names that folder and copies a line naming it.

6. **Prove an update keeps the installation.** A user step: raise `src/VERSION`,
   rebuild, and open the new app. It passes when `src/VERSION` in the scratch
   folder rises, `config/config.local.json` is byte-identical, and the board
   still holds the card step 7 of §The clone made.

7. **Then steps 7 through 10 of §The clone**, against the scratch folder.

### The clone

1. **Note the four values the last step adopts.** A user step.

   ```bash
   cat ~/Library/Application\ Support/BristolTickets/instance.json
   ```

   **An absent pointer is a normal state here, not a stop.** Take the four
   values from the real repository instead: `repo_root` is the clone,
   `config_path` is its `config/config.local.json`, and `data_root` and
   `instance_slug` are what that file's `important_paths.tickets_db` resolves
   back to — the folder holding the installations, and the one installation's
   folder beneath it. `src/tools/config_tools/instance_pointer.py` (no
   arguments) prints the pointer; `--write` reconstructs it from exactly those
   values.

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
   rm -rf ~/Downloads/bristol_check
   mkdir -p ~/Downloads/bristol_check
   git -C <repo> archive HEAD | tar -x -C ~/Downloads/bristol_check
   ```

   // Downloads is a mounted folder and the home directory is not, so the copy
   // goes there rather than beside the repo.

4. **Install the dependencies against the copy.** A user step, in Terminal.

   ```bash
   cd ~/Downloads/bristol_check && pip3 install -r requirements.txt
   ```

   A Homebrew-managed Python refuses this; `docs/install.md` holds both ways
   round it.

5. **Launch Bristol Tickets from the copy.** A user step. The session takes the
   window from here.

   ```bash
   cd ~/Downloads/bristol_check && python3 src/tools/bristol/app.py
   ```

6. **Complete the wizard, and check what it wrote.** The session clicks
   through, naming the instance something disposable and pointing the data
   folder inside the scratch copy. Then confirm `config/config.local.json`
   exists, the enabled agents' folders exist, and `tickets.db` opens empty.

   **Give the notebook page a folder inside the scratch copy too.** An unset
   notebook resolves to no reports directory, and the report step then passes
   by writing nothing.

   **Leave the summary page's startup box ticked.** Step 8 resolves the board
   through the pointer, so a run that declines it tests the real installation
   instead of the copy.

7. **Work one card end to end in the window** — create it, close it, Clear
   Done — and confirm the report landed in that notebook folder.

8. **Run one session against the copy.** A user step: point an agent host at
   `~/Downloads/bristol_check`, open a new conversation there, and say
   `continue`. It passes when the session initializes from `src/app.md`,
   resolves config, loads an agent, prints a snapshot, and names no path
   belonging to the user.

9. **Fix every defect in the repo, never in the copy**, then rebuild the copy
   from step 3 and re-run. A fix made in the scratch copy is lost and proves
   nothing.

10. **Hand the pointer back by adopting the real installation, then delete the
    copy.** The user launches Bristol Tickets from the real repository and the
    session drives **File → Setup…**: name the installation step 1 recorded,
    choose its data folder, adopt it, and Finish with the startup box ticked.
    Adoption writes the pointer and nothing else. Deleting the copy is a
    session step.

    ```bash
    rm -rf ~/Downloads/bristol_check
    ```

## Failure modes

- **The workflow publishes a release whose notes are the first-launch line
  alone** → the notes are written after it, against the tag it created.
- **The user's real Bristol Tickets opens the scratch board afterwards** → the
  pointer was not handed back. §The clone step 10, or
  `instance_pointer.py --write` from the real repo.
- **The wizard offers to create rather than adopt** → the data folder it was
  given holds no `tickets/tickets.db`. The folder to choose is the one the
  pointer's `data_root` and `instance_slug` name together, not `data_root`
  alone.
- **`TICKETS_DB` is set in the environment** → the wizard never opens, because
  the variable suppresses first-run setup. Unset it before §The clone step 5.
- **The scratch copy resolves the real board** → either the pointer is still in
  place, or the copy was placed inside the repo. Path resolution consults the
  pointer before it walks up to the nearest `src/app.md`, so the pointer must be
  gone and the copy must sit outside.
- **A step needs more than one session** → the board carries it. Leave the card
  in `doing` at the top of its column with what remains in one comment.

## Audit

- **The published release carries the settled tag, both build artifacts and
  notes that lead with what the release gives.**
- **A scratch copy exists nowhere at the end.** It is not a deliverable.
  `~/Downloads/bristol_download` and the built `dist/` go the same way.
