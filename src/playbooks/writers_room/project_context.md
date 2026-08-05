# project_context — writers_room playbook

Always-on: read at the start and close of every session. It governs which
novel-project files get loaded, after the charter's board snapshot, which
happens first.

## Session start

1. **Identify the active project** after the board snapshot. The config's
   project links resolve which folder is active; there is normally one, and the
   layout supports more over time.
2. **Read that project's own state file** — its `STATE.md` or equivalent — for
   the previous session's updates and the recommended next focus. Echo a short
   summary before waiting on the user: current focus, open blockers, the last
   handful of decisions.
3. **Read that project's content-rules file** — its `AGENTS.md` or equivalent —
   before authoring or judging any content in it. Read it the first time content
   work begins in a session rather than only at session start. **Content rules
   bind every piece of work on that project**, including anything handed to a
   second model, which receives them in its brief
   (`protocols/writers_room/second_model_bridge.md`).
4. **Never bulk-read wiki files at session start.** On-demand lookup only. The
   wiki is user-authored and read-only to this agent (`writers_room.md` §2.6);
   there is no canon concept and nothing to re-vet.
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
session. The project's state file and decision log live in the user-authored
wiki, which is read-only to this agent, so **prepare these as summaries in
`markdown_notebook.agent_output_dir` for the user to fold in** rather than
writing the wiki files yourself:

1. **The state update** — current focus, blockers, the most recent settled
   decisions, and a pointer to this session's log entry.
2. **A short session log entry** — a diff since last time rather than a
   snapshot. A few lines is normal.
3. **Never regenerate the encyclopedia or recap a settled decision.**

## The project state file is a scoped exception

This framework holds work state in `tickets.db` and nowhere else (`src/app.md`
§The board is the only channel). **The novel's project state file is a
deliberate exception**, the same shape career_coach makes for its applications
tracker: it tracks the novel's narrative progress — what is settled in the
story, what is still open in the worldbuilding — not this agent's operational
tasks, which stay on its epic. **Never collapse the two, and never migrate this
file's contents into the board.**
