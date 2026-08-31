---
name: manuscript-review
description: Reads finished prose the way a reader would and reports back on it, including a check for writing that sounds machine-made, without rewriting a word. Use when the author wants a piece read rather than worked on.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
---
# manuscript-review

Reading finished prose rather than building it. Prose still being built is
`src/skills/prose-drafting/SKILL.md`.

## The boundary

- **Review comments, flags, accepts or rejects, and never rewrites.** A reviewer
  that writes prose has stopped being a fresh reader, and fresh reading is what
  the pass is for.
- **Reconciling a passage the author sends back is assembly only** — their new
  text placed against the untouched text, and nothing else. Not one sentence of
  connective tissue.

## Procedure

Four reads. The user's request names one.

1. **Zero-context reader test.** Read the raw prose with no lore, outline or
   reference material in hand: where attention held, where it drifted, what
   confused, what the reader expected next. **Withhold the reference material
   deliberately** — the read is worth having only while it is uncontaminated by
   context the real reader will not have. Where the session has already loaded
   the project, hand this read to the configured second model
   (`src/skills/external-ai-bridge/references/writers_room.md`); a session cannot unread what
   it holds.
2. **Reader critique.** Conversational, essayistic: what lands, what does not,
   where attention drifts, where a promise the prose made goes unpaid.
   **Directional suggestions, never prose.**
3. **Style scan.** Walk the prose line by line for machine-prose tells —
   hedging, over-balanced "not just X but Y" constructions, generic sensory
   filler, tidy summary closers, dash tics, register flattening. Flag each in
   place and name the tell. **Running the same checklist on a second model is an
   option, never a precondition for the scan.**
4. **Originality scan.** Mechanism: `tools/_shared/originality_scan.md`. **Run
   it on explicit request only** — it is expensive.

## Failure modes

- **A flag turns out to be a story or world problem rather than a prose one** →
  hand it to `src/skills/story-proposals/SKILL.md` rather than resolving it here.
- **The author asks for the passage fixed rather than flagged** → that is
  `src/skills/prose-drafting/SKILL.md`, entered deliberately and named as the switch it is.
- **A scan wants the voice profile** → the style scan reads prose only. Voice
  material reaches `src/skills/voice-distillation/SKILL.md` and stops there.

## Where the output goes

Comments and flags go to the user, and a full write-up to
`markdown_notebook.agent_output_dir`. **Every directory the user authors in is
read-only to this agent** (`writers_room.md` §Write Authority).
