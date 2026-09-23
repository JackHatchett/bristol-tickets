---
name: researching-the-market
description: Hands the market research stage over as a hub and five blank forms - the questions the stage has to answer, who the customer is and how many, the competitors and their prices, the survey or interviews, and the published figures - each field saying what a usable answer looks like. Use when market research is the stage being worked, or when the user asks for help with one part of it.
license: MIT
compatibility: Runs where the user's Markdown notebook is reachable; needs python3 to resolve where the packet is filed and to write the board. Filling a form needs whatever source that answer comes from.
metadata:
  bristol.kind: playbook
  bristol.maintainer: business_advisor
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/ticket_tools/ticket_write.py
---
# researching-the-market

Input: a business concept in a sentence, and the place it trades in. Operation:
the procedure below. Output: the market research stage elaborated into a hub and
five forms, blank, inside the business's packet.

`src/skills/road-to-opening/SKILL.md` §The packet shape defines the hub, the
stage note, what a form asks and which facts go on a card. This skill restates
none of it, and adds only what this stage's forms ask.

## What the stage is for

- **The stage answers what the model will be built from**: how many buyers are
  reachable, what they pay today, and what they would pay for this.
- **Write the questions before any of them is answered**, so the user sees the
  whole stage rather than whichever question the session started with.
- **Write nothing the user did not ask for.** Scaffolding is the output; a
  filled answer is a separate request — §Filling part of a form.

## The five forms

One note each, wikilinked from the stage note, each question a `##` section
left blank with what a usable answer looks like beside it.

- **The questions this stage has to answer** — the decisions downstream that
  turn on this stage, and the question each one needs settled. A usable answer
  states the decision, the question, and the figure or fact that would settle it.
- **The customer, and how many** — who buys, how many of them are reachable
  from where the business trades, how often they buy, and what share of them buy
  this at all. A usable answer is a count or a rate for a named area, from a
  published table or a survey, with its link and its year.
- **The competitors, and what they charge** — a table, and the stage gives its
  columns and how many rows it needs before the table is a finding rather than
  three examples. Columns: the business, what it sells that competes, its price
  by the unit the buyer compares, how it is bought, and the source. A usable row
  is a business currently trading in the area, priced as its own page or system
  states it.
- **The survey or the interviews** — who is asked, how many, how they are
  reached, and the questions in the words they will be put in. A usable answer
  is a question that a person can answer without knowing the business exists,
  and that a later stage can count.
- **The published market and financial figures** — the industry figures the plan
  and the lender will expect: market size, growth, typical margins, typical
  costs per unit of capacity. A usable answer is a figure with its publisher,
  its year, and the geography it covers.

- **Shape each form to the concept.** The five parts are fixed; the questions
  inside one are the ones this concept has to answer, and a question that does
  not apply is left out rather than asked emptily.
- **Name the unit the concept is bought in** — a visit, a bottle, a month, a
  seat — in every form that asks about price or volume, so the answers can be
  multiplied together.

## Filling part of a form

The condition is the user asking for a part: some rows, one section, a question
he is stuck on.

- **Fill only what was asked**, and leave the rest of the form as it was.
- **Carry the source in the sentence that states the value**, so what the
  session produced and what the user produced are told apart by reading.
- **Say what a value is when it is not a finding** — an estimate, a figure for a
  neighbouring area, a range two sources disagree across — in the same sentence.
- **Leave a question that cannot be sourced blank**, and write beside it what
  would answer it and where that is held.

## The gate

- **Read the forms to see what the stage has produced** —
  `src/skills/road-to-opening/SKILL.md` §The gate.
- **Meet a request for later-stage work with the blanks and what each would
  change** — the same file, §Work asked for from further down the road.

## What goes on the board

`src/skills/road-to-opening/SKILL.md` §What goes on the board. This stage adds
nothing to it: the questions are the forms', and a card is the stage's, a date's
or a decision's.

## Procedure

1. **Take the concept and the place**, and ask for whichever is missing.
2. **Name the decisions downstream that this stage settles**, which is the first
   form's content.
3. **Write the stage note** into the business's packet, wikilinked to the five
   forms.
4. **Write the five forms blank**, each question with what a usable answer looks
   like beside it, shaped to the concept and its unit.
5. **File one card for the stage**, and a card for any date or decision the
   stage itself produces.
6. **Read the forms back against three checks**, fixing what fails: nothing is
   filled in that was not asked for, every question states what a usable answer
   looks like, and the competitor table gives its columns and its row count.
7. **Return at the gate** and plan the next stage from what the forms say.

## Failure modes

- **Three competitors the session picked** → the form was answered instead of
  written; it gives columns and a row count, and the rows are the user's to
  fill or to hand back.
- **A market size with no publisher or year** → §The five forms; a figure
  without those is not usable in a plan a lender reads.
- **A survey question that assumes the business exists** → it measures
  agreement rather than behaviour, and the answers cannot be counted.
- **A form filled in unasked** → §Filling part of a form; the user can no
  longer tell his own answers from the session's.
- **Volume in one unit and price in another** → §The five forms; the two never
  multiply, and the model cannot be built from them.

## Audit

**Whether the user can look at the stage once and know every question he has to
answer, and hand any single one of them back.**
