---
name: reviewing-finished-work
description: Reads a card whose author has finished the work against its own acceptance criteria, one at a time, and closes it or sends it back. Use when work another agent finished should be checked by someone who did not do it.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3 to read and write the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/ticket_tools/ticket_write.py
  bristol.subtitle: Check finished work against its criteria
---
# reviewing-finished-work

Input: a card in `doing`, assigned to the reviewer, whose author has finished
the work. Operation: its own acceptance criteria, one at a time, against what is
actually on disk. Output: one comment on that card, and the card closed or
returned to its author.

**The reviewer is not the author.** An agent holding both the authorship and the
judgement of one output is the case
`src/templates/identity_template.md` §When one job is two agents names, and it
is why this is a pass someone else runs rather than a section of the work.

## What is reviewed

- **The card's own acceptance criteria**, in the order they are numbered. They
  are the contract; nothing else is the standard, and a criterion the reviewer
  disagrees with is a finding about the card rather than about the work.
- **What is on disk**, not what the closing comment says was done. A comment is
  a claim, and the review exists because a claim is not evidence.
- **The verification the card stated** — `src/skills/verifying-a-card/SKILL.md`.
  Re-run it. A card that stated none is itself the first finding.

## The pass

1. **Read the card whole**: description, criteria, comments, links.
2. **Take one criterion.** Find the thing it refers to, open it, and say met or not
   met. Not "looks right": the file, the line, the output.
3. **Repeat for every criterion**, including the ones the closing comment
   already claims. A review that reads the comment and agrees has reviewed the
   comment.
4. **Re-run the verification** the card stated, and record what it produced.
5. **File it**, per §Where findings go.

**Stop at the criteria.** Everything a reviewer would rather say — a better
design, a tidier name, a thing they would have done differently — is not a
finding unless a criterion asks for it. A review that widens its own scope is an
author with a second opinion.

## Where findings go

- **One comment on the card reviewed**, listing each criterion and whether it
  is met, and nothing else. That comment is the review; there is no report file
  and no second place to look — `src/app.md` §The board is the only channel.
- **Every criterion met: close the card.** The review was the last reason to
  come back to it.
- **A criterion unmet: return the card to its author** — `update-task-status
  --id N --status doing --assignee <the author's agent>` — with the comment
  stating each unmet criterion. The card stays one card until it passes.
- **A defect outside the card's criteria is a card of its own**,
  `add-task --assignee <the author's agent> --reporter <you>`, linked to the
  card reviewed.
- **Nothing to find is a real outcome**, and it is still a comment: a review that
  ran and found nothing is evidence, and its absence is indistinguishable from a
  review that never ran.

## What the community supplies, and what it does not

The public libraries do carry an adversarial-review skill. It dispatches to a
sub-agent defined in a file outside the skill's own directory, and instructs the
session to execute that file's system prompt as its operating instructions for
the turn. Neither half survives here: the file does not travel with the skill,
and a body that replaces a session's own operating instructions is what
`src/skills/importing-a-skill/SKILL.md` refuses first. This practice is written
here for that reason rather than for want of looking.

**What was worth borrowing from it**: a finding carries a concrete correction
rather than only a complaint, which is why a defect here is a card with a
subject rather than a line of prose.

## Failure modes

- **The review reads the closing comment** → it has reviewed a claim.
- **A finding with no card** → it will not be worked.
- **A criterion skipped because the comment sounds convincing** → that is the
  criterion most worth checking.
- **The reviewer rewrites the work** → then it has an author again, and nobody
  has reviewed it.

## Audit

**Whether every criterion on the reviewed card is listed in the comment.** A
criterion the review passed over silently is one nobody checked, and the card
now carries a review saying otherwise.
