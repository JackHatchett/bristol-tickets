# Local LLM Fallback — career_coach protocol

**Specializes `protocols/_shared/external_ai_bridge.md`.** The six common
invariants live there and are not restated here. This file carries only the
delta for running the JD-triage/cover-letter workflow on a local, offline LLM
(e.g. an AnythingLLM-style workspace over an Ollama-style model) when the
primary system isn't available.

- **Memory model:** local-LLM session — the contract lives in the runtime's
  **system-prompt field**; static reference is pinned/embedded; live files are
  read and written fresh from shared disk.
- **Direction:** the local model *executes* the same evaluation and drafting
  logic as the interactive session, on much weaker/offline hardware.
- **Payload:** the file tiers below; all paths resolve via `/config`.
- **Return format:** direct write-back on shared disk (the local runtime shares
  the directory), with a labeled full-file fallback if it can't write.
- **Guardrails cited, never restated:** the zero-dash constraint, banned-
  language list, voice inhabitation-not-imitation guidance, locked-decisions
  rule, approach-label suppression, and referral trigger are exactly the rules
  in `jd_evaluation.md` and `cover_letter.md`.

## Placement matters

The governing prompt must live in the local workspace's **system prompt
field**, never as an uploaded/embedded document. An embedded copy only
surfaces a few retrieved fragments to the model, which is enough for it to
ignore the protocol entirely and return a generic response with no real
verdict. The context files (identity/positioning, resume, voice profile,
etc.) are the right thing to embed/pin — the system prompt is what governs,
they are the data it reads. This protocol overrides anything retrieved from
those documents; if a retrieved snippet conflicts with the steps in the
system prompt, the system prompt wins.

## File tiers

- **Static reference** (rarely changes): identity/positioning, the ATS resume
  text, the voice-profile core file, the cover-letter spec, the blacklist.
  Safe to pin or embed for reliable retrieval.
- **Live read/write** (changes every session): the applications tracker (the
  `applications` table in `data/*/personal/db/personal.db`) and any context
  module updated this session. Never rely on an embedded copy of these — read
  them fresh from disk and write changes back to disk, so a later interactive
  session resumes cleanly from the same source. Do not embed deep
  employment-history detail; it goes stale and must stay writable. (There is no
  separate live "state file" or "change log"; the tickets db and the applications
  tracker are the record.)

## Domain-specific quirks

The local model has no automated lint tool (the `cl_lint.py` gate does not run
here), so it must scan its own draft against the blacklist by hand before
delivering, and re-check the zero-dash and banned-language rules on every
draft since weaker/offline models drift more than the primary system does.
Because weaker models drift toward vague "good fit" language without a rigid
structure, the local system prompt should force a strict fill-in output
template for the verdict rather than leaving the format to the model's
judgment. Protocol A (JD evaluation) and Protocol B (cover letter) otherwise
run the same verdict vocabulary, global disqualifier, and context-once gate as
the interactive session.

## Session closure: write-back is mandatory

Because the interactive session shares the same directory and resumes from
the same source, the local model must write its changes back to disk, not just
print them in chat: append pending rows to the applications tracker
(`data/*/personal/db/personal.db`) and write any context-module updates back to
their files. If the local setup cannot write to disk (no DB access offline),
output each change's full updated contents clearly labeled instead, and tell
the user which records changed, so they can apply them in the next interactive
session.

## Operational notes

Works with any local model via an Ollama-style runtime; model choice and
quantization are an instance-specific hardware decision, not part of this
protocol. Prefer quoting the source files over improvising the user's history
or voice from memory — a weak model's training-data guess is never an
acceptable substitute for the actual context file.

## Cross-links
- `protocols/_shared/external_ai_bridge.md` — the archetype this specializes.
- `src/agent_identities/career_coach.md` and the `jd_evaluation.md` /
  `cover_letter.md` playbooks — the guardrails cited above, never restated.
- `protocols/career_coach/gemini_gem_bridge.md` — the hosted-Gem sibling bridge.
