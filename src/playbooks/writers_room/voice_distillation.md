# voice_distillation — writers_room playbook

Triggered by a natural request ("let's do some voice work," "voice mode," "give
me the next exercise," "prompt me on how I write \<X\>") or by the keyword
**`VOICE`**. Never entered by default at session start.

This is writers_room's application of the generic method in
`tools/writing_tools/voice_capture.md` — read that file for the philosophy, the
two intake paths and the distillation loop. **writers_room always plays the
distiller half**; the Grammatizator, an external role dispatched per
`crew_dispatch.md`, plays the scout half.

## Entering voice work

**Read the voice system's README once per entry into `VOICE` mode**, not every
session, for its architecture, and read its inventory file for what is filled
and what is next. **The inventory is the resumable state**, per the generic
method's Resumability section. Both live in the active author's voice data root,
resolved via `/config`; never hardcode that path in `/src`.

## Running Path A (elicit) or Path B (mine)

1. **Choose the path**: A to fill one specific unfilled technique, B for an
   initial bulk pass over existing writing.
2. **Dispatch the Grammatizator** per `crew_dispatch.md` — a
   `QUARTERMASTER_TO_GRAMMATIZATOR` brief naming the mode (`BULK_CORPUS` or
   `TARGETED_SAMPLE`), the `corpus_type`, the `provenance` and the sample
   reference.
3. **Receive the `GRAMMATIZATOR_TO_QUARTERMASTER` reply**, the Specimen Pack.
   **writers_room never reads the raw source documents itself** — only the pack.

## Distilling

Run the generic distillation loop from `tools/writing_tools/voice_capture.md`
against the returned pack: write or update the technique's card, set its
confidence threshold from `strength` and `recurrence`, update the inventory
status, and promote the sharpest signature lines into the core profile.

- **Quote verbatim into the card, never from a paraphrase.**
- **The raw Specimen Pack stays on disk as payload**; the distiller does not
  re-read it once the card is written.

## Genre and provenance firewall

Apply the firewall in `protocols/writers_room/gemini_crew_handoff.md` before
storing anything: **an `external` intake — outside the author's own corpus —
yields abstract method facts only, never verbatim specimens or lexicon
entries.** The Grammatizator's reply schema enforces this, and the distillation
step checks it too: **never promote a specimen into a card without confirming
its `provenance`.**

## The growth command

On "prompt me on how I write \<X\>": add a new inventory row, compose or reuse
an exercise, run Path A, distil. **This is the sole mechanism for extending the
technique library** — never invent a technique card without a specimen behind
it.

## Session close

**Note voice progress in the project's session log** — one line naming which
technique IDs got filled — per `project_context.md`'s end-of-session step.
**Surface a milestone to the user** when one lands, such as the core tier
completing, and record it in the session-log summary.
