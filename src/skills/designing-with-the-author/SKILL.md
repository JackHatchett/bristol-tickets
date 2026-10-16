---
name: designing-with-the-author
description: Designs a piece of a constructed language or of a fictional world with the author — which questions go to him, which choices the session makes itself, what it recommends, how a coined name or a language's sound is checked against those already given, and what completeness is measured against. Use when a language, a creature, a culture, an institution or any other piece of the world is being designed or extended, or a name coined.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.scripts: src/tools/wiki_tools/sound_check.py
  bristol.subtitle: Design a language or world with the author
---
# designing-with-the-author

Input: a piece of a language or of the world to design. Operation: the rules
below. Output: a design the author has decided, written into the note that holds
it. A proposal's route into the notebook is
`src/skills/story-proposals/SKILL.md`.

## Before proposing

- **Read the project's content-rules file first** —
  `src/skills/writers-room-project-context/SKILL.md` step 3. Where the project
  keeps its guidance for agents apart from its notes, that guidance is the file,
  and it holds the project's own lists of overused concepts and of assumptions
  the author never set.

## Who decides what

The author draws the world and the session colors it in. He draws the shapes
and chooses which crayons are in the box; the session fills the shapes, inside
the lines and with those crayons.

- **Color without asking when all three hold**, and report what was colored:
  - a note says the thing exists;
  - a note gives the rule for filling it in — a count, a structure, a naming
    logic;
  - the materials are in hand — a language able to build the names, a
    real-world model the author has approved for that culture.
  Naming each of a hundred family towers from the notes' count, house-name
  logic and coining rules is color. Expansive color of this kind is what the
  author most needs, so a detail used once in passing is still written into the
  note that owns it, where a later book will find it.
- **Ask about anything missing one of the three.** It is still sketch, and the
  author draws it. The questions the session itself raises are his to answer, and so is every
  principle for how a class of things is built.
- **A linguistic choice is the session's own** — a sound change, an affix's
  shape, which of several grammatical solutions a language of the type uses,
  how a word is coined. Make it, and report it with its reason.
- **Follow a burst of questions to its end.** One question begets more, and the
  burst is finite: every new need becomes a question in the session or a card.
- **Ask in the session, in batches, in plain words about the world**, never
  about linguistics. Each question says what the design needs the answer for and
  offers two to four concrete ideas, one of them recommended with its reason. A
  design too large to settle in the session goes to a card.
- **Two of the author's notes that cannot both be true are his to resolve.**
  The session brings him what replaces them, and the replacement is usually
  neither note as written.
- **Offer the replacement in the shape the ideas take.** Where one idea fits,
  recommend it alone for his approval; where several fit, offer two to four,
  one recommended with its reason. The correction he chooses is made under
  `src/agent_identities/writers_room.md` §2.3.
- **A domain becomes color once the author's logic for building it is written
  down**, in the guidance the project keeps for agents. Until then, building a
  new thing of that kind is sketch.

## What to recommend

- **Recommend what a real language or a real world of the type has.** Weigh
  solutions from at least three families or cultures, with Latin and English two
  data points among the rest.
- **Variety is the default, and every option offered is a varied, good
  design.**
- **Reuse an existing form or concept only where the culture would repeat it,
  and say why.** A root recurs the way a religion's central figure recurs in its
  names. Adding nothing, or using what already exists, is never a merit in
  itself.
- **Check how alike a class of things is in the real world before a rule makes
  it uniform**, and keep uniformity only in that proportion and for a stated
  reason — personal names, a species' body plans, a city's institutions.
- **Skew a real-world model rather than copying it.** Change its variables — a
  term of two years where history had one, a wider remit — so no framework
  arrives whole from Earth.
- **Coin every root and grammatical word of a constructed language in its own
  sounds and forms.** A core Earth language the design draws on lends it
  features — a case system, an aspect split, a word order — and none of its
  words.
- **Reshape a coined word that lands near an Earth word of the same meaning**
  until it is no longer recognisable as that word.

## Checking a name's sound

Input: a coined proper name, or a sample of words in a language's proposed
sound. Operation: `src/tools/wiki_tools/sound_check.py`, which reads every
language and every main character's name from the notes the config entry
`agents.writers_room.sound_check` lists. Output: the name or the sound, apart
from every other language and every main character's name.

- **Run `sound_check.py name <name> --language <its language>` on every coined
  proper name before it is offered or written**, adding `--character` for a
  main character's name.
- **Run `sound_check.py words <sample> --language <its language>` on a sample
  of ten or more words for each proposed sound of a language**, and the name
  check on each name the sample coins.
- **Replace whatever the check reports too near before it reaches the author**,
  and run the check again on the replacement.
- **Give each offered name or sound its nearest language and score** beside
  the option, so the author sees how far apart it stands.
- **Add a new language's notes to `agents.writers_room.sound_check.languages`
  in the session that writes its first words.**

## Measuring completeness

- **Measure against a published checklist** — a meaning list such as the World
  Loanword Database's for vocabulary, a grammar questionnaire such as Comrie and
  Smith's for grammar. Test sentences prove a design and set none of its scope.

## Writing it down

- **Write the decided design as he decided it**, in the note that holds it, by
  `src/templates/identity_template.md` §Words: the fact, and the sentence stops.
