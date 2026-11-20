---
name: copyediting-to-a-house-style
description: Copyedits a passage of finished prose to the house style in force and the project's style sheet, flagging each departure with the rule it departs from. Use when a draft passage, chapter or manuscript is to be checked for grammar, punctuation, consistency or style.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3.
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.scripts: src/tools/writing_tools/house_style.py
  bristol.subtitle: Copyedit prose to a house style
---
# copyediting-to-a-house-style

Input: a passage of finished prose. Operation: the pass below, against the
house style in force and the project style sheet. Output: a list of flags, one
per departure, each giving the rule.

## The style in force

- **Resolve the house style before reading the passage** — `python3
  src/tools/writing_tools/house_style.py <your slug>`. It prints the style and
  its rules file, from `agents.<agent>.house_style` in config.
- **Read the rules file whole**: `references/<style>.md`, beside this file.
  Each rule there carries the ID a flag cites.
- **A style that is set but not built stops the pass.** The tool exits 2 and
  gives the style and the styles built; say both to the user, and the pass
  runs once the setting is one that is built or the style is built.
- **Read the project style sheet**, by
  `src/skills/keeping-a-project-style-sheet/SKILL.md`, for the project the
  passage belongs to.

## Precedence

- **The project style sheet wins over the house style** for every entry it
  states: a spelling, a capital, an accent, an italic, a number or date form,
  and each departure the author has chosen.
- **The house style wins over the copyeditor's own preference** wherever the
  style sheet is silent.
- **A choice of voice is the author's.** A fragment, a splice or a
  nonstandard form in dialogue or close interior voice is a query, never a
  correction, and the rule that applies says so where it does.

## The pass

1. **Read the passage once through** before flagging anything.
2. **Flag each departure in order of appearance**, one flag per instance:

   ```
   <ID> | <the text as it stands> → <the text proposed> | <one line: what the rule asks>
   ```

   An entry of the style sheet is cited as `SHEET:<entry>`. A query takes `?`
   after the ID and gives the choice rather than a replacement.
3. **Flag inconsistency the style sheet does not settle**: the same name,
   number or term written two ways in the passage. Propose the form the notes
   use, and the entry the style sheet lacks.
4. **Leave structure and the sentence's music alone.** A beat, an arc or a
   world rule in doubt goes to the Developmental Editor as a card; a sentence
   that is correct but weak goes to the Line Editor as a card.

## Output

- **The flag list goes where the request came from**: the card the passage
  belongs to, or the agent-output folder for a whole chapter or manuscript.
- **The prose is proposed, never rewritten in place**, by the common fiction
  clauses' write authority.
- **New style-sheet entries the pass found go into the style sheet** by its
  skill, and the flag list gives each one added.

## Failure modes

- **A flag with no rule ID** → the departure is a preference; drop it.
- **A house-style correction applied over a style-sheet entry** → §Precedence;
  the sheet wins.
- **A pass run on the style in memory rather than the file** → the rules file
  is read every pass.
