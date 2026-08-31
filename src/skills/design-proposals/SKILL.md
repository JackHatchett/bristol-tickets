---
name: design-proposals
description: Turns a proposed design or world change into a written proposal filed where that kind of content lives. Use when a mechanic, an art direction, or a piece of the game's world is suggested.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: game_designer
---
# design-proposals

A design idea or change proposed by the user directly, or arriving as a RETURN
from the external Gem (`src/skills/external-ai-bridge/references/game_designer.md`). The
notebook half of it runs on `src/skills/notebook-proposal/SKILL.md`.

## The two homes

- **Worldbuilding** — story, characters, world, lore, scenes, tone. The
  notebook, per `src/skills/notebook-proposal/SKILL.md`.
- **Game design and production** — mechanics, art direction, art pipeline.
  Lives in the project repo's `design/` folder, edited directly as ordinary
  git-tracked docs. No proposal status, no gate.

Reconciliation spans both: notebook worldbuilding plus repo `design/`.

## This agent's additional steps

1. **Run `src/tools/_shared/originality_scan.md` over any new name, character,
   beat or design in it.** A reported resemblance stays flagged until the user
   clears it.
2. **Close the ticket where the proposal resolves an open blocker**
   (`src/skills/game-designer-project-context/SKILL.md`).
3. **Move a Gem request and return pair into `handoffs/archive/<request_id>/`**
   once handled.
