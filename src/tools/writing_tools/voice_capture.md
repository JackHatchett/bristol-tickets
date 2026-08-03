# Sample-First Voice Capture

Input is a person's prose — an existing corpus, or a page written to an
exercise. Operation is reading specimens out of it and distilling each into a
technique card. Output is a voice library: a small always-on core profile, an
inventory, and a card per technique.

`tools/voice_capture/voice_capture_interview.md` is the other method: a
structured interview, which suits a voice the person can articulate under
questioning. This one assumes self-report is unreliable about sentence-level
craft. A domain may use both.

## Rules

- **Never ask the person to describe a technique before they have performed
  it.** Mine a specimen or elicit one, then read the specimen for the move.
- **Issue one exercise, or ingest one batch, per turn.** Never a menu.
- **Every specimen becomes a rule plus the verbatim line proving it.**
- **Quote a specimen exactly**, punctuation and line breaks included. A
  paraphrase is no longer evidence.
- **Keep the core profile small and let the card library grow.** Only the
  sharpest and most frequent moves reach the core.

## Two roles

- **Scout** — reads the prose and returns verbatim specimens with a short
  analysis of each. It never writes to the library.
- **Distiller** — receives specimens only, sets each card's confidence
  threshold, decides promotion into the core, and is the sole writer of the
  library.

The distiller sets a threshold on what the scout reports rather than on the
corpus, so the full source never influences it. Either role may be an external
AI or a mode of the same agent.

## Two intake paths

- **Mine** — point the scout at a body of existing writing in one pass. It
  returns specimens across every technique the corpus demonstrates, plus a
  lexicon: favoured words, avoided words, register, tics.
- **Elicit** — take the next unfilled technique from the inventory and issue
  its exercise as setup, constraint and cap. Name nothing about what it tests;
  naming the target contaminates the sample.

Mine first where a corpus exists: one pass fills many cards, and what it fails
to yield sets the exercise queue.

## Distilling a specimen

1. **Read it for its target move only** — not for quality, not to edit.
2. **Write or update that technique's card**: the rule, the verbatim specimen,
   a confidence threshold, a failure mode, links to related cards.
3. **Set the threshold from how clean the exemplar is and how often the move
   recurs.** One specimen rarely justifies the top tier; corroboration raises
   it.
4. **Update the technique's status in the inventory** — `empty`,
   `specimen-collected`, `distilled`, `promoted`.
5. **Promote a signature or high-frequency move's sharpest line into the core
   profile.**
6. **Distil one specimen into every card it serves**, rather than forcing one
   card per specimen.

## Layers

Loaded à la carte, on the lookup principle in `tools/wiki_tools/`:

| Layer | Loaded when | Size |
|---|---|---|
| Core profile | Every job | A page or two, and it does not grow with the library |
| Inventory | Deciding what a job needs | One lookup table, status column included |
| Technique cards | A job exercises that technique | Unbounded |
| Raw specimens | Never by a drafting job | Unbounded |

- **The inventory is the state.** Its status column shows what is filled and
  what is next, so resuming after a gap needs no separate progress file.
- **A request to capture a new situation is an inventory row, an exercise and a
  distillation** — a new card, never a change to the core.

## Mixed registers

- **Tag every captured fact with the register or genre it came from, and never
  blend across tags.** A habit true of one register is not automatically true
  of another.
- **Take only abstract method facts from a corpus that is not a clean sample of
  the person's own voice** — a deliberate pastiche, a co-written piece,
  in-world prose. Its concrete language is not theirs to quote as a specimen.
