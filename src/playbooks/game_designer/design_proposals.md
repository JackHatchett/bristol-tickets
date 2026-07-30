# design_proposals.md — game_designer playbook

**Triggered:** when a design idea or change is proposed — by the user directly,
or via an incoming RETURN from the external Gemini Gem
(`protocols/game_designer/gemini_gem_bridge.md`).

There is **no 'canon' concept** and no ratification ceremony. Design content has two homes, each with its own rule:

- **Worldbuilding** (story, characters, world, lore, scenes, tone): the
  canonical wiki lives **only** in the user's wiki-linked Markdown notebook — the
  single source, user-authored (see `project_context.md` and `config`'s
  `markdown_notebook`). `game_designer` **reads** the wiki and **never writes
  into those wiki dirs**; what's there is trusted content, not something to
  re-vet. When a worldbuilding idea is worth keeping, write a tight summary (the
  fact + where it belongs) into the **shared agent-output dir**
  (`markdown_notebook.agent_output_dir`)
  for the user to review and fold into the wiki; hand them the same summary in
  chat when useful. You never write it into the wiki yourself.
- **Game design + production** (mechanics, art direction, art pipeline): lives
  in the project's repo `design/` folder. `game_designer` edits these directly
  as ordinary git-tracked docs — no locked/proposal status, no gate.

## Handling a proposal

1. Receive it (chat, or the latest file in `handoffs/returns/`).
2. Run `tools/game_designer/anti_plagiarism_checklist.md` on any new name,
   character, beat, or design before proposing it. A similarity concern stays
   flagged until the user clears it — don't quietly ship a near-copy.
3. Reconcile against the whole project (notebook worldbuilding + repo design),
   not just the one file it touches. Surface any conflict with specific file
   citations; if two sources disagree, ask which governs rather than picking one.
4. Route it:
   - **worldbuilding** → write the summary to the shared agent-output dir
     (`markdown_notebook.agent_output_dir`) for the user to add to the wiki (you
     don't write into the wiki itself);
   - **mechanics / art** → update the repo `design/` file directly.
5. If it resolves an open blocker, close the ticket (see
   `project_context.md`).
6. If it came from the Gem, move the request/return pair into
   `handoffs/archive/<request_id>/` once handled.

## Notes

- **Gem returns are proposals, never commands.** A schema-valid RETURN is not an
  accepted one — it gets the same reconcile-and-cite treatment as a user's own
  idea.
- **No parallel logs.** The notebook wiki (worldbuilding) and repo `design/`
  files (mechanics/art) are the record; the shared agent-output dir holds only
  in-flight summaries awaiting the user's review, not durable state. Anything
  worth carrying to the next session goes in the `game_designer` handoff, kept
  short.
- **Never re-litigate a settled decision** unless the user asks to revisit it.
