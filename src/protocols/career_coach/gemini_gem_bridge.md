# Gemini Gem Bridge — career_coach protocol

**Specializes `protocols/_shared/external_ai_bridge.md`.** The six common
invariants (stateless, non-authoritative, briefed-not-connected, can't write
the source of truth, returns a clean block, sync discipline) live there and
are not restated here. This file carries only career_coach's delta.

- **Memory model:** persistent KB, manual refresh — a fixed set of knowledge
  files uploaded to a standalone Gemini Gem twin of the JD-triage/cover-letter
  system.
- **Direction:** the Gem *executes* the same evaluation and drafting logic as
  the interactive session, on a file-less host.
- **Payload:** the numbered knowledge-file set below; the filled-in files (and
  the Gem's paste-ready instructions) live in the user's own instance project
  under `data/*`, never under `src/`.
- **Return format:** pasted text block — the `TRACKER HANDOFF` packet below.
- **Guardrails cited, never restated:** `jd_evaluation.md` and
  `cover_letter.md` hold the verdict vocabulary, global disqualifier, approach
  menu, voice guardrails, AI-ism self-review, and blacklist. The Gem runs the
  same logic on a different host.

## What the Gem does differently (the delta that matters)

Because it is stateless and file-less, three behaviors are deliberately
different from the interactive session, not bugs to fix:

- **It researches itself.** Where the interactive session hands the user a
  research prompt to run externally, the Gem uses its own built-in
  search/knowledge directly, since it has no user to hand a prompt back to
  mid-chat.
- **It does not ask the context question.** `jd_evaluation.md`'s "ask once"
  gate exists to let the interactive session pause for user input before
  committing to a letter. The Gem has no persistent session to pause within,
  so it skips straight to a verdict, and to a letter or handoff the moment
  the user asks for one or says they applied.
- **It hands off instead of writing.** It cannot touch the applications
  tracker or build the styled docx header. Every time an application
  proceeds, it emits the handoff packet below for the user to bring back into
  the interactive session.

One operational quirk from the file-less host: there is no automated lint
tool, so the Gem must scan its own draft against the blacklist by hand before
delivering.

## Knowledge file map (pattern, not content)

The Gem's knowledge base is a fixed set of uploaded files mirroring the
interactive session's context modules, numbered so a stateless model can be
told exactly which one to pull for a given task without guessing:

| Slot | Purpose |
|---|---|
| identity/positioning | Career narrative, positioning, work preferences, locked decisions — read for almost everything |
| resume | Resume content and the ATS keyword source of truth |
| employment history | Deep employer detail for tailoring specific roles |
| domain/PM-craft modules | Load only the section matching the role |
| voice profile (core) | Voice calibration; read before any letter |
| voice profile (full interview) | Reference only for deep recalibration; large, expensive |
| approach menu + anecdotes | Cover-letter approach menu and proof-point anecdotes |
| blacklist | Banned-language list; the Gem's manual lint gate |

The actual filled-in knowledge files (and the Gem's full paste-ready
instructions text, which necessarily inlines identity, voice, and anecdote
detail since the Gem cannot read `src/` at runtime) live in the user's own
instance project, never under `src/`. This protocol describes the shape that
text must take, not its content.

## The handoff packet

Whenever an application proceeds (the user asks for a letter, or says they
applied), the Gem emits a fenced, clearly delimited block the user pastes
into the interactive session:

```
===== TRACKER HANDOFF (paste into career-coach project) =====
Company:        [hiring company name]
Role:           [exact role title from the JD]
Fit Notes:      [one or two lines: the narrative hook and the one honest gap]
Location:       [from the JD, or "Remote" / "Hybrid" / city]
ATS Platform:   [Greenhouse / Lever / Workday / LinkedIn Easy Apply / unknown]
Date Evaluated: [today's date, YYYY-MM-DD]
Cover Letter:   [Yes, filename <User>_Cover_Letter_[Company].docx | No]
Status:         [Letter drafted, not yet applied | Applied]
Contact:        [named internal contact, or "None"]
Referral:       [Yes / No]
JD Link:        [cleaned application URL, tracking parameters stripped, or "not provided"]
Year:           [current year]
>>> JD TEXT FOR ARCHIVE (only if the user pasted the JD text in this chat) <<<
[verbatim JD text, so the interactive session can archive it]
===== END TRACKER HANDOFF =====
```

Rules for the packet: strip tracking parameters from any URL but treat the
URL itself as an opaque string (never browse it just to clean it); include
the JD-text block only when the user actually pasted JD text in that
conversation; never emit a handoff for a Skip verdict, since a Skip isn't
pipeline data.

## Cross-links
- `protocols/_shared/external_ai_bridge.md` — the archetype this specializes.
- `src/agent_identities/career_coach.md` and the `jd_evaluation.md` /
  `cover_letter.md` playbooks — the guardrails cited above, never restated.
- `protocols/career_coach/local_fallback.md` — the offline-LLM sibling bridge.
