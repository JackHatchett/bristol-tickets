---
name: splitting-an-explanation
description: Moves a big idea out of a document into a note of its own, and points every document that uses it at that one note. Use when explaining something inside a document would take the document over.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# splitting-an-explanation

Input: a document that rests on a concept its reader may not have. Operation:
the procedure below. Output: a document that reads whole on its own, and a note
that explains one concept.

Load it where the concept needs more explanation than the document can carry
without becoming a document about that concept instead. A term one plain
sentence settles is defined in place, per `src/app.md` Phase 4, and nothing here
fires.

## Procedure

1. **Keep in the document whatever the sentence needs to be followed.** What
   moves out is depth — where the concept came from, what it rules out, how it
   behaves at its edges. A definition the reader needs to parse the line they
   are on is not depth.
2. **Give the concept its own note and put nothing else in it.** One note, one
   concept, named for the concept.
3. **Link that one note from every document that uses the concept.** Four
   documents reading one note is the point; a second copy beside the fourth is
   the failure.
4. **Read the document through with every link unfollowed.** It has to make
   sense that way. Where it does not, a definition left with the depth — bring
   that sentence back.
5. **Write the note for a person**, per `src/app.md` §What a file may say. No
   note here is written only for a machine.

## Failure modes

- **The reader opens three notes to read one plan** → step 1 moved definitions
  rather than depth.
- **A note explains two concepts** → it is two notes; split it and relink both.
- **The same explanation stands in two documents** → step 3 was skipped once.
- **A note has acquired a section on something adjacent** → step 2; the note is
  an explanation of one concept, not a place things collect.

## Audit

**Whether the document survives its links being unfollowable.** One that stops
making sense without them has had its content moved out, not its depth.
