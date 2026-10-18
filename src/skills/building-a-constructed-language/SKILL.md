---
name: building-a-constructed-language
description: Builds a constructed language for a fictional world, or a piece of one - its sound, grammar, roots and words - out of what the world's notes say about its speakers' land, life and neighbours, borrowing from the project's other languages where their speakers meet, and checks that it sounds unlike every other. Use when a language's sound, grammar, root stock or vocabulary is designed, extended or revised.
license: MIT
compatibility: Runs where the project's notes are reachable; needs python3 for the sound check.
metadata:
  bristol.kind: playbook
  bristol.maintainer: writers_room
  bristol.scripts: src/tools/wiki_tools/sound_check.py
  bristol.subtitle: Build a constructed language from its world
---
# building-a-constructed-language

Input: a language of a fictional world, or a piece of one — its sound, a
grammatical category, a field of roots, a set of words. Operation: the rules
below. Output: the piece written into the language's notes, sounding like that
language alone.

Who decides what, what to recommend and how a design is written down are
`src/skills/designing-with-the-author/SKILL.md`, and hold here. The rules below
are the language's own.

## Who decides

- **A linguistic choice is the session's own** — a sound change, an affix's
  shape, which of several grammatical solutions a language of the type uses,
  how a word is coined. Make it, and report it with its reason.
- **A fact about the world the language needs is the author's** — what grows
  where its speakers live, whom they trade with, what they believe. Where the
  notes do not give it, ask him in plain words about the world, never about
  linguistics.

## Build it out of the world

- **Read what the notes say about the speakers before coining a field** —
  their land and its ecology, their work, their history, their gods, and the
  peoples they meet. A field of roots names what that world holds.
- **Give the world's own things words of their own**, and leave a thing the
  speakers never meet without one: a cave people has words for kinds of stone
  and darkness, and a borrowed word, or none, for the open sea.
- **Let the language's history follow the world's history** — a conquest, a
  migration, a split between two peoples who once spoke as one shows in its
  sound changes and its layers of words.

## Borrow where speakers meet

- **Borrow a word from another language of the same project where its
  speakers meet the lender's** — in trade, rule, worship, marriage or war —
  and give the reason beside it.
- **Reshape a borrowed word to the borrower's sounds**, as the borrower's
  speakers would hear and say it, and keep the lender's form beside it in the
  borrower's notes.
- **Borrow most where contact is closest**, and in the fields that contact
  touches: a port's trade words, a conqueror's law words, a missionary's
  religious words.
- **Keep the borrower's loans when the lender's sound is rebuilt** by giving
  them a conservative source — a dialect or an older stage of the lender that
  keeps the old sounds — rather than rewriting the borrower. one language's
  Port loans come from the speech of the trade ports.

## Coin in the language's own forms

- **Coin every root and grammatical word in the language's own sounds and
  forms.** A core Earth language the design draws on lends it features — a
  case system, an aspect split, a word order — and none of its words.
- **Reshape a coined word that lands near an Earth word of the same meaning**
  until it is no longer recognisable as that word.
- **Make each language sound unlike every other in the project** — its own
  syllable shape, its own consonants that close a syllable or cluster, its own
  signature sounds, vowels and rhythm, its own look on the page.

## Check the sound

`designing-with-the-author` §Checking a name's sound runs on every name the
language coins. A language's sound is checked the same way, as a sample.

- **Run `python3 src/tools/wiki_tools/sound_check.py words <sample> --language
  <the language>` on ten or more words for each proposed sound**, and the name
  check on each name the sample coins.
- **Check a name in a language whose sound is being rebuilt against its new
  forms**: `sound_check.py name <name> --language <the language> --home-words
  <the new forms>`. Read from its notes, the language is its old sound.
- **Read the profiles beside the score** — the consonants that close a word,
  the signature letters, the commonest syllables, the word lengths and the
  sample — and set ten names of the language beside ten of its nearest. The
  score is a mean of six parts and can call apart two languages the ear hears
  as near.
- **Replace a sound the check reports too near before it reaches the author**,
  and give each sound offered its nearest language and score.
- **Add a new language's notes to the `languages` of the `sound_check` key** of
  the config entry of the agent holding the languages, in the session that
  writes its first words.

## Write it down

- **State a language's sound targets technically in a card that directs work
  on it** — the inventory, the consonants that may close a word, the
  vowel-final and closed shares, the stress.
- **State in a note the rule a choice produced, never the world reason behind
  it.** A seafaring language's sound heard across a deck is written as its sounds, never as
  the sailors' "aye".

## Measure completeness

- **Measure vocabulary against a published meaning list**, such as the World
  Loanword Database's, and grammar against a published questionnaire, such as
  Comrie and Smith's. Test sentences prove a design and set none of its scope.

## Failure modes

- **A field of roots coined with no reading of the speakers' world** → §Build
  it out of the world.
- **A word taken whole from an Earth language** → §Coin in the language's own
  forms.
- **Two languages whose speakers trade for centuries with no word between
  them** → §Borrow where speakers meet.

## Audit

**Whether every word in the piece names something the world notes give its
speakers, and the sound check reports the language apart from every other.**
