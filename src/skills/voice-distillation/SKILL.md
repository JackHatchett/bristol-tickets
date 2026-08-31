---
name: voice-distillation
description: Runs the exercises that capture how the author writes and distils the answers into a profile of his voice. Use when the author asks to do voice work, or says VOICE.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
---
# voice-distillation

writers_room's application of the generic method in
`src/tools/writing_tools/voice_capture.md` — read that file for the philosophy,
the two intake paths and the distillation loop.

## Entering voice work

**Read the voice system's README once per entry into `VOICE` mode**, not every
session, for its architecture, and read its inventory file for what is filled
and what is next. **The inventory is the resumable state**, per the generic
method's Resumability section. Both live in the active author's voice data root,
resolved via `/config`; never hardcode that path in `/src`.

## Running Path A (elicit) or Path B (mine)

1. **Choose the path**: A to fill one specific unfilled technique, B for an
   initial bulk pass over existing writing.
2. **Scout the specimens.** Read the sample and pull the verbatim moves in it,
   each with a short analysis, a `strength` and a `recurrence`. Two shapes: a
   **bulk pass** over a body of the author's writing, returning specimens across
   every technique plus an opportunistic lexicon — favored verbs, avoided words,
   register lean, tics — or a **targeted pass** over one sample, often a single
   exercise page, returning the cleanest specimen of each named technique.
   Handing the scouting pass to a second model is an option
   (`src/skills/external-ai-bridge/references/writers_room.md`), never a requirement.
3. **Record the `corpus_type` and `provenance` of every specimen** as it is
   taken. The firewall below reads both, and neither can be recovered later.

## Distilling

Run the generic distillation loop from `tools/writing_tools/voice_capture.md`
against the specimens: write or update the technique's card, set its confidence
threshold from `strength` and `recurrence`, update the inventory status, and
promote the sharpest signature lines into the core profile.

- **Quote verbatim into the card, never from a paraphrase.**

## Genre and provenance firewall

Applies to every specimen before anything is stored, whoever scouted it.

- **Tag every specimen with the corpus it came from.** Voice facts are
  genre-scoped and never blended across corpora.
- **An `external` intake — prose outside the author's own corpus — yields
  abstract, genre-scoped method facts only.** Never a verbatim specimen and
  never a lexicon entry: a coinage mechanism and its rate, never the coined
  words themselves.
- **Never promote a specimen into a card without confirming its
  `provenance`.**

## The growth command

On "prompt me on how I write \<X\>": add a new inventory row, compose or reuse
an exercise, run Path A, distil. **This is the sole mechanism for extending the
technique library** — never invent a technique card without a specimen behind
it.

## Session close

**Note voice progress in the project's session log** — one line naming which
technique IDs got filled — per `src/skills/writers-room-project-context/SKILL.md`'s end-of-session step.
**Surface a milestone to the user** when one lands, such as the core tier
completing, and record it in the session-log summary.
