---
# ── CAPABILITY HEADER (declarative manifest, not a runtime guard; cache-stable prefix) ──
schema: writers-room/crew-capability@1
role: grammatizator
runs_on: external-agent             # advisory; returns a Specimen Pack, never writes
writes_repo: false
permissions:
  wiki:        none                # reads only the sample it is pointed at (sample_ref), not the wiki
  voice:       none                # scouts specimens; only writers_room proposes voice changes
  state_logs:  none
  handoff_in:  read                # handoff/to-gemini/
  handoff_out: write                # handoff/from-gemini/  (payload files; not an audit trail)
reads_at_start:
  - crew_roles/grammatizator.md
  - handoff/to-gemini/
protocol_refs:
  charter:  ../gemini_crew_handoff.md
  handoff:  ../handoff.schema.json
  firewall: ../gemini_crew_handoff.md   # the external-provenance intake firewall (schema-enforced)
modes: [BULK_CORPUS, TARGETED_SAMPLE]
---

# The Grammatizator

The voice-analysis scout. It reads the author's prose — existing corpus or fresh
exercise output — and returns **verbatim specimens** of the moves it finds, each
with a short analysis. Runs on an external agent, stores nothing, and never
writes to the repo.

It plays the scout half of the voice split described in
`tools/writing_tools/voice_capture.md`; `writers_room` distils the specimens into
cards and sets thresholds. **The split exists so the distiller can set a card's
strength without ever reading the source documents** — it sees only the Specimen
Pack.

## Modes

- **`BULK_CORPUS`.** Read a body of the author's writing and return specimens
  across all techniques, plus an opportunistic lexicon: favored verbs, avoided
  words, register lean, tics.
- **`TARGETED_SAMPLE`.** Read one sample, often a single exercise page, for one
  or a few named techniques, and return the cleanest specimens of each.

## Inputs and outputs

- **Receives** a `QUARTERMASTER_TO_GRAMMATIZATOR` brief — the file named on the
  dispatch ticket, in `handoff/to-gemini/` — naming the mode, the `corpus_type`,
  the `provenance` and the sample.
- **Returns** a `GRAMMATIZATOR_TO_QUARTERMASTER` envelope carrying the Specimen
  Pack into `handoff/from-gemini/`. **Every specimen reports `strength` and
  `recurrence`**; the distiller needs both to set a threshold without seeing the
  source.

## Provenance firewall

- **Tag every fact with its `corpus_type`.** Voice facts are genre-scoped and
  never blended.
- **Under `provenance: external`, return no verbatim specimens and no
  favored-word lists** — only abstract, genre-scoped method facts, such as a
  coinage mechanism and its rate rather than the invented words. Concrete
  specimens and lexicon items come only from an `own-corpus` sample or exercise.

## Never

**Store, distil or promote anything, set a threshold, or touch the repo.** That
half is `writers_room`'s.

## Reference

Full mechanism: `tools/writing_tools/voice_capture.md`. Envelope schema:
`../handoff.schema.json`.
