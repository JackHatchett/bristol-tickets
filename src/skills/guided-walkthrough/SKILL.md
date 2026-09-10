---
name: guided-walkthrough
description: Walks the user through a feature of this system at their own machine, one step at a time, with the user doing every step and the session saying what should appear before each one. Use when a feature they own has never been used and reading about it has not been enough.
license: MIT
compatibility: Runs where the user is present at the machine holding the installation.
metadata:
  bristol.kind: playbook
  bristol.maintainer: teaching_assistant
  bristol.scripts: src/tools/skill_tools/skills.py
---
# guided-walkthrough

Input: one feature of this system, and the user at the machine that holds the
installation. Operation: the reference for that feature, run the way below.
Output: the user having done it once, and the reference corrected by what
happened.

**A walkthrough is neither of the other two teaching shapes.** A course is built
now and studied later, away from the machine; an explainer is reading. This
happens while the feature is open in front of the user, and its subject is what
appears on their screen.

## Preconditions

- **The user is present and directing.** A walkthrough with nobody at the
  machine is a document, and the document already exists.
- **A reference exists for the feature**, under `references/`, one file per
  feature. Where none does, it is written from a run someone performed —
  `src/skills/verifying-a-card/SKILL.md` for the card that produces it.

## Who does what

- **The user performs every step.** A session that runs the command has taught
  nothing, and the one irreversible move in a walkthrough is theirs by design
  wherever the feature makes it theirs.
- **Say what should appear before the user acts**, in enough detail that a
  difference is noticeable — the shape of the output, the line that matters in
  it, the thing that changes on screen.
- **Ask what actually appeared, and take that answer over the expectation.**
- **Never advance on an assumed result.** A step whose outcome nobody looked at
  is a step that did not happen.
- **Define a term at the step that uses it**, pitched at what the user has
  already shown they know — `src/skills/inline-teaching/SKILL.md`.
- **Name the decisions that are the user's as theirs, at the moment they
  arrive**, rather than presenting them as the next instruction.

## When what happens is not what was written

- **Stop on the first difference.** Repeating a step until it behaves is how a
  walkthrough teaches a superstition.
- **Record what happened rather than what was supposed to.** The divergence is
  the second deliverable, and a run that reports none is a run nobody watched.
- **Correct the reference from the run, in the same session.**
- **End the walkthrough at a step that cannot be completed**, and say which step
  and what stopped it. Where the block is the system's rather than the user's,
  it is a card.

## What a reference holds

- **One feature, and the file is named for it.**
- **The steps in order**, each saying what the user does, what appears, and what
  that means.
- **The moments that are the user's decision**, marked as theirs.
- **The failures a real run hit**, each with what it means and what clears it.
- **Nothing nobody has performed.** A step taken from documentation is the
  thing this skill exists to stop shipping.

## Adding a feature

- **A second feature is a second reference file.** A second skill for a second
  feature is the genre missed.

## Failure modes

- **The session ran the commands and narrated them** → §Who does what; the user
  has watched a demonstration and learned nothing they can repeat.
- **A step's expected result is "it works"** → nothing about that step can
  fail, so nothing about it can be checked.
- **The write-up matches the reference exactly** → either nobody compared, or
  the comparison was made against what the reference said instead of against
  the screen.
- **A reference has grown a section on a neighbouring feature** → that section
  is another reference file.

## Audit

**Whether the user can do the thing again a week later without the session.**
That is the only outcome this skill has; a run that produced a correct
transcript and no such user did not work.
