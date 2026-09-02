# Gemini Gem Bridge — career_coach protocol

Specializes `src/skills/external-ai-bridge/SKILL.md`, which holds the six
common invariants. This file carries only career_coach's delta.

- **Memory model:** persistent KB, manual refresh — a fixed set of knowledge
  files uploaded to a standalone Gem twin of the triage and cover-letter system.
- **Direction:** the Gem executes the same evaluation and drafting logic as the
  interactive session, on a file-less host.
- **Payload:** the knowledge-file set below. The filled-in files, and the Gem's
  paste-ready instructions, live in the user's instance project under `data/*`,
  never under `src/`.
- **Return format:** pasted text block — the `TRACKER HANDOFF` packet below.
- **Guardrails cited, never restated:** `src/skills/jd-evaluation/SKILL.md` and `src/skills/cover-letter/SKILL.md`
  hold the verdict vocabulary, global disqualifier, approach menu, voice
  guardrails, AI-ism self-review and blacklist.

## The delta

Three behaviors differ from the interactive session by design, because the host
is stateless and file-less:

- **The Gem researches itself.** The interactive session hands the user a
  research prompt to run externally; the Gem uses its own search directly, since
  it has no user to hand a prompt back to mid-chat.
- **The Gem does not ask the context question.** `src/skills/jd-evaluation/SKILL.md`'s ask-once
  gate exists so the interactive session can pause for input before committing
  to a letter. The Gem has no session to pause within, so it goes straight to a
  verdict, and to a letter or handoff the moment the user asks or says they
  applied.
- **The Gem hands off instead of writing.** It cannot touch the applications
  tracker or build the styled docx header, so it emits the handoff packet every
  time an application proceeds.

**The Gem scans its own draft against the blacklist by hand before
delivering**; the file-less host has no lint tool.

## Knowledge file map

The Gem's knowledge base mirrors the interactive session's context modules,
numbered so a stateless model can be told exactly which one to pull.

| Slot | Purpose |
|---|---|
| identity/positioning | Career narrative, positioning, work preferences, locked decisions — read for almost everything |
| resume | Resume content and the ATS keyword source of truth |
| employment history | Deep employer detail for tailoring specific roles |
| domain and craft modules | Load only the section matching the role |
| voice profile (core) | Voice calibration; read before any letter |
| voice profile (full interview) | Reference only for deep recalibration; large and expensive |
| approach menu and anecdotes | The cover-letter approach menu and proof-point anecdotes |
| blacklist | Banned-language list; the Gem's manual lint gate |

**The blacklist slot is a copy of the canonical list and never an edited
version of it.** The Gem cannot read the disk, so the slot has to hold bytes;
refreshing it is a copy and re-upload, and a phrase is added to the canonical
file rather than to the slot.

**The filled-in knowledge files live in the user's instance project, never
under `src/`.** The Gem's instructions text necessarily inlines identity, voice
and anecdote detail, because the Gem cannot read `src/` at runtime; this
protocol describes the shape that text takes, not its content.

## The handoff packet

Whenever an application proceeds — the user asks for a letter, or says they
applied — the Gem emits a fenced block the user pastes into the interactive
session:

```
===== TRACKER HANDOFF (paste into career-coach project) =====
Company:        [hiring company name]
Role:           [exact role title from the JD]
Fit Notes:      [one or two lines: the narrative hook and the one honest gap]
Location:       [from the JD, or "Remote" / "Hybrid" / city]
ATS Platform:   [the applicant-tracking system named in the URL, or unknown]
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

- **Strip tracking parameters from any URL, and treat the URL itself as an
  opaque string.** Never browse it just to clean it.
- **Include the JD-text block only where the user pasted JD text in that
  conversation.**
- **Never emit a handoff for a Skip verdict.** A Skip is not pipeline data.

## Cross-links

- `src/skills/external-ai-bridge/SKILL.md` — the archetype this specializes.
- `src/agent_identities/career_coach.md`, `src/skills/jd-evaluation/SKILL.md`,
  `src/skills/cover-letter/SKILL.md` — the guardrails cited above.
- `src/skills/external-ai-bridge/references/career_coach_local_fallback.md` — the offline sibling bridge.
