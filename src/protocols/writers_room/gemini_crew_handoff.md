# Gemini Crew Handoff — writers_room protocol

Specializes `protocols/_shared/external_ai_bridge.md`, which holds the six
common invariants. This file carries only writers_room's delta: the contract
between `writers_room`, the Quartermaster, and the external advisory crew roles
it briefs an external AI into playing.

- **Memory model:** stateless, re-pointed each request — an external client with
  repo access, briefed into one role per session, or a no-access Gem through the
  `embedded` delivery mode.
- **Direction:** a crew role proposes — the Editor drafts and beat-engineers,
  the Grammatizator scouts voice specimens — and never finalizes.
- **Payload:** a Reference Pack of file and section pointers the role reads
  itself, plus the voice profile where relevant and explicit constraints,
  dropped in `handoff/to-gemini/`.
- **Return format:** schema-validated JSON envelope, validated against
  `handoff.schema.json`, a discriminated union over the six crew directions.
  This is the reference example `external_ai_bridge.md` §1b points at.
- **Guardrails cited, never restated:** `src/agent_identities/writers_room.md`
  holds the hard rules, `playbooks/writers_room/crew_dispatch.md` is the
  dispatch procedure, `playbooks/writers_room/story_proposals.md` is how a
  returned proposal is handled, and shared wiki conventions live in
  `tools/wiki_tools/`.

## The roles

**A crew role is what an external AI is briefed to become for one session, not
an agent this framework provisions.** Only `writers_room` has repo write access
and a board epic.

- **Editor** — drafts, coaches and beat-engineers prose, handing back deltas.
- **Grammatizator** — scouts voice specimens from the author's prose;
  `tools/writing_tools/voice_capture.md` holds the generic method whose scout
  half this role performs.
- **Proofer** — read-and-react reviewer: comments, flags, accepts or rejects
  finished prose, and never rewrites.

Each role's full profile, including its capability header and current status,
is `crew_roles/<role>.md`; `crew_roles/README.md` is the roster. **One role per
external session**, handed to the external AI by `gemini_bootstrap.md`.

**The user's story wiki, voice cards and logs are user-authored.**
`writers_room` reads them and proposes; every proposal is reconciled and
summarized to the shared agent-output dir for the user to fold in. There is no
canon concept and no ratification gate.

## Delivery folders are payload, not state

An external crew role cannot read `tickets.db`, so a brief's content travels as
a file it can be shown. **These folders hold bytes an outside party can read and
nothing else.** The ticket is the only record that a dispatch happened, that a
reply is awaited, or that anything is in progress — `crew_dispatch.md` holds the
procedure.

| Folder | Written by | Read by | Holds |
|---|---|---|---|
| `handoff/to-gemini/` | `writers_room` | the external crew member | brief payloads to the role |
| `handoff/from-gemini/` | the external crew member | `writers_room` | reply payloads from the role |

Each side writes one folder and reads the other, so payloads never collide.

- **Filename convention:** `YYYY-MM-DD-HHMM-<direction-slug>.json`,
  zero-padded.
- **One envelope per file.** Never append a second envelope to an existing file.
- **Never scan these folders to find work.** The ticket names the file you want.
  A ticket pointing at an envelope that is not there is a blocker to state on
  the ticket, never a cue to hunt for a different file.
- **These folders are not an audit trail and hold no authority.**
  `writers_room` may delete a superseded envelope freely; everything that
  mattered was reconciled onto a ticket.

## Envelope shape

`handoff.schema.json` is the authoritative machine form: one discriminated union
keyed on `direction`, covering all six. **Where the schema and this document
disagree, the schema wins on shape and this document wins on intent.** The
schema is writers_room-specific and stays in this folder
(`protocols/_shared/README.md`).

