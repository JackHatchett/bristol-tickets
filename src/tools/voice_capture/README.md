# Voice Capture

Input is the user, answering. Operation is `voice_capture_interview.md`, a fixed
100-question interview. Output is a `VOICE PROFILE` document holding how they
think and write.

- **Run it only on an explicit request for a capture or a recalibration** —
  never at session start, never opportunistically.
- **Write the profile into the user's own instance data**, never under `src/`.
- **The interview is domain-agnostic.** Whatever the user is interviewed as is
  what the profile covers.

`tools/writing_tools/voice_capture.md` is the other method: sample-first, for
sentence-level craft the person cannot articulate.
`playbooks/career_coach/cover_letter.md` §Voice owns how a profile is consumed.
