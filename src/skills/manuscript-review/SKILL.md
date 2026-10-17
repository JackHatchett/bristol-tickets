---
name: manuscript-review
description: Reads finished prose line by line and reports back on it - its voice against the author's, writing that sounds machine-made, and borrowing from published work - without rewriting a word. Use when the author wants the sentences of a piece read rather than worked on.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.subtitle: Read finished prose line by line and report back
---
# manuscript-review

Reading finished prose at the sentence rather than building it. Prose still
being built is `src/skills/prose-drafting/SKILL.md`; the read of the same draft
for its structure — attention, promises, a reader with no context — is
`src/skills/developmental-read/SKILL.md`.

## The boundary

- **Review comments, flags, accepts or rejects, and never rewrites.** A reviewer
  that writes prose has stopped being a fresh reader, and fresh reading is what
  the pass is for.
- **Reconciling a passage the author sends back is assembly only** — their new
  text placed against the untouched text, and nothing else. Not one sentence of
  connective tissue.

## Procedure

Two reads. The user's request picks one.

1. **Style scan.** Walk the prose line by line for machine-prose tells —
   hedging, over-balanced "not just X but Y" constructions, generic sensory
   filler, tidy summary closers, dash tics, register flattening. Flag each in
   place and name the tell. **Running the same checklist on a second model is an
   option, never a precondition for the scan.**
2. **Originality scan.** Mechanism: `tools/_shared/originality_scan.md`. **Run
   it on explicit request only** — it is expensive.

## Failure modes

- **A flag turns out to be a story or world problem rather than a prose one** →
  hand it to `src/skills/developmental-read/SKILL.md`'s reader, or to
  `src/skills/story-proposals/SKILL.md`, rather than resolving it here.
- **The author asks for the passage fixed rather than flagged** → that is
  `src/skills/prose-drafting/SKILL.md`, entered deliberately and named as the switch it is.
- **A scan wants the voice profile** → the style scan reads prose only. Voice
  material reaches `src/skills/voice-distillation/SKILL.md` and stops there.

## Where the output goes

Comments and flags go to the user, and a full write-up to
`markdown_notebook.agent_output_dir`. **A directory the user authors in takes a
proposal rather than a write**, by the Write Authority clauses the agent's
charter gives.
