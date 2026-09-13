---
name: road-to-opening
description: Hands the user the whole road from a business concept to open doors as one packet - every stage in outline, the stage in front of him elaborated into its own forms, and the gate each stage has to pass before the next one is planned. Use when work on a business opens, when a stage is finished and the next one starts, or when something is asked for that belongs further down the road.
license: MIT
compatibility: Runs where the user's Markdown notebook is reachable; needs python3 to resolve where the packet is filed and to write the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: business_advisor
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/ticket_tools/ticket_write.py
---
# road-to-opening

Input: a business concept in a sentence, and the stage the user is about to
work. Operation: the procedure below. Output: one packet — a hub note naming
every stage between the concept and opening, and the live stage elaborated into
its own note and forms — plus one card for the live stage and one for each date
and each decision.

Three terms, used throughout:

- **A stage** is one span of the road that answers its own questions and hands
  the next span something it cannot start without.
- **The live stage** is the stage being worked now. It is the only one
  elaborated.
- **A packet** is the folder holding the hub and whatever stage notes have been
  elaborated so far.

Two named practices give the shape. **Rolling wave planning** details the near
work and leaves later work in outline until it approaches. **A stage gate** is
the point where what a stage produced is read before the next stage is planned.
Everything below is those two applied to opening a business.

## What the input has to name

- **The concept in one sentence** — what is sold, to whom, and where.
- **The live stage**, where the user names one.
- **Take the live stage as the earliest stage whose questions are unanswered**
  where he names none, reading the packet's forms to find it.
- **Ask for the concept rather than working from an inferred one.** Every stage
  is tested against that sentence, so a wrong one is wrong twelve times.
- **Treat a changed concept as a new input.** The road is rewritten from it, and
  a stage whose answers rested on the old sentence is elaborated again.

## The road

Twelve stages. Each is named in the hub with what it answers, what it needs from
the stages before it, what it hands the ones after, and its gate.

- **Concept definition** — what is sold, to whom, where, and why they would
  choose it over what they do today. Needs nothing. Hands on the sentence every
  later stage is tested against.
- **Market research** — who the customer is and how many of them there are, who
  already serves them and at what price, and what published figures say about
  the market. Needs the concept. Hands on the demand and price evidence.
- **The model and its unit economics** — the price, the cost of one unit sold,
  the fixed costs, and the volume at which the two meet. Needs the research.
  Hands on the numbers every projection rests on.
- **Concept proof** — the cheapest test that would change the decision. Needs
  the model's assumption that hurts most if it is wrong. Hands on evidence that
  replaces that assumption.
- **The plan** — the written business plan. Needs the four stages above. Hands
  on the document money and premises are asked for with.
- **Money** — how much is needed, in what form, from whom, and on what
  conditions. Needs the plan and its projections. Hands on committed funds, and
  the dates and covenants attached to them.
- **Premises** — where, on what terms, and whether the use is permitted there.
  Needs the space the model requires and the ceiling the money sets. Hands on an
  address.
- **Licensing** — what the exact combination of activities, address and
  headcount triggers. Needs all three.
  `src/skills/working-a-licence/SKILL.md` is the procedure. Hands on the
  requirements, their fees, their lead times and the long pole.
- **Build-out** — what the space has to become to pass inspection and open.
  Needs the lease and the licensing prerequisites. Hands on a dated path to an
  inspection.
- **Hiring** — how many people, in what roles, what each has to hold, and what
  employing them obliges. Needs the model's labour line and the people rules
  licensing imposes. Hands on staff and payroll obligations.
- **Supply** — what is bought, from whom, on what terms and lead times. Needs
  the model's volumes and the build-out's dates. Hands on opening stock and the
  recurring cost line.
- **Launch** — the opening date and what has to be true on it. Needs everything
  above in hand. Hands on an operating business, whose obligations become
  recurring.

- **The order is the default, not the rule.** Say in the hub which stages run in
  parallel for this concept, and re-run any stage whose input a later stage
  changed.
- **Name a stage this concept does not have, and why**, rather than dropping it
  silently.

## Only the live stage is elaborated

- **Elaborate the live stage into a stage note and its forms**, and leave every
  later stage the paragraph the hub gives it.
- **Never write a later stage's forms.** They would be written against answers
  the live stage has not produced, and they would have to be written again.
- **Plan the next stage from what the live stage produced**, at the gate, never
  from what was guessed when the road was drawn.
- **Keep a finished stage's note and forms where they are.** They are the
  record the later stages cite, and nothing marks them finished.

## The gate

- **Name every stage's gate in the hub**: the answers that stage has to have
  produced.
- **Write a gate as produced answers**, never as a date, a count or a
  proportion.
- **Pass a gate by reading the stage's forms**, which is reading content —
  `src/app.md` §The board is the only channel.
