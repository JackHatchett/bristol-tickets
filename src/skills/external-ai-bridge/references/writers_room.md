# Second-Model Bridge — writers_room protocol

Specializes `src/skills/external-ai-bridge/SKILL.md`, which holds the six
common invariants. This file carries only writers_room's delta.

- **Memory model:** stateless, re-pointed each request — nothing persists
  between sessions, and every brief is complete on its own.
- **Direction:** the second model reads and proposes. It reacts to finished
  prose, scans it, or scouts voice specimens from a sample it is pointed at.
- **Payload:** a reference set of file and section pointers, plus the content
  rules and constraints below. Where the model has no access to the files, each
  pointer carries its verbatim excerpt instead, and the brief becomes
  self-contained.
- **Return format:** pasted text block — one fenced block the user copies back
  into the session.
- **Guardrails cited, never restated:** `src/agent_identities/writers_room.md`
  holds the hard rules; `src/skills/story-proposals/SKILL.md` is how a
  return is filed; `src/skills/voice-distillation/SKILL.md` holds the
  genre and provenance firewall on voice intake; wiki conventions live in
  `tools/wiki_tools/`.

## The delta

**A second model is worth the round trip only where this session cannot do the
job on its own.** Three cases:

- **The zero-context reader test** (`src/skills/manuscript-review/SKILL.md`). A session that has
  loaded the project cannot unread it, and the read is worthless once
  contaminated.
- **A style scan of prose this session drafted.** Self-assessment finds fewer
  tells than fresh eyes do.
- **A scouting pass over a corpus** (`src/skills/voice-distillation/SKILL.md`), where the sample
  is large enough that reading it in full would crowd out the session.

Everything else writers_room does itself.

## The brief

One block, containing:

- **The job**, in one line, named from the list above.
- **The reference set** — file and section pointers scoped to what the job
  needs, never the whole project. Withhold it entirely for a zero-context reader
  test; that is the point of the read.
- **The voice profile**, where prose is being drafted or revised.
- **The constraints** — the active project's content rules, what may be invented
  freely, and what must not be touched: settled beats, settled terms.

**Scope the model to the pointers the brief names.** It reads those files and
sections and flags a gap rather than wandering into the rest of the project.

## The return

- **One fenced block, pasted back into the session.** No folder, no envelope
  file, and nothing the session goes hunting for on disk.
- **Every delta, flag or specimen is a proposal**, reconciled and filed per
  `src/skills/story-proposals/SKILL.md` or distilled per `src/skills/voice-distillation/SKILL.md`. **Well-formed
  is not accepted.**
- **A return that touches something the brief put out of bounds is a conflict to
  surface**, never something to silently drop or silently apply.

## Cross-links

- `src/skills/external-ai-bridge/SKILL.md` — the archetype this specializes.
- `src/agent_identities/writers_room.md` — the hard rules cited above.
- `src/skills/manuscript-review/SKILL.md`,
  `src/skills/voice-distillation/SKILL.md` — the capabilities that reach
  for this bridge.
