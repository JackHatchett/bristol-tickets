# Wiki Tools

Conventions for reading a wiki-shaped body of durable facts — a novel's
worldbuilding, a game's bible, a documentation set.

## Index

- **`wiki_conventions.md`** — reconciling a proposed change against the whole
  domain, the Facts / Reasoning / Open-questions reading aid, and on-demand
  lookup through a router. Load it when a task reads or proposes a change to a
  knowledge base.
- **`name_variants.py`** — one coined name spelled more than one way across a
  folder of notes, with how often each spelling is used and which notes contain it.
  Run it when a body of notes has grown past what one session can read; the
  procedure around it, including what a finding is and where it goes, is
  `src/skills/checking-a-wiki-for-disagreements/SKILL.md`.
- **`sound_check.py`** — how near a coined name, or a sample of a language's
  words, sounds to every constructed language and every main character's name
  in the notes. Run it on any name or language sound before it is offered; the
  procedure around it is `src/skills/designing-with-the-author/SKILL.md`
  §Checking a name's sound, and for a language's own sound
  `src/skills/building-a-constructed-language/SKILL.md` §Check the sound. Its
  docstring gives the measures and the thresholds.

## Using these

- **Point a skill at `wiki_conventions.md` rather than restating it.** An
  agent's own charter and skills own that domain's file layout, ID scheme and
  content rules, and nothing else.
- **Two skills describing the same reconcile flow differently is drift** — cut
  both back to a reference.

`src/skills/story-proposals/SKILL.md` and
`src/skills/design-proposals/SKILL.md` use the pattern.
