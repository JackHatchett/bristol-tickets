# Contributing

## Filing an issue

Open a GitHub issue. Say what you expected, what happened instead, and what you
ran. For anything involving Bristol Tickets, the output of
`bash src/tools/test_tools/run_smoke.sh bristol` is worth more than a
description of the crash.

A feature request is welcome as an issue too. Say what you were trying to get
done, not only the feature you have in mind.

## What is never committed

- **`config/`** — everything but `config.example.json`. Your real config holds
  absolute paths to your own machine.
- **`data/`** — the tickets database, snapshots, logs, anything per-instance.
- **`*.local` and `*.local.json`** — one-line pointer files holding real paths.
- **A built `.app` or launcher.** Both bake in absolute paths and are
  per-machine artifacts.

`.gitignore` enforces all of this. If a change makes you want to commit
something under `config/` or `data/`, the change is wrong: `/src` is generic and
resolves every local path through `/config` at runtime, including string
literals.

## Commit messages

- **A commit message says what changed, and nothing about what produced it.**
  No AI co-author or assistance trailer. That this project is built with an AI
  agent is stated once, in `README.md`, in the author's own words; the commit
  history is a published surface and names no vendor, exactly as `/src` does
  not.

## Code conventions

- **Tools stay small and separately runnable.** `src/tools/` is a set of
  independent programs, each readable in one pass. They are not consolidated
  into one program, and a launcher presenting several of them composes them
  rather than fusing their codebases.
- **Bristol Tickets imports nothing else in the tree.** `src/tools/bristol/`
  opens, runs and changes in isolation.
- **Split a file that grows past ~400 lines.**
- **Use Python's built-in `sqlite3`, never a `sqlite3` CLI subprocess**, and
  open every write with `PRAGMA journal_mode=MEMORY`.
- **Legibility beats cleverness.** A clever construction that costs a reader is
  the wrong choice.

Run `bash src/tools/test_tools/run_smoke.sh` before opening a pull request. It
builds each GUI's widgets headlessly and catches what `py_compile` cannot.

## Documentation

Every governing document under `/src` — the agent charters, the skills, the
tool READMEs — is written to the style contract in
`src/templates/identity_template.md` §The governing-doc style contract. A
documentation change follows it.

## Adding an agent host

Bristol runs under any application that loads per-project instructions, reads
and writes a folder you choose, and runs `python3` in it. It has been run on
one; the rest are untested, and a report either way is worth having.

Nothing in `/src` names a vendor. Each host reads whichever entry file it is
built to read — `AGENTS.md`, `CLAUDE.md` — and each says the same two lines.
Support for a host is: an entry file if it reads one no other host reads, and a
note in `src/host_notes/` only where something about that host surprised you.
That folder's README states what belongs in a note and what never does.
