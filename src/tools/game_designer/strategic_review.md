# strategic_review.md — game_designer tool

A fixed briefing template for a periodic external strategic-health pass on
a game project — a different kind of collaborator than the Gemini Gem
(`protocols/game_designer/gemini_gem_bridge.md`, an ongoing creative
co-writer). This is a one-off "bring in an outside CTO" consultation: on
request only, not a routine per-session tool, and not itself a coordination
protocol since there's no ongoing back-and-forth contract to maintain
between sessions. It is deliberately **not** a specialization of
`protocols/_shared/external_ai_bridge.md` (which governs recurring external-AI
contracts) — the archetype's "review and file the return" step still applies
in spirit (see "After the review comes back" below), but a single advisory
pass needs no memory model, sync discipline, or return schema, so it stays a
tool rather than a bridge protocol.

## When to use
The user asks for a strategic gut-check on the project — phase-exit
readiness, technical-architecture risk, or blind spots neither the user nor
this agent has caught. Not for routine design or build work.

## What to hand the external advisor
Three things, uploaded or pasted together so the advisor has full context
in one pass:
1. **The brief** — this file's opening prompt (below), filled in for the
   current project.
2. **Current project state** — the project's own state file plus a short
   pull from its session-brief/changelog's most recent entries.
3. **The design overview** — whichever worldbuilding (notebook) and repo
   design files are most relevant to the
   review's focus (usually identity/premise, world/mechanics, and current
   narrative/art state) — read the project's own file names rather than
   assuming any.

## The opening prompt (fill in the bracketed fields)
```
You are being brought in as an outside strategic advisor on an indie game
project called [PROJECT TITLE] — [one-line genre/tone description].

Who's on this team:
- [User]: creative lead and final decision-maker. [Coding-experience level].
- You (strategic advisor): big-picture review only — you commission
  findings, you don't execute changes yourself.
- [game_designer / the Architect]: runs sessions with the user day to day,
  translates strategy into concrete steps, has been running this project
  since it started.
- [Any code-execution collaborator, e.g. GitHub Copilot]: [status — active
  or not yet].

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

## After the review comes back
Treat every finding as a proposal, same as any other incoming suggestion —
route it through `playbooks/game_designer/design_proposals.md` if it
touches design content, or a plain ticket
(`tools/ticket_tools/ticket_write.py add-task`) if it's a process/
architecture action item. Never apply a structural recommendation directly
just because the advisor's review sounded confident.
