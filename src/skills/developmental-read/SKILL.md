---
name: developmental-read
description: Reads a finished draft for its structure the way a reader meets it - where attention holds and drifts, what confuses, which promises go unpaid - and reports back without rewriting a word, including a read by a second model that knows nothing of the project. Use when the author wants a draft read for what the story does rather than how the sentences run.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.subtitle: Read a draft for its structure and report back
---
# developmental-read

Input: a finished passage, chapter or draft. Operation: one of the reads below,
as the author's request picks. Output: comments and flags on the story's
structure, and no prose.

The prose read of the same draft — line by line, for voice and machine-made
writing — is `src/skills/manuscript-review/SKILL.md`. Prose still being built
is `src/skills/prose-drafting/SKILL.md`.

## The boundary

- **Comment, flag, accept or reject, and never rewrite.** A reader who writes
  prose has stopped being a fresh reader.
- **A flag that turns out to be about the sentences rather than the story** is
  the prose read's, and is handed over as such.

## The reads

1. **Zero-context reader test.** Read the raw prose with no lore, outline or
   reference material in hand: where attention held, where it drifted, what
   confused, what the reader expected next. **Withhold the reference material
   deliberately** — the read is worth having only while it is uncontaminated by
   context the real reader will not have. Where the session has already loaded
   the project, hand this read to the configured second model
   (`src/skills/external-ai-bridge/SKILL.md`); a session cannot unread what it
   holds.
2. **Reader critique.** Conversational, essayistic: what lands, what does not,
   where attention drifts, where a promise the prose made goes unpaid, where a
   beat the outline gives is missing from the page. **Directional suggestions,
   never prose.**

## Failure modes

- **A flag is a story or world problem the outline has settled otherwise** →
  `src/skills/story-proposals/SKILL.md`, rather than resolving it here.
- **The author asks for the passage fixed rather than flagged** → that is
  `src/skills/prose-drafting/SKILL.md`, entered deliberately and named as the
  switch it is.

## Where the output goes

Comments and flags go to the author, and a full write-up to
`markdown_notebook.agent_output_dir`. A directory the author writes in takes a
proposal rather than a write, by the Write Authority clauses the agent's
charter gives.
