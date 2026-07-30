# Gemini Crew Handoff — writers_room protocol

**Specializes `protocols/_shared/external_ai_bridge.md`.** The six common
invariants (stateless, non-authoritative, briefed-not-connected, can't write
the source of truth, returns a clean block, sync discipline) live there and
are not restated here. This file carries only writers_room's delta: the
coordination contract between `writers_room` (the Quartermaster — coordinates
the story wiki, repo write access) and external advisory crew roles it briefs an
external AI into playing.

- **Memory model:** stateless, re-point each request — usually Gemini in VS
  Code with repo access, briefed into one role per session; also supports a
  no-access Gem via the `embedded` delivery mode below.
- **Direction:** the crew role *proposes* (Editor drafts/beat-engineers,
  Grammatizator *scouts* voice specimens); it never finalizes.
- **Payload:** a Reference Pack (file + section pointers the role reads itself) +
  the voice profile if relevant + explicit constraints, dropped in
  `handoff/to-gemini/`.
- **Return format:** schema-validated JSON envelope — the most formal return
  in the system, validated against `handoff.schema.json` (a discriminated
  union over the six crew directions). This is the reference example the
  archetype's §1b points at.
- **Guardrails cited, never restated:** `src/agent_identities/writers_room.md`
  holds the hard rules; `playbooks/writers_room/crew_dispatch.md` is the
  procedure `writers_room` runs; `playbooks/writers_room/story_proposals.md`
  is how a returned proposal is handled (no ratification gate); shared wiki
  conventions live in `tools/wiki_tools/`.

## Why external roles, not more agent identities

`writers_room` is one agent identity in this framework, the same as
`career_coach` is one identity that separately coordinates with a Gemini Gem
twin (see `protocols/career_coach/gemini_gem_bridge.md`). The crew metaphor
(Editor, Grammatizator, Proofer) describes **what an external AI is briefed to
become for a session**, not separate agents this framework provisions or
tracks. Only `writers_room` — the Quartermaster — has repo write access and a
roadmap epic; the other roles are stateless externally-run
counterparts it hands work to and receives proposals back from.

## The roles (what each is briefed to become)

Full profiles: `crew_roles/editor.md`, `crew_roles/grammatizator.md`,
`crew_roles/proofer.md` (roster table: `crew_roles/README.md`). One role per
external session; the profile is handed to the external AI by
`gemini_bootstrap.md`.

- **Editor** — drafts, coaches, beat-engineers prose. Advisory; proposes
  deltas back, never writes to the wiki.
- **Grammatizator** — scouts voice specimens from the author's prose (see
  `tools/writing_tools/voice_capture.md` for the generic method this role
  performs the "scout" half of). Advisory; never writes.
- **Proofer** *(reserved — specced, not yet built)* — read-and-react
  reviewer: comments, flags, accepts/rejects finished prose. Never
  rewrites.

**The user's story wiki, voice cards, state, and logs are user-authored.**
`writers_room` reads them and proposes changes; every proposal is reconciled and
summarized to the shared agent-output dir for the user to fold in — see
`playbooks/writers_room/story_proposals.md`. There is no 'canon' concept and no
ratification gate.

## Delivery — payload files, board state

**The board is the channel. These folders are only the payload.**

An external crew role is a Gemini Gem with no access to `roadmap.db`, so the
*content* of a brief has to travel as a file it can be shown. That is all these
folders are: a place to put bytes an outside party can read. They carry no
state, and no agent learns anything about outstanding work from them.

Every exchange is a **ticket**, and the ticket is the only record that a
dispatch happened, that a reply is awaited, or that anything is in progress:

- Dispatching a brief → open or update a card on the active board
  (`roadmap_write.py add-task --stage active --assignee writers_room`), and
  name the envelope file in its description. Then write the envelope.
- Receiving a reply → the *same* ticket moves to `doing` and its comment thread
  records the reconciliation. Never a new card for the reply half.
- Nothing outstanding on the board means nothing is outstanding. There is no
  second place to check.

| Folder | Written by | Read by | Holds |
|---|---|---|---|
| `handoff/to-gemini/` | `writers_room` | the external crew member | Brief payloads **to** Editor / Grammatizator / Proofer |
| `handoff/from-gemini/` | the external crew member | `writers_room` | Reply payloads **from** Editor / Grammatizator / Proofer |

Each side writes to one folder and reads the other, so payloads never collide.

**Filename convention:** `YYYY-MM-DD-HHMM-<direction-slug>.json`, zero-padded.
One envelope per file — never append a second envelope to an existing file.

**Never scan these folders to find work.** Do not "take the last file by name"
to discover what to do; that is deriving state from disk. The ticket names the
file you want. If a ticket points at an envelope that is not there, that is a
blocker to state plainly on the ticket — not a cue to go hunting for a
different file.

These folders are **not an audit trail** and hold no authority. The board is
the record. Superseded envelopes may be deleted freely; deleting one loses
nothing, because everything that mattered was reconciled onto a ticket.

## Envelope shape

**Authoritative machine form:** `handoff.schema.json` — one discriminated union
keyed on `direction`, covering all six directions. Envelope files are
`.json`, validated against it. When the schema and this document disagree,
the schema wins on shape; this document wins on intent. (This schema is
writers_room-specific and intentionally stays in this folder rather than the
shared layer — see `protocols/_shared/README.md`.)

