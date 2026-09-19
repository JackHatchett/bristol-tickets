# Wiki Tools

Conventions for reading a wiki-shaped body of durable facts — a novel's
worldbuilding, a game's bible, a documentation set.

## Index

- **`wiki_conventions.md`** — reconciling a proposed change against the whole
  domain, the Facts / Reasoning / Open-questions reading aid, and on-demand
  lookup through a router. Load it when a task reads or proposes a change to a
  knowledge base.
- **`name_variants.py`** — one coined name spelled more than one way across a
  folder of notes, with how often each spelling is used and which notes hold it.
  Run it when a body of notes has grown past what one session holds; the
  procedure around it, including what a finding is and where it goes, is
  `src/skills/checking-a-wiki-for-disagreements/SKILL.md`.

## Using these

- **Point a skill at `wiki_conventions.md` rather than restating it.** An
  agent's own charter and skills own that domain's file layout, ID scheme and
  content rules, and nothing else.
- **Two skills describing the same reconcile flow differently is drift** — cut
  both back to a reference.

`src/skills/story-proposals/SKILL.md` and
`src/skills/design-proposals/SKILL.md` use the pattern.
