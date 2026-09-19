---
name: checking-a-wiki-for-disagreements
description: Finds where a body of notes disagrees with itself — one name spelled two ways, one fact stated two ways — and files each disagreement where the user will meet it. Use when a wiki, a story bible or a documentation set has grown past what one session can hold, and when a disagreement in one is suspected or reported.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3 and read access to the notes.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/wiki_tools/name_variants.py src/tools/ticket_tools/ticket_write.py
---

# checking-a-wiki-for-disagreements

Input: a folder of notes about one subject. Operation: the machine pass, then
the reading pass. Output: one card per disagreement, naming every note that
holds it.

Catching a disagreement is worth as much as fixing one, and it does not depend
on being allowed to fix anything: a folder an agent may only read is checked the
same way, and the card is the whole of the output. How a body of notes is read
and reconciled at large is `src/tools/wiki_tools/wiki_conventions.md`; this owns
finding where it contradicts itself.

## The machine pass

- **Run `python3 src/tools/wiki_tools/name_variants.py <folder>`.** It finds one
  coined name spelled more than one way, with how often each spelling is used
  and which notes hold it, and finds nothing else.
- **Judge every group it raises; it raises candidates rather than verdicts.**
  Three answers are usual: a spelling used once beside one used often is a typo;
  two spellings both used widely are a decision the user has to make; and two
  names that merely resemble each other are two names, which is a finding to
  drop rather than file.
- **A suffix that marks a form is not a disagreement** where the subject is a
  constructed language and the notes say so. Read the note that defines the
  form before filing anything about it.

## The reading pass

What a machine cannot see is the same fact stated two ways. Bound it, or it
becomes a re-reading of the whole wiki:

1. **Take the subjects the machine pass raised**, plus any the user named.
2. **For each, read every note that mentions it** — one `grep -rl` over the
   folder gives the list — and write down the claim each note makes.
3. **Keep only the pairs that cannot both be true.** A note saying less than
   another is not a disagreement; a note saying something else is.
4. **Stop at the subjects in hand.** A wiki-wide reading is its own card, sized
   as such.

## Where a finding goes

- **One card per disagreement**, assigned to the agent that owns those notes,
  written as a fix: what is expected, and what the notes say instead.
- **Name every note holding each side**, by path, with how often each spelling
  or claim appears. The card is what the user meets; a disagreement spoken only
  in a session is not recorded.
- **Never file the fix as done by finding it.** What a card may then do about it
  is that agent's own write authority — `src/templates/identity_template.md`
  §Data locations and the agent's charter — and a folder it may not write gets a
  proposal in the card rather than an edit.
- **File nothing for a group you dropped.** A candidate the reading pass
  explains is not a finding, and a board of dismissed candidates teaches the
  user to skim it.

## Failure modes

- **A card naming a spelling but not its notes** → the user cannot see which is
  right without a search of their own.
- **Every group the tool raised filed as a card** → §The machine pass: three of
  the four answers are not findings.
- **A finding held until it can be fixed** → catching is the output; the fix is
  a separate authority and may never come.
