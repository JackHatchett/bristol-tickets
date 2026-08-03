# design_proposals — game_designer playbook

Triggered when a design idea or change is proposed, by the user directly or as
an incoming RETURN from the external Gem
(`protocols/game_designer/gemini_gem_bridge.md`). The notebook half of it runs
on `src/playbooks/_shared/notebook_proposal.md`.

## The two homes

- **Worldbuilding** — story, characters, world, lore, scenes, tone. The
  notebook, per the shared playbook.
- **Game design and production** — mechanics, art direction, art pipeline.
  Lives in the project repo's `design/` folder, edited directly as ordinary
  git-tracked docs. No proposal status, no gate.

Reconciliation spans both: notebook worldbuilding plus repo `design/`.

## This agent's additional steps

1. **Run `src/tools/_shared/originality_scan.md` over any new name, character,
   beat or design in it.** A reported resemblance stays flagged until the user
   clears it.
2. **Close the ticket where the proposal resolves an open blocker**
   (`project_context.md`).
3. **Move a Gem request and return pair into `handoffs/archive/<request_id>/`**
   once handled.