- **Re-read the gate of every upstream stage when a stage is re-run**, because a
  changed answer upstream is what re-opened it.

## The packet shape

Every stage skill writes this shape and restates none of it.

- **The hub** — one note per business, holding the concept sentence, the road as
  one bullet per stage in the order above, and a `## Related Notes` section
  linking each stage note that exists.
- **A stage note** — what the stage has to answer, a wikilink to each of its
  forms, and the stage's gate.
- **A form** — one note per part of a stage. Each `##` section is one question
  the stage has to answer, left blank, with what a usable answer looks like
  stated beside it.
- **What a usable answer looks like is the answer's shape**: its unit, how many
  rows or examples the stage needs, and what would make it evidence rather than
  an impression.
- **A value the session writes carries its source in the sentence that states
  it**, so what the agent produced and what the user produced are told apart by
  reading.
- **The notes hold answers, evidence, sources, reasoning, and the questions
  still blank.**
- **The board holds the live stage, every date, and every decision** — and
  nothing else about the packet.
- **No note carries a status marker of any kind** — no checkbox, no `DONE`, no
  percentage, no line saying how far along anything is. Which stage is live is
  legible from which stage has a note; which questions are answered is legible
  from whether the answers are written in.
- **`src/skills/note-formatting/SKILL.md` governs the filename, the
  frontmatter, the headings, the wikilinks and the closing section** of every
  note in the packet.

## Work asked for from further down the road

The condition is a request whose deliverable belongs to a stage after the live
one, with questions in an upstream form still blank.

- **Name the blanks, by the form and the section each sits in.**
- **Say what each blank would change in the thing being asked for** — the figure
  it feeds, the option it opens or closes, the requirement it decides.
- **Do not produce the deliverable.**
- **Name questions, never a status.** "Three prices and the rent are blank, and
  each moves the break-even" is the answer; "market research is incomplete" is
  not.
- **Offer the two moves that follow**: work the blanks, or take the one question
  the user is stuck on.
- **Produce it where the user directs it anyway, having read the questions**,
  with every value that rests on a blank naming the assumption it rests on in
  the sentence that states it.

## Where the packet goes

- **One folder per business under `markdown_notebook.business_dir`**, resolved
  through `src/tools/config_tools/data_paths.py` with `ensure_dir()` at the
  moment of the write.
- **The business's other documents stay in the folder
  `agents.business_advisor.key_data_paths` declares.** The notebook holds what
  the user hand-edits; research and drafts he reads rather than fills in are the
  other folder's.
- **One packet per business.** A second concept is a second packet; a changed
  concept rewrites the one that exists.

## What goes on the board

- **One card for the live stage**, `--assignee business_advisor`, signed with
  the running agent's slug.
- **A card for every date** — a filing window, an appointment, a lease term, a
  renewal, a decision that expires.
- **A card for every decision the user has to make**, carrying what turns on it.
- **Never a card per form or per question.**
- **Never a backlog seeded with the stages after the live one.** They would be
  written from guesses, and the board would carry a plan that has to be thrown
  away.
- **The card names the packet; no note names a card.**

## Procedure

1. **Take the concept sentence**, and ask for it where it is missing.
2. **Draw the road**: every stage in the order above, each with what it answers,
   what it needs, what it hands on, and its gate, adapted to this concept.
3. **Name the live stage** — the user's, or the earliest whose questions are
   unanswered.
4. **Write the hub** into the packet folder.
5. **Elaborate the live stage alone** into its note and its forms, blank, with
   what a usable answer looks like beside each question.
6. **File the board**: one card for the live stage, one for each date, one for
   each decision.
7. **Read the packet back against three checks**, fixing what fails: no stage
   after the live one has a form, no note carries a status marker, and every
   value the session wrote carries its source.
8. **Return to the hub at the gate**, when the live stage's questions are
   answered: read them, then elaborate the next stage from what they say.

## Failure modes

- **Forms for a stage that is not live** → step 5, and they were written against
  answers nobody has produced.
- **A checkbox, a `DONE` or a percentage in a note** → §The packet shape; state
  belongs on the board and nowhere else.
- **A card per question** → §What goes on the board; the questions are the
  form's, and the card is the stage's.
- **A downstream deliverable produced with the gaps filled quietly** → §Work
  asked for from further down the road; the assumptions went in unnamed and are
  now indistinguishable from findings.
- **A refusal that names a status** → the same section; the user cannot act on
  "incomplete", and can act on a list of questions.
- **The next stage elaborated from the road as first drawn** → step 8; the gate
  exists because the answers change the plan.
- **A stage dropped without a line saying why** → §The road; a reader cannot
  tell a stage that does not apply from one that was forgotten.

## Audit

**Whether the user can see the whole road and still have only this week's work
in front of him.** A packet that details a stage he cannot start has spent his
attention on answers that will be written again.
