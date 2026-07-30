# voice_capture

A single-purpose tool: a fixed 100-question interview prompt
(`voice_capture_interview.md`) that produces a full voice-profile document for
whatever the user is being interviewed as (career_coach's cover letters and
recruiter emails, but the interview itself is domain-agnostic).

Dormant by default. Runs only on an explicit request for a fresh capture or a
recalibration — never at session start, never opportunistically. The output
(a `VOICE PROFILE` markdown document) is personal content and belongs in the
user's own instance data, never under `src/`.

Once produced, the resulting voice-profile file is what `cover_letter.md`
reads in full, once per session, at the moment of first composition — see
that playbook's "Voice" section for how it's actually consumed.
