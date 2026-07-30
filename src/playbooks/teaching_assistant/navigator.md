# Navigator — teaching_assistant Playbook (Mode 2)

## Purpose
Return a bounded recommendation of what to study next. Does not teach. Does
not generate files. Does not decide priority — the board already did.

## The one rule this playbook exists to obey

**Work state comes from the board and only from the board.** What is in
progress, what is finished, what comes next, and in what order are facts held
in `tickets.db`. This playbook may not re-derive any of them from a file on
disk. Computing a ranking of its own out of `progress.json` would be a second
next-action engine competing with the board.

`syllabus/progress.json` is a **file manifest**, not a tracker. The only
questions an agent may ask it are content questions: does this lesson exist,
what is its topic, what is its filename, has the file been generated. Any
status-shaped field that happens to sit in that JSON (`current_lesson`,
`course_complete`, `lesson_complete`, `studied`, `mastery`, `tutored_on`) is
**stale by definition and must not be read to decide anything.** The HTML
renderer paints some of them as badges in generated output; a generated
artifact displaying a value is not a channel an agent reads back.

## Preconditions
The board is readable. Run `python3 src/tools/ticket_tools/agent_status.py
teaching_assistant` — that is the input to this playbook.

## Procedure

**Step 1 — Read the board.** `agent_status.py teaching_assistant` returns this
agent's own active-stage tasks in precedence order (`doing` first, then `todo`,
both by priority), plus its epics. That ordering IS the recommendation. Do not
re-sort it, re-weight it, or second-guess it.

**Step 2 — Resolve each card to a concrete artifact.** For the top cards, look
up the named course and lesson in that course's `progress.json` to get the
topic and the file path, and to check whether the file has actually been
generated. This is the only use of that file.

**Step 3 — Report divergence, never silently correct it.** If a card says a
lesson is next but the file is absent, that is a blocker to state plainly. If a
`progress.json` status field contradicts the board, **the board is right** —
say so and move on. Do not edit the JSON to match, and do not edit the board to
match the JSON.

**Step 4 — Output**, in exactly this format:

```
WHAT'S NEXT — [DATE]

PRIMARY ──────────────────────────────────────────────────────
[Course] · Lesson [NN]: [Topic]        (ticket #[id])
Status: [Ready to study / Needs generation]
Why: [One sentence — the board's reason, not yours]
Action: [Exactly what to do]

SECONDARY ────────────────────────────────────────────────────
[same format]

OPTIONAL ─────────────────────────────────────────────────────
[same format]

BLOCKERS (omit section if none) ─────────────────────────────
[Course] · Lesson [NN]: [blocker description and how to clear it]
```

Every entry cites its ticket id. If a course has no card on the board, it does
not appear in this output at all — its absence from the board is the answer.

**Step 5 — Stop.** Do not offer to take action; the user opens the next session
themselves when ready.

## Tools Used
`src/tools/ticket_tools/agent_status.py` (the input). `progress.json` is read
for content lookup only.

## Logging Requirements
None — this is a read-only recommendation, not a state change.

## Failure Modes
- **The board has no teaching_assistant cards** → say exactly that. Do not fall
  back to scanning `progress.json` to invent a queue. An empty board means
  there is no next lesson until the user or this agent puts one there.
- **A `progress.json` is missing or malformed** → report it as a content
  blocker against the relevant ticket. It never changes the recommendation
  order, because it never sets it.

## Human Audit Notes
If the recommendation order feels wrong, the fix is on the board — change a
card's `priority` or `stage`. There is no ranking logic in this file to tune,
and none should be added back.
