# Cowork

A mode inside the Claude desktop app. A session runs in a Linux sandbox and
reaches the folders you connect through a file bridge, so the shell it holds is
not the shell your machine runs.

## Removing a file

The shell cannot remove a file: the bridge blocks `unlink`, so `rm` and `rmdir`
fail on a connected folder, and so does a `mv` whose destination is outside the
one it starts in. A session removes files in two moves, collapse then delete,
and carries out both itself.

- **Rename every unwanted file onto one sink path at the root of the connected
  folder that holds them.** `rename` is permitted, including onto a name already
  taken, so the whole set becomes a single file whatever the files were. Each
  connected folder needs its own sink, because a rename cannot leave the folder
  it starts in. The sink belongs at that folder's root and never inside a source
  tree: a session that stops early leaves its sink where it put it, and among
  the files a project is made of is the one place that damages.
- **Delete the sink through the desktop's file manager, under computer use,
  before the session ends.** One deletion at the end, not a step repeated per
  file.
- **An empty directory has no route here.** Neither the bridge nor a rename
  reaches it.

The file manager's menus do not open while it runs in the background, so this
one step takes the screen: request full control, select the sink, move it to the
Trash, release control.

### The delete grant

A grant exists that lets the shell `unlink` directly, and the host offers
`device_request_delete_permission` to ask for it. The session's own approval
policy answers that ask before the desktop sees it and returns `MCP tool call
requires approval`.

- **Ask where the user's own request is what needs something deleted**, and name
  that request in the reason.
- **Read that error as this session not holding the grant**, and finish the
  deletion by the route above. Repeating the call produces the same error.

## Running git in a connected folder

Git works here — staging, committing, branching — and leaves a `.lock` file
behind almost every time, because releasing one is an `unlink`. A `.lock` left
in place is what stops the next command: git reads it as another process
holding the repository and refuses. So clear the locks *before* each git
command rather than after:

```
for f in $(find .git -name '*.lock'); do mv "$f" <sink>; done
```

`<sink>` is the one path every leaving is renamed onto, at the root of the
connected folder holding the repository — §Removing a file places it and says
what removes it.

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
targets that touch no Qt do, and a session's own container has room for the
install.

The bridge stages files rather than directories and takes a bounded number per
call, so a tree crosses it as one archive written into a connected folder.

**The route itself is `src/skills/checking-a-bristol-change/SKILL.md`.**

// `QT_QPA_PLATFORM=offscreen` is what lets those targets build widgets with no
// display attached.

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
root go unread here. Paste this — the entry file's own text, with `<folder>`
replaced by the name of the connected folder, and kept in step with it:

```
Read <folder>/src/app.md, then the note in <folder>/src/host_notes/ that
matches the host you are running under.

A session that will only read is exempt from both, and from the identity and
the queue they lead to - a scheduled briefing, a lookup, a question answered
out of a file. Read what was asked for, answer, and stop. A session that turns
out to need a write starts over at the top of these instructions, before the
write.

agent_override: none
```

A session sees every connected folder at once, which is why the paths are
written from the folder name down rather than from the project root.
