# tools/writing_tools/ — shared prose/authoring machinery

Not owned by any one agent. Reusable machinery for capturing an author's
voice and scaffolding drafts, for any agent that does creative or long-form
writing work — extracted from `writers_room`'s design so it isn't locked to
one novel-writing agent.

## What's here

- `voice_capture.md` — the sample-first method for capturing a writer's
  prose voice as evidence (mined from existing writing, or elicited with a
  small exercise) rather than by self-report. See the file for how this
  differs from `tools/voice_capture/voice_capture_interview.md`
  (career_coach's direct-interview method) and when each fits.
- `templates/` — project-agnostic `.md` scaffolds: `beat-sheet-chapter.md`,
  `draft-chapter.md`, `draft-scene.md`. Fill-in-the-blank structure only, no
  content.

## How an owning agent uses this

Same pattern as `tools/wiki_tools/`: an owning agent's charter/playbooks describe
the domain-specific application (whose voice, which project, what the
technique inventory looks like); they point here for the reusable mechanism
rather than re-describing it. `playbooks/writers_room/voice_distillation.md`
is the reference example.
