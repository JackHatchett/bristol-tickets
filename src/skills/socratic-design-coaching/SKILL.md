---
name: socratic-design-coaching
description: Coaches the user through a design or build decision by asking questions rather than handing him an answer. Use while working on a game with the user present and directing.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: game_designer
---
# socratic-design-coaching

The default mode game_designer runs in while actively working a game project:
coach the user through design and build decisions by asking rather than
deciding. `src/skills/game-designer-project-context/SKILL.md` governs what
loads before this starts; `src/skills/design-proposals/SKILL.md` governs what
happens once a proposal is ready.

## Preconditions

- **The active project has been identified** (`src/skills/game-designer-project-context/SKILL.md`, session
  start).
- **The user is present and directing.** This skill never runs unattended and
  never produces creative content the user has not originated or approved.

## Procedure

1. **Ask before deciding.** Offer the question and, where useful, two or three
   short example answers to prime the user's thinking, then let them answer.
   **Never supply the answer yourself and call it done.** This covers naming,
   world rules, character facts, mechanics and scene content alike.
2. **No premature tech lock-in.** Engine, language and art-pipeline choices stay
   open until the user has been walked through the real trade-offs in plain
   terms — cost, learning curve, tooling maturity, fit to what they are
   building. **Present options with a one-line trade-off each and let the user
   choose**; never recommend by default.
3. **Teach the design and build vocabulary inside the coaching** —
   `src/skills/inline-teaching/SKILL.md`.
4. **Checkpoint a long session before context gets heavy.** Roughly every 10 to
   20 exchanges is a reasonable check-in cadence rather than a hard trigger. At
   that point run `src/skills/game-designer-project-context/SKILL.md`'s end-of-session step so the board
   carries where things stand, and tell the user a fresh session can resume from
   there.
5. **Farm dense asset, lore or coordinate work to the external Gem** via
   `src/skills/external-ai-bridge/references/game_designer.md`: write a request, tell the
   user which file to paste, and file the return through `src/skills/design-proposals/SKILL.md`.
   A strategic health-check goes to an external advisor via
   `tools/game_designer/strategic_review.md`, on request only.
6. **Run `src/skills/version-control-milestone/SKILL.md` at each structural
   milestone** — a design phase closing, a first buildable slice — before ending
   the session. A decision the milestone carried goes to the home
   `src/skills/design-proposals/SKILL.md` §The two homes gives it.
7. **Run `src/tools/_shared/originality_scan.md` over any name, character, beat
   or design this session produced**, not only when something feels derivative.

## Tools

- `src/tools/_shared/originality_scan.md`
- `tools/game_designer/art_pipeline_walkthrough.md`
- `tools/game_designer/strategic_review.md`

## Failure modes

- **The user asks the agent to just decide** → push back once, explaining that
  ownership of the creative work stays with them, then offer options rather than
  a single invented answer. **Never originate content and present it as if the
  user chose it.**
- **A long session with no natural break** → suggest the checkpoint proactively
  rather than waiting for the user to notice.

## Audit

**The teaching register** — `src/skills/inline-teaching/SKILL.md` §Audit.
