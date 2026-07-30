# art_pipeline_walkthrough.md — game_designer tool

The generic three-tool art-production sequence this agent walks a user
through, project-agnostic. A project's own art-direction file (name varies by project — check what's
actually there rather than assuming) supplies the parameters this
walkthrough fills in (the locked style reference, palette, aspect-ratio
conventions) — this file describes the *steps*, never a specific project's
locked look.

> Tool facts here reflect each tool's state as last verified against a real
> project; if a tool's UI has since changed, trust its own on-screen labels
> over this file's exact wording — the underlying concepts (style
> reference, layered cleanup, character-consistency training) are stable
> even when button names drift.

## Stage 1 — Midjourney (generation)
An AI image generator prompted with text (and optionally a reference
image). Build every prompt from the project's own style template (its
art-direction file — check the project's actual file name), filling only
the subject/setting/framing slots and keeping the style tail constant so
every asset reads as one world.
1. Open Midjourney (web app or Discord). Start a prompt with `/imagine`
   (Discord) or the prompt bar (web).
2. Paste the filled prompt. Submit — this returns four thumbnails.
3. Upscale the preferred thumbnail for a full-resolution version; use the
   variation control to nudge a near-miss instead of re-rolling from
   scratch.
4. For a recurring character needing visual consistency across scenes, use
   the platform's current reference-image mechanism (name and mechanics
   change between model versions — check the current on-screen label
   rather than trusting a specific past parameter name) to say "keep this
   person, new scene."
5. Save the chosen image as a PNG. Record the seed (a number that lets the
   result be reproduced or triangulated) and the exact prompt used — both
   go in the project's asset to-do record so the look stays reproducible.
6. Hand off to Stage 2.

## Stage 2 — Krita (cleanup, the pipeline hub)
A free painting/image-editing program. This is where raw generated output
becomes a usable game asset.
1. Open the generated PNG. Import any additional elements onto their own
   layers (a layer is a clear sheet stacked on top, editable without
   touching the others).
2. Clean up: erase artefacts, fix edges, remove any stray baked-in text.
3. Match the project's baseline palette per its own art-direction file
   (typically a saturation/contrast pass, not a full repaint).
4. For a sprite or item needing a transparent cutout: select the subject,
   add a transparency mask, delete the background.
5. Export as PNG — transparency on for sprites/items, off for full-scene
   backgrounds. Name per the asset's own ID convention.
6. If the project's rendering approach applies an effect dynamically at
   runtime (e.g. a pixelation shader), do not pre-bake that effect by hand
   here — check the project's art-direction file for what the engine is
   expected to handle live versus what must be delivered clean.

## Stage 3 — Scenario.gg (character-consistency training, optional)
A tool that trains a small custom model on a specific character so that
character can be generated in any pose or scene. Use only once a
character's reference look is settled and Midjourney alone isn't holding
consistency well enough.
1. Create a character model; upload a spread of the character's best
   generated outputs (varied angles/expressions, consistent outfit).
2. Pick a base training model — use whichever the tool currently
   recommends as default; the user doesn't need to evaluate the options
   themselves.
3. Train (this takes real wall-clock time; the tool notifies on
   completion).
4. Compare training checkpoints side by side on a test prompt before
   finalizing — a later checkpoint isn't automatically better.
5. Generate poses/expressions/scenes from the trained model. Multi-
   character scenes may need the tool's character-combination feature if
   two trained characters need to appear together.
6. Export to Stage 2 (Krita) for final cleanup, then to the engine.

## Failure Modes
- **A tool's UI no longer matches this file's exact button names.** Trust
  the tool's current labels; the stage's *purpose* hasn't changed even if
  the interface has.
- **Skipping straight to Scenario without a locked Midjourney look first.**
  Don't train a character model on an unsettled design — settle the
  appearance first (record it in the repo `design/` art notes; see
  `design_proposals.md`), then train.
