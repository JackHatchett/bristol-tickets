# Cowork

A mode inside the Claude desktop app. A session runs in a Linux sandbox and
reaches the folders you connect through a file bridge, so the shell it holds is
not the shell your machine runs.

## Removing a file

The bridge blocks `unlink` and allows `rename`, including onto a name that is
already taken. So `rm` and `rmdir` fail on a connected folder, and `mv` does
not: renaming every unwanted file onto one path collapses them all into a
single file, whatever they were. Delete that one through the desktop's own file
manager, under computer use, which resolves at full permission and moves it to
the trash.

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
removes it once at the end.

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
