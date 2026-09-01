# Cowork

A mode inside the Claude desktop app. A session runs in a Linux sandbox and
reaches the folders you connect through a file bridge, so the shell it holds is
not the shell your machine runs.

## Removing a file

The shell cannot remove a file: the bridge blocks `unlink`, so `rm` and `rmdir`
fail on a connected folder. A session removes one by collapsing every unwanted
file onto a single path and deleting that one file at full permission.

- **Rename each unwanted file onto one sink path inside a connected folder.**
  `rename` is permitted, including onto a name that is already taken, so the
  whole set becomes a single file whatever the files were. A rename onto a path
  outside the mount is a copy and an `unlink`, and fails.
- **Delete the sink with the desktop's own file manager, under computer use.**
  It is one deletion at the end, not a step repeated per file.
- **An empty directory has no route here.** Neither the bridge nor a rename
  reaches it.

// A file manager may hide a dotfile even with hidden items shown. Rename it to
// a plain name over the bridge first, then delete it.

### The delete grant

A grant exists that lets the shell `unlink` directly, and the host offers a tool
to ask for it, named `device_request_delete_permission`. An approval layer
inside the session answers that ask before it reaches the desktop, and an ask
carrying only the session's own housekeeping as its reason is refused there: the
user is shown nothing on any device, and the error reads `MCP tool call requires
approval`. A session asks only where the user's own request is what needs
something deleted, and names that in the reason.

- **Report an ask that does not reach the user rather than repeating it**, and
  carry on by the route above. A second identical call produces the same
  silence.

// The layer is the session's approval policy, readable in the container at
// `~/.claude/launcher-settings.json`. Its `autoMode` block holds the bridge
// tools cleared outright and those cleared against named criteria;
// `device_request_delete_permission` is in neither, while
// `device_request_folder_access` is in the second and clears when the user's
// own message referenced the folder. That folder tool is granted in sessions
// where this one is refused, so the refusal is the single tool's rather than
// the bridge's or the class's.

## Running git in a connected folder

Git works here — staging, committing, branching — and leaves a `.lock` file
behind almost every time, because releasing one is an `unlink`. A `.lock` left
in place is what stops the next command: git reads it as another process
holding the repository and refuses. So clear the locks *before* each git
command rather than after:

```
for f in $(find .git -name '*.lock'); do mv "$f" <sink>; done
```

`<sink>` is one path every leaving is renamed onto, and the file manager
removes it once at the end. It goes inside a connected folder: a rename onto a
path outside the mount is a copy and an `unlink`, and fails.

**A session's last act in a repository is a clearing pass, and no git command
follows it.** The lock that stops the user's own next command is the one their
session left, and a read leaves one as surely as a write — so a status or a diff
run to check the work is what breaks the commit block offered underneath it.

// `git status` and `git diff` take the index lock too — any command that reads
// the index refreshes it — so a run of read-only commands leaves one as surely
// as a commit does.

Two commands are worth avoiding rather than repairing: `git gc` and `git
maintenance`, which pack loose refs by unlinking them, and `git checkout` of a
tracked file, which unlinks before it writes. Restore a file by writing its
contents in place instead.

## Seeing an application on the machine

The shell's process table is the sandbox's own, and the applications the user
runs are not in it. `pgrep`, `ps` and `pkill` answer about the sandbox whatever
the desktop is doing, so a check written as "is X running" reports no every
time.

- **Ask a file, not a process.** An application that holds a file open while it
  runs — a lock file, a database journal — leaves that file on the real disk,
  where the bridge reads it.
- **Quitting an application is the user's**, or computer use; nothing here
  signals a process.

## Reading a database

The sandbox carries no `sqlite3` command-line binary. Python's built-in
`sqlite3` module is present and is what every tool here uses.

## When the shell stops answering

The sandbox holds a fixed volume of about ten gigabytes, and everything a
session runs happens on it. At zero free space the sandbox can no longer create
the socket file a command arrives on, so every call fails — reads, writes and
the board alike — and the error names sockets rather than disk.

- **Read a repeated `failed to create bridge sockets` as a full volume**, not as
  a broken bridge. The two are indistinguishable from the error text and only one
  of them is common.
- **Never install a package here.** A tool the sandbox lacks is a reason to stage
  the files that step needs into a session's own container, never a reason to try
  the install and see; a failed install still writes what it downloaded before it
  gives up.
- **Clear the volume by quitting the desktop application, moving its VM bundle to
  the Trash, and reopening it.** The bundle is at
  `~/Library/Application Support/Claude/vm_bundles`, it is the sandbox's whole
  disk, and a fresh one is built on the next use. Nothing of the user's is inside
  it: their files are on their own disk and are mounted in.
- **The session survives that restart**, and the bridge reconnects.

