# voice_distillation.md — writers_room playbook

**Triggered:** by a natural request ("let's do some voice work," "voice
mode," "give me the next exercise," "prompt me on how I write \<X\>"), or
the keyword **`VOICE`**. Not entered by default at session start.

This is `writers_room`'s application of the generic method in
`tools/writing_tools/voice_capture.md` — read that file for the underlying
philosophy, the two intake paths, and the distillation loop, described once
and not repeated here. `writers_room` always plays the **distiller** half;
the Grammatizator (an external role, dispatched per
`crew_dispatch.md`) plays the **scout** half.

## Entering voice work

Read the voice system's own README once per entry into `VOICE` mode (not
every session) for its architecture, and its inventory file for exactly
what's filled and what's next — the inventory **is** the resumable state,
per the generic method's "Resumability" section. Both live in the active
author's voice data root, resolved via `/config`; never hardcode that path
in `/src`.

## Running Path A (elicit) or Path B (mine)

1. Decide which path fits: Path A for filling one specific unfilled
   technique, Path B for an initial bulk pass over existing writing.
2. Dispatch the Grammatizator per `crew_dispatch.md` — a
   `QUARTERMASTER_TO_GRAMMATIZATOR` brief naming the mode
   (`BULK_CORPUS` / `TARGETED_SAMPLE`), the `corpus_type`, `provenance`,
   and the sample reference.
3. Receive the `GRAMMATIZATOR_TO_QUARTERMASTER` reply (the Specimen Pack).
   `writers_room` never reads the raw source documents itself — only the
   pack.

## Distilling

Run the generic distillation loop from `tools/writing_tools/voice_capture.md`
against the returned Specimen Pack: write or update the technique's card,
set its confidence threshold from `strength` + `recurrence`, update the
inventory status, and promote the sharpest signature lines into the core
profile. Quote verbatim into the card — never from a paraphrase. The raw
Specimen Pack stays on disk as payload; the distiller doesn't need
to re-read it once the card is written.

## Genre/provenance firewall

Apply the firewall described in
`protocols/writers_room/gemini_crew_handoff.md` before storing anything: an
`external` (non-author-corpus) intake yields abstract method facts only, never
verbatim specimens or lexicon entries. This is enforced at the schema level on
the Grammatizator's reply, but the distillation step should still check it —
don't promote a specimen into a card without confirming its `provenance`.

## The growth command

On "prompt me on how I write \<X\>": add a new inventory row, compose or
reuse an exercise, run Path A, distil. This is the sole mechanism for
extending the technique library — never invent a new technique card without
a specimen behind it.

## Session close

Note voice progress in the project's session log (one line — which
technique IDs got filled) per `project_context.md`'s end-of-session step.
If a milestone lands (e.g. the core tier completes), surface it to the user
and record it in the session-log summary per `story_proposals.md`.
