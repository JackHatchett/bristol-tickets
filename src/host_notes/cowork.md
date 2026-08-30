# Cowork

A mode inside the Claude desktop app. A session runs in a Linux sandbox and
reaches the folders you connect through a file bridge, so the shell it holds is
not the shell your machine runs.

## Removing a file

The shell cannot remove a file until the session holds a delete grant: the
bridge blocks `unlink`, so `rm` and `rmdir` fail on a connected folder. A
session asks for that grant with the tool its host offers for it.

- **Ask at session start, for every connected folder, before any work.** By the
  time a session needs the grant it has usually already left something behind,
  and a grant arriving then is one the user answers while blocked. One ask, once,
  is also the whole cost.
- **Report an ask that does not reach the user rather than repeating it.** The
  request can be refused by the host before it is ever shown, and a second
  identical call produces the same silence.

// The tool has been named `device_request_delete_permission`. Whether a
// session holds it is a property of that session, so look for it rather than
// assuming either way.

Two things hold when a session has no such tool. `rename` is permitted,
including onto a name that is already taken, so renaming every unwanted file
onto one path collapses them into a single file whatever they were. And the
desktop's own file manager, under computer use, deletes that one file at full
permission. That pair is the fallback, not the first move.

// A file manager may hide a dotfile even with hidden items shown. Rename it to
// a plain name over the bridge first, then delete it.

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
machine the folder belongs to, under computer use, or a session's own container
with PySide6 installed and the tree copied into it.

// `QT_QPA_PLATFORM=offscreen` is what lets those targets build widgets with no
// display attached.

## Writing to a connected folder

A write crosses the bridge to your real disk, and a failure part-way through
leaves whatever it had written. This is why every board write opens with
`PRAGMA journal_mode=MEMORY` and edits the database in place rather than
replacing the file.

## Project instructions

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
