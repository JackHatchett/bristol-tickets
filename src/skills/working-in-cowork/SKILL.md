---
name: working-in-cowork
description: The routes a session takes in Cowork, whose shell cannot remove a file — how a file is removed, how git is run in a connected folder, how a shell that has stopped answering is brought back, and where a step that needs a package or Qt is run instead. Use when a delete is refused, before running git in a connected folder, when calls start failing whatever they ask for, or when a step needs something the sandbox cannot hold.
license: MIT
compatibility: A session running in Cowork, a mode in the Claude desktop app, with at least one folder connected to it.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/test_tools/smoke.py
---
# working-in-cowork

Cowork runs a session in a Linux sandbox and reaches the folders the user
connects through a file bridge, so the shell it holds is not the shell the
user's machine runs. Each route below is for one step that difference changes.
Take one when the step in front of you is refused, never in advance of it.

## Removing a file

Input: files to remove. Operation: collapse, then delete. Output: none of them
on disk, and nothing left where they were.

1. **Rename a file onto the file that replaces it, where one exists.** A file
   moved into its new home leaves its old one by the same call, and no sink is
   involved.
2. **Rename every other unwanted file onto one sink path.** A rename onto a name
   already taken is what makes a whole set one file.
3. **Put the sink at the root of the connected folder holding those files, never
   inside a source tree.** A rename cannot leave the folder it starts in, so
   each connected folder needs its own; and a session that stops early leaves
   its sink where it put it, which among the files a project is made of is the
   one place that damages.
4. **Delete the sink through the desktop's file manager**, once, at the end.
   This step takes the screen: request full control, select the sink, move it to
   the Trash, release control.

- **Ask for the delete grant whenever something has to go** — the user's own
  request, or this system's own leftovers under
  `src/templates/identity_template.md` §Removing a file — and name in the
  reason what will be deleted.
  `device_request_delete_permission` is the ask, and a grant makes `rm` work
  directly for the rest of the session.
- **An empty directory is what this route leaves.** Neither the bridge nor a
  rename reaches one: say it is there and stop.

## Running git in a connected folder

- **Clear the locks before each git command, never after.**

  ```
  for f in $(find .git -name '*.lock'); do mv "$f" <sink>; done
  ```

  `<sink>` is the path §Removing a file places.
- **End a session in a repository with a clearing pass, and run no git command
  after it.** A command run to check the work leaves the lock that stops the
  user's own next one, and a read leaves one as surely as a write.
- **Restore a tracked file by writing its contents in place**, never with `git
  checkout`.
- **Never run `git gc` or `git maintenance`.**

## When the shell stops answering

- **Rebuild the sandbox's volume where calls start failing whatever they ask
  for**, reads and board writes alike. Quit the desktop application, move
  `~/Library/Application Support/Claude/vm_bundles` to the Trash, and reopen it.
  That bundle is the sandbox's whole disk and a fresh one is built on next use;
  nothing of the user's is inside it, and the session survives the restart.
- **Never install a package in this shell**, and never write a large or
  throwaway file into a connected folder. Both raise a high-water mark that
  only the rebuild above lowers.
- **Run a step that needs a package, or a library the sandbox lacks, in the
  session's own container**, and carry back only what it produced.

## Running the Qt smoke targets

- **Take the archive route in `src/skills/checking-a-bristol-change/SKILL.md`**
  for the two targets that build widgets, and install PySide6 in the session's
  own container rather than here.
- **A tree crosses to that container as one archive written into a connected
  folder.** The bridge stages files rather than directories, and a bounded
  number of them per call.

## Asking about the machine

- **Ask a file whether an application is running, never a process.** The shell's
  process table is the sandbox's own, and an application that holds a file open
  while it runs leaves that file where the bridge reads it.
- **Quitting an application is the user's, or computer use.**

## Audit

**Whether a sink this session created is gone**, and **whether any lock this
session's git commands left is cleared.**
