# Host notes

A **host** is the application a session runs inside: it loads per-project
instructions, reads and writes a folder you choose, and runs `python3`. Any
host that does those three things can run this system.

A **host note** holds what is true of one host and no other — a capability it
lacks, a mechanism only it has, a limit its sandbox imposes. Everything else
about how a session behaves lives in `src/app.md` and the charters, written for
no host in particular.

## The notes

| File | Host |
| --- | --- |
| `cowork.md` | Cowork, a mode in the Claude desktop app |

A host with nothing peculiar about it needs no note, and most do not.

## How a session finds one

The host reads whichever entry file it is built to read — `AGENTS.md` or
`CLAUDE.md` at the project root — and each says the same two things: read
`src/app.md`, and read the note here that matches the host you are running
under. The table above is the whole lookup.

## What belongs in one, and what never does

- **A note states a property of the runtime**, then how to work with it. It
  never restates a rule that `src/app.md` or a charter already states.
- **No document outside this folder tests which host is reading it.** A rule
  that would need `if you are <host>` is two rules: the host-neutral one, which
  goes where the rule lives, and the mechanism, which goes here.
- **A note is not a preference.** How the board behaves is configuration and
  belongs in `/config`.

Adding support for a host is: confirm it does the three things above, add its
entry file if it reads one no other host reads, and add a note here only if
something about it surprised you.