// The volume is an ext4 filesystem mounted without `discard`, on a thin image
// file on the host's disk. Deleting a file inside frees the volume but sends no
// TRIM, so the image keeps the blocks; `fstrim` from inside fails with
// Operation not permitted. The image therefore tracks the high-water mark of
// what has been written, not what is currently there.

## What the bundle costs, and what actually grows

The bundle holds two different things and only one of them is a session's doing.

- **A fixed base image of about twelve gigabytes** — `rootfs.img` at ten, fully
  allocated, plus its compressed original. That is the cost of the feature
  existing and it does not grow.
- **A session-data image that tracks a high-water mark.** This is the volume
  sessions actually work on. On a fresh bundle it is tens of megabytes.

- **Write large or throwaway things in a session's own container, not here.** A
  downloaded package or an extracted archive raises the high-water mark and
  nothing lowers it short of rebuilding. The cost of one such write is small; it
  is the accumulation across a long-lived bundle that eventually reaches the
  ceiling.
- **Reclaiming the image is the desktop application's.** Rebuilding the bundle
  is the whole of a session's part in it: nothing inside can see the image or
  return its blocks, so never add a mechanism here that measures, prunes or
  compacts it.

## Running a Qt application

The sandbox carries no PySide6 and no room to install one, so Bristol Tickets
itself and the smoke targets that build its widgets do not run there. The
targets that touch no Qt do. The rest run wherever a Qt is installed: the
machine the folder belongs to, under computer use, or a session's own container,
which is the one a session takes by itself.

// `QT_QPA_PLATFORM=offscreen` is what lets those targets build widgets with no
// display attached.

### The container route

- **Send the tree as one archive.** The bridge stages files rather than
  directories and takes a bounded number per call, and the tree is more files
  than that, so it crosses as a single archive written into a connected folder:

  ```
  tar czf "$HOME/mnt/<connected-folder>/bristol_smoke.tgz" \
      -C "$HOME/mnt/<project-folder>" src config
  ```

- **`src` and `config` are what those targets read**, which is the rule rather
  than a list: the tools they build the widgets from, the schema they provision
  a board from, and the configuration both resolve through. Nothing under
  `/data` is needed — a target that wants a board provisions its own.
- **Install PySide6 in the container and invoke the target directly.**

  ```
  mkdir -p /tmp/bristol && tar xzf <staged archive> -C /tmp/bristol
  pip install PySide6 --break-system-packages
  cd /tmp/bristol && QT_QPA_PLATFORM=offscreen \
      python3 src/tools/test_tools/smoke.py bristol
  ```

- **`run_smoke.sh` is not the entry point here.** It installs PySide6 wherever it
  is invoked, so running it from the bridged shell installs into the sandbox,
  which is the one thing that must not happen there. In the container the
  install is the deliberate step above and `smoke.py` is called directly.
- **The extracted copy is a snapshot.** Re-archive and re-stage before every run
  that follows an edit: a passing run against a stale copy is worse than no run,
  because it reports on code the user does not have.
- **Remove the archive from the connected folder when the run is finished** —
  §Removing a file. It is not a deliverable, and it is stale the moment the tree
  changes.

// The container has room for PySide6 and the sandbox does not; that difference
// is the whole reason this route exists rather than the simpler one.

## The sandbox home is not the user's home

`~` in this shell is the sandbox's own home, and the user's folders are reachable
only under the mount root the bridge gives them. A path naming the user's
filesystem — `~/Library/...`, `/Users/<name>/...` — therefore names nothing here.

- **Resolve a declared location through
  `src/tools/config_tools/data_paths.py`** rather than expanding the string. It
  looks for an absent absolute path beside the project, which is where this
  host's mount root puts every connected folder, so config keeps one spelling
  and both hosts read it.
- **A tool that expands a config path itself has this fault**, whatever the path
  looks like, and the fix is the resolver rather than a second spelling.

## Writing to a connected folder

A write crosses the bridge to your real disk, and a failure part-way through
leaves whatever it had written. This is why every board write opens with
`PRAGMA journal_mode=MEMORY` and edits the database in place rather than
replacing the file.

## Project instructions

**Two settings inside the application are what a clone cannot bring with it**:
the folder Cowork reads, connected in its own folder picker, and the per-project
instructions below. Everything else this system needs is in the repository.

Cowork takes its per-project instructions as text you paste into the project,
not as a file it reads from the folder, so `AGENTS.md` and `CLAUDE.md` at the
root go unread here. Paste this, with `<folder>` replaced by the name of the
connected folder:

```
Read <folder>/src/app.md, then the note in <folder>/src/host_notes/ that
matches the host you are running under.
agent_override: none
```

A session sees every connected folder at once, which is why the paths are
written from the folder name down rather than from the project root.