| Direction | Carries | Required fields |
|---|---|---|
| `QUARTERMASTER_TO_EDITOR` | Reference Pack + voice profile + constraints | `role_profile, scope_intent, reference_pack, constraints` |
| `EDITOR_TO_QUARTERMASTER` | atomic deltas + open questions | `deltas` |
| `QUARTERMASTER_TO_GRAMMATIZATOR` | a voice task | `mode, corpus_type, provenance, sample_ref` |
| `GRAMMATIZATOR_TO_QUARTERMASTER` | the Specimen Pack | `mode, corpus_type, provenance` |
| `QUARTERMASTER_TO_PROOFER` *(reserved)* | prose to react to | `role_profile, prose_ref` |
| `PROOFER_TO_QUARTERMASTER` *(reserved)* | comments only | `notes` |

## Shared vocabulary

- **Reference Pack** — the set of story/world references a role reasons from,
  delivered as file + section pointers it reads itself (not a summary, not a
  paraphrase).
- **Delta** — a single, atomic proposed change to the story/world. One idea per
  delta.
- **Specimen Pack** — verbatim prose specimens plus the Grammatizator's
  per-specimen analysis; the voice analogue of the Reference Pack.
- **ID scheme** — not every wiki file has a domain-specific ID; the schema
  accepts `WB-###` / `CHAR-<name>` / `PLOT-<slug>` / `VOICE-###` as a
  starting convention. This is the reference project's scheme; a different
  active project may define its own, as long as the pattern in the schema
  is either matched or the schema is extended for it. The `file` path is
  always authoritative — the `id` is a best-guess hint, verified against
  which files actually change.

## Delivery modes — `pointers` (default) and `embedded`

What a `QUARTERMASTER_TO_*` brief scopes a role to is always the
`reference_pack` / `voice_profile` pointers it names — the role reads only those
files and sections, flagging gaps rather than wandering. *How* those
pointers are delivered has two modes, set by the brief's `delivery` field:

- **`pointers` (default).** The external agent has repo access, so each
  pointer carries only `file` + `sections` and it opens them itself. No
  pasted text — the token-lean path.
- **`embedded`.** For a no-local-access external agent (a Gem that can't
  read the repo and only produces handoff files for the human to drop
  manually). Each `reference_pack` pointer additionally carries its verbatim
  `excerpt`. The brief is self-contained: `writers_room` posts it in chat
  for the human to paste into the Gem, and writes the same `.json` locally
  as the record. The schema enforces this — under `delivery: embedded`,
  every `reference_pack` item must include an `excerpt`.

## A brief is onboarding, not a task order

A `QUARTERMASTER_TO_*` brief points the role at its profile and the content
it has to work with, and names the constraints (`content_rules`,
`invent_freely`, `do_not_touch`). It does **not** command a specific job.
The external agent reads its profile, surveys the content, and asks the
human which of its modes to use — drafting is one Editor mode, not the
default. See `gemini_bootstrap.md` for the exact onboarding sequence the
external agent follows.

## Rules

**Packaging a brief** (written to `handoff/to-gemini/`): point at the role's
profile, a Reference Pack (file + section pointers), the voice profile if
relevant, and explicit `content_rules` / `invent_freely` / `do_not_touch`
constraints. The brief sets up the work; the external agent chooses the mode
with the human.

**Receiving a reply** (`EDITOR_TO_QUARTERMASTER` or
`GRAMMATIZATOR_TO_QUARTERMASTER`, read from `handoff/from-gemini/`): treat
every delta or specimen as a proposal per `playbooks/writers_room/story_proposals.md`
— reconcile, surface conflicts with citations, propose a synthesis, then
summarize to the shared agent-output dir for the user to fold in. Never treat a
delta or specimen as accepted because the envelope looks well-formed; well-formed
only means the schema validated, not that the content is accepted.

## Provenance & genre firewall (voice intake only)

Governs *where a voice sample may be mined from*, not when voice guidance is
applied. Every voice intake declares `corpus_type` (genre/register) and
`provenance` (`own-corpus` | `external`):

- Voice facts are genre-scoped and never blended — a habit mined from one
  register/genre is not assumed to hold in another.
- An `external` corpus (outside the author's own approved writing) yields
  **only abstract, genre-scoped method facts** — no verbatim specimens, no
  favored-word lists. Its concrete language isn't the author's real voice and
  must never enter a voice card, a lexicon file, or any whitelist. The schema
  enforces this: a `GRAMMATIZATOR_TO_QUARTERMASTER` envelope with
  `provenance: external` is rejected if it carries `specimen_pack` or `lexicon`.

## The counterpart

Usually **Gemini in VS Code** with read/write repo access to the active
project's data root, playing one role, told which by `gemini_bootstrap.md`
in the human's first message to it.

## Cross-links
- `protocols/_shared/external_ai_bridge.md` — the archetype this specializes.
- `src/agent_identities/writers_room.md` — the hard rules cited, never restated.
- `handoff.schema.json` — the authoritative envelope shape (writers_room-specific).
- `gemini_bootstrap.md` — the external agent's onboarding sequence.
- `playbooks/writers_room/crew_dispatch.md` — this agent's own dispatch procedure.
