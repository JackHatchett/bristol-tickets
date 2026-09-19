---
name: writers-room-project-context
description: Loads the files for whichever novel project is active at the start of a session and closes them out at the end, so the session knows the story it is working in. Use at the open and close of every session on the novel.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
---
# writers-room-project-context

Governs which novel-project files get loaded, after the charter's board
snapshot, which happens first.

## Session start

1. **Identify the active project** after the board snapshot. The config's
   project links resolve which folder is active; there is normally one, and the
   layout supports more over time.
2. **Take where the project stands from the board and nothing else** — the
   snapshot the charter already ran. What is settled, what is open and what to
   work next are cards and their comments; a file saying any of it is a second
   record that goes stale (`src/app.md` §The board is the only channel).
3. **Read that project's content-rules file** — its `AGENTS.md` or equivalent —
   before authoring or judging any content in it. Read it the first time content
   work begins in a session rather than only at session start. **Content rules
   bind every piece of work on that project**, including anything handed to a
   second model, which receives them in its brief
   (`src/skills/external-ai-bridge/references/writers_room.md`).
4. **Never bulk-read wiki files at session start.** On-demand lookup only. The
   wiki is user-authored and takes a proposal rather than a write
   (`writers_room.md` §Write Authority); there is no canon concept and nothing
   to re-vet.
5. **Never read a `private/`-equivalent personal-notes folder unless the user
   names a specific file in it.** Never list, scan or summarize that folder
   unprompted.

## On-demand lookup

When a request needs a project fact not in hand, read that project's router or
index file to find which wiki file holds it, read **that one file**, and
continue. Needing three files to answer one question means the request is
under-specified — ask rather than keep reading. Conventions:
`tools/wiki_tools/`.

## End of session

On "end of session," "update everything," or the natural end of a content
session. Where the project stands goes on the board —
`src/skills/manage-tickets/SKILL.md` §Session closure, which every agent
follows: the cards you came back to in the column that reflects reality, what
remains in a comment on the card it belongs to, and the launch in the To
Continue block.

- **Never write a state file, a session log or a decision log**, in the
  notebook or anywhere else. A settled decision is a comment on the card that
  settled it.
- **A deliverable is not state.** Prose, a proposal, a summary the user asked
  for goes to `markdown_notebook.agent_output_dir` as content he folds in, and
  says nothing about where the work stands.
- **Never regenerate the encyclopedia or recap a settled decision.**
