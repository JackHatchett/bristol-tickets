# anti_plagiarism_checklist.md — game_designer tool

A fixed originality self-check, run on any name, character, beat, or design
before it's proposed as ready to lock — by `game_designer` itself, or by the
external Gemini Gem per `protocols/game_designer/gemini_gem_bridge.md`.
Referenced from `playbooks/game_designer/design_proposals.md` and
`socratic_design_coaching.md`; the mechanism lives here once, not repeated
in either.

## The line: inspiration vs. infringement
- **Allowed (mood):** borrowing a register, rhythm, or mood from a stated
  inspiration touchstone (a project's own worldbuilding/art-direction notes name
  its touchstones — read what the project actually calls that file rather than
  assuming a name).
- **Not allowed (content):** reusing a named character, a specific plot
  device, a signature line, a distinctive creature/world design, or a
  recognisable structure from any existing work. Borrowing the *thing
  itself*, not just its mood.

## The self-check — run before proposing
For any name, character, beat, or design, ask:
1. **Name check** — does this name belong to a known character, place,
   brand, or work? If unsure, treat as risky and offer an alternative.
2. **Device check** — is this plot/puzzle device lifted from a specific
   known story, or is it built from this project's own established
   mechanics? Prefer the latter; derive from the project's own logic rather
   than reaching for a genre cliché.
3. **Phrase check** — is any line a recognisable quote/paraphrase from a
   known work? Rewrite in the project's own voice.
4. **Silhouette check** — does a character/creature design read as a known
   IP's design? Diverge the silhouette, palette, or defining feature.

## When something feels close
Tag it `SIMILARITY_FLAG` (per the status taxonomy in
`protocols/game_designer/gemini_gem_bridge.md`), name what it resembles, and
propose a concrete divergence in the same pass. Never quietly ship a
near-copy. Better to flag a false alarm than to let one through — leave it
`OPEN_Q` until the user explicitly clears or reworks it (see
`design_proposals.md`'s failure modes).

## Note on tooling
A standalone automated similarity-audit tool has been discussed but does
not exist as a script anywhere in this framework. Until one does, this
checklist is the actual guardrail — applied by hand, every time, not a
placeholder for automation that isn't there yet.
