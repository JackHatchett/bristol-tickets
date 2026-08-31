# Strategic Review

Input is a game project's current state and design material. Operation is a
single outside advisory pass, run in an external service. Output is a set of
findings, each handled as a proposal.

- **Run it on a request for a strategic gut-check** — phase-exit readiness,
  architecture risk, blind spots. Never for routine design or build work.
- **Hand the advisor everything in one pass**: the filled-in brief below, the
  project's own state file with its most recent changelog entries, and whichever
  worldbuilding and design files bear on the review's focus. Read the project's
  actual filenames rather than assuming any.
- **Route every finding back as a proposal** — through
  `src/skills/design-proposals/SKILL.md` where it touches design content,
  or as a card (`tools/ticket_tools/ticket_write.py add-task`) where it is a
  process or architecture action. A confident review is still a proposal.

`src/skills/external-ai-bridge/SKILL.md` governs a recurring external-AI
contract; a single pass carries no memory model, sync discipline or return
schema, so it needs none of it.

## The brief

```
You are being brought in as an outside strategic advisor on an indie game
project called [PROJECT TITLE] — [one-line genre/tone description].

Who's on this team:
- [User]: creative lead and final decision-maker. [Coding-experience level].
- You (strategic advisor): big-picture review only — you commission
  findings, you don't execute changes yourself.
- [game_designer]: runs sessions with the user day to day, translates
  strategy into concrete steps, has been running this project since it
  started.
- [Any code-execution collaborator]: [status — active or not yet].

What we want from this review:
1. Phase-exit assessment: are we actually ready to call the current phase
   done, by its own stated exit criteria?
2. Next-phase readiness: is the next deliverable well-defined enough to
   start, or are there gaps that would surface immediately?
3. Technical architecture review: any concerns about the current engine/
   language/pipeline choice given what's actually being built?
4. Risk identification: name the biggest risks to this project succeeding.
   Be direct.
5. Blind spots: what hasn't the team considered that an outside advisor
   would flag immediately?

Operating rules for this review:
- Be direct — the user can handle hard feedback.
- Define technical jargon inline if the user's own comfort level (stated
  above) is low.
- Treat everything marked LOCKED in the attached materials as settled
  unless you have a strong architectural reason to flag a conflict — if you
  do, say so explicitly rather than quietly building around it.
- Anything you propose is a proposal, not a decision — nothing changes
  until the user and game_designer review it together.
```