| Direction | Carries | Required fields |
|---|---|---|
| `QUARTERMASTER_TO_EDITOR` | Reference Pack + voice profile + constraints | `role_profile, scope_intent, reference_pack, constraints` |
| `EDITOR_TO_QUARTERMASTER` | atomic deltas + open questions | `deltas` |
| `QUARTERMASTER_TO_GRAMMATIZATOR` | a voice task | `mode, corpus_type, provenance, sample_ref` |
| `GRAMMATIZATOR_TO_QUARTERMASTER` | the Specimen Pack | `mode, corpus_type, provenance` |
| `QUARTERMASTER_TO_PROOFER` | prose to react to | `role_profile, prose_ref` |
| `PROOFER_TO_QUARTERMASTER` | comments only | `notes` |

## Shared vocabulary

- **Reference Pack** — the story and world references a role reasons from,
  delivered as file and section pointers it reads itself, never a summary or a
  paraphrase.
- **Delta** — one atomic proposed change to the story or world. One idea per
  delta.
- **Specimen Pack** — verbatim prose specimens plus the Grammatizator's
  per-specimen analysis; the voice analogue of the Reference Pack.
- **ID scheme** — the schema accepts `WB-###`, `CHAR-<name>`, `PLOT-<slug>` and
  `VOICE-###` as a starting convention. **A project may define its own, as long
  as it matches the schema's pattern or the schema is extended for it.** **The
  `file` path is always authoritative**; the `id` is a hint, verified against
  which files actually change.

## Delivery modes

A brief always scopes a role to the `reference_pack` and `voice_profile`
pointers it names: **the role reads only those files and sections, and flags
gaps rather than wandering.** The brief's `delivery` field sets how those
pointers travel:

- **`pointers`, the default.** The external agent has repo access, so each
  pointer carries `file` and `sections` and it opens them itself. The token-lean
  path.
- **`embedded`.** For an external agent with no local access, each
  `reference_pack` pointer additionally carries its verbatim `excerpt`, making
  the brief self-contained: `writers_room` posts it in chat for the human to
  paste, and writes the same `.json` locally as the record. **The schema
  enforces this** — under `delivery: embedded`, every `reference_pack` item must
  include an `excerpt`.

## A brief is onboarding, not a task order

A `QUARTERMASTER_TO_*` brief points the role at its profile and the content it
works with, and names the constraints (`content_rules`, `invent_freely`,
`do_not_touch`). **It does not command a specific job.** The external agent
reads its profile, surveys the content, and asks the human which mode to use —
drafting is one Editor mode, not the default. `gemini_bootstrap.md` holds the
onboarding sequence.

## Rules

**Packaging a brief**, written to `handoff/to-gemini/`: point at the role's
profile, a Reference Pack of file and section pointers, the voice profile where
relevant, and explicit `content_rules`, `invent_freely` and `do_not_touch`
constraints.

**Receiving a reply**, read from `handoff/from-gemini/`: treat every delta or
specimen as a proposal per `story_proposals.md` — reconcile, surface conflicts
with citations, propose a synthesis, then summarize to the shared agent-output
dir. **Never treat a delta or specimen as accepted because the envelope is
well-formed**; well-formed means the schema validated.

## Provenance and genre firewall

Governs where a voice sample may be mined from, not when voice guidance is
applied. Every voice intake declares `corpus_type` (genre and register) and
`provenance` (`own-corpus` or `external`).

- **Voice facts are genre-scoped and never blended.** A habit mined from one
  register is not assumed to hold in another.
- **An `external` corpus yields only abstract, genre-scoped method facts** — no
  verbatim specimens and no favored-word lists. Its concrete language is not the
  author's real voice and never enters a voice card, a lexicon file or a
  whitelist. **The schema enforces this**: a `GRAMMATIZATOR_TO_QUARTERMASTER`
  envelope with `provenance: external` is rejected if it carries
  `specimen_pack` or `lexicon`.

## Cross-links

- `protocols/_shared/external_ai_bridge.md` — the archetype this specializes.
- `src/agent_identities/writers_room.md` — the hard rules cited above.
- `handoff.schema.json` — the authoritative envelope shape.
- `gemini_bootstrap.md` — the external agent's onboarding sequence.
- `playbooks/writers_room/crew_dispatch.md` — this agent's dispatch procedure.
