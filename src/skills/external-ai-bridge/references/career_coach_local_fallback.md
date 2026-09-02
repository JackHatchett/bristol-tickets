# Local LLM Fallback — career_coach protocol

Specializes `src/skills/external-ai-bridge/SKILL.md`, which holds the six
common invariants. This file carries only the delta for running the triage and
cover-letter workflow on a local, offline LLM when the primary system is
unavailable.

- **Memory model:** local-LLM session — the contract lives in the runtime's
  system-prompt field, static reference is pinned or embedded, and live files
  are read and written from shared disk.
- **Direction:** the local model executes the same evaluation and drafting logic
  as the interactive session, on weaker hardware.
- **Payload:** the file tiers below; all paths resolve via `/config`.
- **Return format:** direct write-back on shared disk, with a labeled full-file
  fallback where it cannot write.
- **Guardrails cited, never restated:** the zero-dash constraint, banned-language
  list, voice inhabitation guidance, locked-decisions rule, approach-label
  suppression and referral trigger are the rules in `src/skills/jd-evaluation/SKILL.md` and
  `src/skills/cover-letter/SKILL.md`.

## Placement

**The governing prompt lives in the local workspace's system-prompt field,
never as an uploaded or embedded document.** An embedded copy surfaces only a
few retrieved fragments, which is enough for the model to ignore the protocol
and return a generic response with no real verdict. The context files are the
right thing to embed; the system prompt is what governs them.

**Where a retrieved snippet conflicts with the system prompt, the system prompt
wins.**

## File tiers

- **Static reference**, rarely changing: identity and positioning, the ATS
  resume text, the voice-profile core, the cover-letter spec, the blacklist.
  Safe to pin or embed for reliable retrieval.
- **Live read and write**, changing every session: the applications tracker (the
  `applications` table in `data/*/personal/db/personal.db`) and any context
  module updated this session. **Read these fresh from disk and write changes
  back**, so a later interactive session resumes from the same source. **Never
  embed deep employment-history detail** — it goes stale and must stay writable.

## Domain quirks

- **The local model scans its own draft against the blacklist by hand.** The
  `voice_lint.py` gate does not run here.
- **Re-check the zero-dash and banned-language rules on every draft.** Weaker
  offline models drift more than the primary system.
- **Force a strict fill-in output template for the verdict** in the local system
  prompt, rather than leaving the format to the model. Without a rigid
  structure, weaker models drift toward vague "good fit" language.
- **Protocol A (JD evaluation) and Protocol B (cover letter) otherwise run the
  same verdict vocabulary, global disqualifier and context-once gate** as the
  interactive session.

## Session closure

**Write changes back to disk rather than printing them in chat**: append
pending rows to the applications tracker and write context-module updates back
to their files. **Where the local setup cannot write to disk, output each
change's full updated contents clearly labeled** and tell the user which records
changed, so they can apply them in the next interactive session.

## Operational notes

Model choice and quantization are an instance-specific hardware decision rather
than part of this protocol. **Quote the source files rather than improvising the
user's history or voice from memory** — a weak model's training-data guess is
never an acceptable substitute for the actual context file.

## Cross-links

- `src/skills/external-ai-bridge/SKILL.md` — the archetype this specializes.
- `src/agent_identities/career_coach.md`, `src/skills/jd-evaluation/SKILL.md`,
  `src/skills/cover-letter/SKILL.md` — the guardrails cited above.
- `src/skills/external-ai-bridge/references/career_coach.md` — the hosted sibling bridge.
