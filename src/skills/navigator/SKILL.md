---
name: navigator
description: Says what the student should study next, taking the order from the ticket board rather than working one out. Use when the user asks what to do next in a course.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: teaching_assistant
  bristol.scripts: src/tools/ticket_tools/agent_status.py
---
# navigator

Return a bounded recommendation of what to study next. It does not teach, does
not generate files, and does not decide the order — the board already did.

## The rule this skill exists to obey

**Work state comes from the board and only from the board.** What is in
progress, what is finished, what comes next and in what order are facts held in
`tickets.db`, and this skill may not re-derive any of them from a file on
disk. Computing its own ranking out of `progress.json` would be a second
next-action engine competing with the board.

**`syllabus/progress.json` is a file manifest, not a tracker.** The only
questions to ask it are content questions: does this lesson exist, what is its
topic, what is its filename, has the file been generated. **Any status-shaped
field in that JSON — `current_lesson`, `course_complete`, `lesson_complete`,
`studied`, `mastery`, `tutored_on` — is stale by definition and must not be read
to decide anything.** The HTML renderer paints some of them as badges; a
generated artifact displaying a value is not a channel an agent reads back.

## Preconditions

The board is readable. `python3 src/tools/ticket_tools/agent_status.py
teaching_assistant` is this skill's input.

## Procedure

1. **Read the board.** `agent_status.py teaching_assistant` returns this agent's
   active-stage tasks in precedence order — `doing` first, then `todo`, both in
   board order — plus its epics. **That ordering is the recommendation. Never
   re-sort, re-weight or second-guess it.**
2. **Resolve each of the top cards to a concrete artifact.** Look the named
   course and lesson up in that course's `progress.json` for the topic, the file
   path, and whether the file has been generated. This is the only use of that
   file.
3. **Report divergence, never silently correct it.** A card naming a lesson
   whose file is absent is a blocker to state plainly. **Where a
   `progress.json` status field contradicts the board, the board is right** —
   say so and move on. Do not edit the JSON to match, and do not edit the board
   to match the JSON.
4. **Output in exactly this format:**

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

   **Every entry cites its ticket id.** A course with no card on the board does
   not appear at all; its absence from the board is the answer.
5. **Stop.** Do not offer to take action; the user opens the next session when
   ready.

## Failure modes

- **The board has no teaching_assistant cards** → say exactly that. **Never fall
  back to scanning `progress.json` to invent a queue.** An empty board means
  there is no next lesson until someone puts one there.
- **A `progress.json` is missing or malformed** → report it as a content blocker
  against the relevant ticket. It never changes the recommendation order,
  because it never sets it.

## Audit

**A recommendation order that feels wrong is fixed on the board** — a card's
position or `stage`. There is no ranking logic in this file to tune, and none
belongs here.
