---
name: interview-prep
description: Builds a prep sheet for one upcoming interview out of what is already recorded about that application. Use when the user names an interview he has coming up and wants to get ready for it.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: career_coach
---
# interview-prep

Prep material for one named interview, built from the row that interview
already has in the applications tracker.

- **Start from the interview's existing row in the applications tracker.** Every
  interview maps to one; this workflow never creates a row. The JD, company
  research and fit notes already on it are the context, not something to
  re-derive.
- **Ask the user to confirm the company and role** where an interview has no
  matching row, rather than guessing which application it belongs to.

## The prep sheet

Cover the confirmed role and interview stage where known, a refreshed
narrative-hook summary pulled from the original triage and letter, the likely
questions for this stage and role level, and a short set of the user's own proof
points from their anecdotes and employment-history context files matched to
those questions. **Do not regenerate the fit analysis from zero.**

**Never invent an experience, metric or outcome absent from the user's context
files**, per `src/skills/cover-letter/SKILL.md`.

**A take-home or assignment deliverable is its own output**, distinct from the
prep sheet, produced only when the user asks for one.

**The lint gate and voice-profile read that govern cover letters do not apply
here.** A prep sheet is a working document for the user, not prose for an
external reader — unless the user is drafting something they will say or send
verbatim.

## Delivery

Save the sheet to `applications/interview_prep/prep-sheets/` in the user's data
root, and a requested assignment deliverable to
`applications/interview_prep/assignments/`. Deliver in chat as well; the saved
file is what makes it a record rather than scrollback.
