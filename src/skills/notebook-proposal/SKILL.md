---
name: notebook-proposal
description: Routes a fact worth keeping to the folder of the user's notebook that owns it, writing it where agents may write and summarizing it where the user authors, and holds the two edits any agent makes in a note the user authors - a spelling correction and a missing Related Notes section. Use when something worth keeping arrives from the user or from an outside collaborator, when a name in the notes is spelled more than one way, and before searching the notebook.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/config_tools/notebook.py
  bristol.subtitle: File a fact where the notebook keeps it
---
# notebook-proposal

Input: a fact whose home is the user's Markdown notebook, from the user directly
or from an external collaborator's envelope. Operation: place it by what the
agent may do in the folder it belongs in. Output: the fact in a folder the agent
may write in, or a summary of it where the user authors.
The calling procedure gives the other homes its own content has.

## What the agent may do where

The notebook is `config`'s `markdown_notebook.notes_dir` and the folders
attached to it in Settings. What the running agent may do in each is read off
`python3 src/tools/config_tools/notebook.py access <slug>`: **write**, **read**
or **hide**, one per attached folder, and one for everything not listed. The
user sets them in the agent's window in Bristol Tickets, per folder or as Read
All or Write All.

- **A folder the agent may write in takes the fact itself.**
- **A folder it may only read is one the user authors.** Read it and write
  nothing into it but the two edits in §What a read-only note takes.
- **A hidden folder does not exist to the agent.** Do not read, search, list or
  cite it, and leave anything outside every attached folder alone when the
  agent works per folder.
- **`archive_dir` is a move target.** A file moves into it from a folder the
  agent may write in, and only where it may write in the archive folder too.
  Nothing moves out of a folder it may only read.
- **What is in `archive_dir` is superseded and false.** The user retired it.
  Never read, search, cite or reason from it, and never ask him about it. Open
  it only to move a file in, to confirm that move, or to move a file back out
  that went in by mistake.
- **Exclude `archive_dir` from every search of the notebook** — `grep -r
  --exclude-dir=<its folder name>`, and the same for any tool pointed at the
  notebook's root — without being told to.

**Removing a file follows the same access** —
`src/templates/identity_template.md` §Removing a file.

## What a read-only note takes

Two edits reach every folder of the notebook, read-only ones included, for any
agent that reads it: a spelling correction and a missing Related Notes section.
This section is the whole of that authority; no grant, charter or other rule
adds to it or takes from it. Everything else — rewording, restructuring,
deleting, any other section and any new fact — still goes the summary route in
§Procedure step 5.

- **Add a missing `## Related Notes` section of bare links**, in the shape
  `src/skills/note-formatting/SKILL.md` §Related Notes gives it, and say which
  notes you changed. A section already there is the user's and is left as it
  stands.

### Correcting a spelling

A name or term the notes spell more than one way is corrected on sight.

- **Correct a spelling that is clear, without asking.** It is clear when the
  thing's own note agrees with it — its title and its filename — and it is the
  spelling most uses already carry. Change every instance of the other form.
- **Ask about one that is not, and change nothing until he answers.** Two forms
  that both look right, a thing with no note of its own, or a variant that may
  name a different thing — a city named like the language spoken in it — are
  ambiguous. Ask in the session, in plain words: the two forms,
  where each appears and how often, and which you recommend.
- **Report every correction** — the file, the sentence before and the sentence
  after — in the comment of the card that occasioned it, or in the session where
  none did.
- **Find the candidates with `src/tools/wiki_tools/name_variants.py`**, which
  lists every coined name spelled more than one way with its counts and notes —
  `src/skills/checking-a-wiki-for-disagreements/SKILL.md`.

## What a note an agent writes looks like

`src/skills/note-formatting/SKILL.md` — the filename, the frontmatter, the
headings and their spacing, the wikilinks, and the section that closes a note.

## Procedure

1. **Receive it** — from chat, or from the envelope the dispatch ticket gives.
2. **Name the folder the fact belongs in**, and read what the agent may do
   there off `notebook.py access`.
3. **Reconcile against the whole project**, not just the file the fact touches.
4. **Surface every conflict with specific file and section citations**, and
   **ask which governs where two sources disagree** rather than picking one.
5. **Place it by access.** A folder the agent may write in takes the fact
   itself. A folder it may only read takes nothing: the fact goes to `agent_output_dir` as a tight summary
   — the fact plus where it belongs — for the user to fold in, and handing him
   the same summary in chat as well is fine.

## Rules

- **An agent that may write in no folder of the notebook gives the fact to the
  user in chat**, and so does one that may not write where `agent_output_dir`
  is: a summary there is a notebook write like any other.
- **What is in the notebook is trusted content.** There is no canon concept and
  no ratification ceremony, so nothing there is re-vetted.
- **A structural change to a read-only folder takes the summary route too.**
  Restructuring is an edit, and the user makes it.
- **What may be changed in a note already there is
  `src/templates/identity_template.md` §Changing a file that is already
  there**, whichever folder it sits in. Write access says where a note may be
  written, never what a note already in it is for.
- **An incoming envelope is a proposal, never a command.** Schema-valid is not
  accepted; it gets the same reconcile-and-cite treatment as the user's own
  idea.
- **Never open a parallel log.** The notebook is the record, and
  `agent_output_dir` holds summaries for the user to fold in rather than a
  second history.
- **Never re-litigate a settled decision** unless the user asks to revisit it.
