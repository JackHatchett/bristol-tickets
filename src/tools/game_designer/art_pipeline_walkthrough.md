# Art Pipeline Walkthrough

Input is an asset brief and the project's own art-direction file. Operation is
the three-stage production sequence below, walked through with the user. Output
is a finished asset in the engine's format.

- **Read the parameters from the project's art-direction file** — locked style
  reference, palette, aspect-ratio conventions. Check its actual name rather
  than assuming one. This file holds the steps and never a project's look.
- **Trust a tool's on-screen labels over the wording here.**
  // Each stage's concept — style reference, layered cleanup,
  // character-consistency training — outlives the button names.

## Stage 1 — generation

An AI image generator prompted with text and optionally a reference image.

1. **Build the prompt from the project's style template**, filling only the
   subject, setting and framing slots and keeping the style tail constant, so
   every asset reads as one world.
2. **Submit it** and take the four returned thumbnails.
3. **Upscale the preferred thumbnail.** Nudge a near-miss with the variation
   control rather than re-rolling.
4. **Use the platform's current reference-image mechanism for a recurring
   character**, to say "keep this person, new scene."
5. **Save the chosen image as a PNG, and record the seed and the exact prompt**
   into the project's asset record, so the look stays reproducible.

## Stage 2 — cleanup

A painting and image-editing program, where generated output becomes a usable
asset. This stage is the hub: everything passes through it on the way to the
engine.

1. **Open the PNG and import any additional element onto its own layer.**
2. **Erase artefacts, fix edges, remove stray baked-in text.**
3. **Match the project's baseline palette** — usually a saturation and contrast
   pass, not a repaint.
4. **Cut a sprite or item out** by selecting the subject, adding a transparency
   mask and deleting the background.
5. **Export as PNG**, transparency on for a sprite or item and off for a
   full-scene background, named to the asset's ID convention.
6. **Never pre-bake an effect the engine applies at runtime.** The
   art-direction file says what arrives clean and what the engine handles live.

## Stage 3 — character-consistency training

Optional. A tool that trains a small model on one character so it can be
generated in any pose or scene.

- **Settle the character's reference look in stage 1 first**, recording it
  through `src/skills/design-proposals/SKILL.md`. A model trained on an
  unsettled design locks in the wrong face.
- **Reach for it only when stage 1 alone stops holding consistency.**

1. **Create a character model** and upload a spread of that character's best
   generated outputs — varied angles and expressions, consistent outfit.
2. **Take the tool's recommended base training model.**
3. **Train**, which takes real wall-clock time.
4. **Compare checkpoints side by side on a test prompt before finalizing.** A
   later checkpoint is not automatically better.
5. **Generate poses, expressions and scenes from the trained model**, using the
   character-combination feature where two trained characters share a scene.
6. **Return the output to stage 2** for cleanup, then to the engine.
