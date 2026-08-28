---
name: writing-for-the-user
description: Write a report or document the user can read unaided.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# writing-for-the-user

Input: a finding, a decision or a change, and the board it sits on. Operation:
the rules below. Output: text the user reads once, without having to ask what
four of its words mean.

It governs everything written for the user to read — a document, a note, a
ticket description or comment, a session report, an answer in chat that carries
a finding. `src/skills/inline-teaching/SKILL.md` governs the other half:
teaching inside a live exchange, which produces no standalone text. Where an
exchange produces written output, that file governs what is taught and this one
governs how the output reads.

## Preconditions

- **The user is the reader.** Text addressed to an agent, a tool, or a file
  under `/src` is written to `src/templates/identity_template.md` §The
  governing-doc style contract instead.

## Procedure

1. **Read the register from what the user has demonstrated** —
   `src/skills/inline-teaching/SKILL.md` §Procedure step 1 owns how. Writing
   beneath that register is the same defect as writing above it.
2. **Define a term the first time it is used**, in one plain sentence. A term
   left undefined is the defect this file names, and the reader having to ask is
   how it is found.
3. **Define a coined name before it carries any weight.** A label invented for a
   group of problems is defined at first use, and never stands as a heading
   before it is defined.
4. **Order a document carrying more than one finding**: the problems, then what
   their terms mean, then the options — including the ones that fail, and why —
   then the one recommended. That order and no other.
5. **Report a change against the goal it serves.** Name the goal from the board,
   the milestone or epic the card sits under, and say where the change sits in
   the sequence toward it. What changed, alone, is not a report.

## Failure modes

- **The user asks what a word means** → step 2 did not fire; define it, and read
  the rest of the same text for the others.
- **A heading names something the reader has not met** → step 3 fired late.
- **The report reads as a list of edits** → step 5 is missing, and the goal it
  wants is on the board.
- **Every term arrives with a definition the user finishes for you** → step 1 is
  reading a register lower than the one demonstrated.

## Audit

**Whether one term in the text is never defined in it.** One is the whole
failure: the reader stops at it, and nothing after it lands.
