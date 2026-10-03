---
name: working-a-contact
description: Records a person and what is outstanding with them — when a contact row is created, when an ask is opened and closed, and where the prose about them goes instead. Use when a person comes up in a session, when an outreach is sent or answered, or when a due contact is worked.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3 and a personal.db folder grant.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/personal_db/personal_write.py src/tools/personal_db/contacts_due.py
  bristol.subtitle: Record a person and what they're owed
---

# working-a-contact

Input: a person, and something outstanding with them. Operation: the rules
below. Output: one contact row, the asks it carries, and the prose about them in
the document that owns it.

The database holds dates and state; it holds no description of anybody. What a
person is like, what they said, what they do — that is prose, and
§Where the prose goes says where. The mechanism is
`src/tools/personal_db/README.md`; this owns when each write happens.

## The contact row

- **Create one the first time a person is somebody the user owes a move, or
  owes him one.** Meeting a name in a document is not that: a row exists
  because something is outstanding or a cadence is wanted, never to have a
  record of a person.
- **Search before creating** — `personal_write.py find-contact --name <part>`,
  which matches aliases as well as names. A different spelling of one person is
  what makes a second row, and two rows for one person is the failure this
  domain exists to avoid.
- **Put every other spelling in `--aliases`** the moment you meet it: a
  nickname, a maiden name, a middle initial, the name their email signs off
  with.
- **Give a cadence only where one is real** — a person the user means to stay in
  touch with on some rhythm. No cadence is the ordinary case, and an invented
  one makes a due list nobody believes.
- **Move `last_contact_on` whenever an exchange happens**, in either direction,
  whether or not an ask moved with it.

## The ask

- **Open one for each outstanding thing, not one per person.** Two roles at one
  company through one friend are two asks: they are answered separately and they
  go stale separately.
- **Say who the next move waits on** — `--direction them` where the user is
  waiting, `--direction us` where it is his to make. That is what turns the list
  into something he can act on rather than read.
- **Give `--due-on` a date only where one is real** — a posting that closes, a
  renewal, a promise made for a day. A date invented to force a reminder makes
  every date on the board suspect.
- **Close it when the thing it records has happened, or has stopped being
  wanted** — `close-ask --id N`, `--status dropped` for the second. Closing
  moves the contact's last contact to that day unless told otherwise.
- **Never close an ask because time passed.** An ask nobody answered is still
  open; what changes is whether it is still wanted.

## What a due item is

- **`contacts_due.py` is the read**, and the daily capture it writes lands in
  the notebook's capture inbox.
- **A due item is a prompt to the user, never a task for an agent.** Calling a
  friend is his. An agent working a due item drafts, gathers or reminds; it does
  not reach the person.
- **What the agent may do with one is take the next move that is the system's**
  — draft the message for him to send, pull up what he needs before he writes,
  or record what came back.

## Where the prose goes

- **A document about a person is the document's**, never a column here. A career
  dossier, a client profile, a page in the notebook: the fact goes to whichever
  owns it, and the contact row keeps the dates.
- **A fact whose home is a folder this agent may not write** goes to the user as
  a summary — `src/skills/notebook-proposal/SKILL.md`, which owns that route.
- **Link rather than copy** — `add-link --contact N --kind application
  --target-id M`, or `--target-path` for a file. A person is attached to many
  documents over time, and copying an identifier onto the contact row is how
  that stops being true.

## Failure modes

- **A second row for one person** → §The contact row: search first, and aliases.
- **One ask carrying two things** → §The ask: they close separately.
- **A description of a person in `notes`** → §Where the prose goes. `notes`
  holds what a reader of the due list needs, and nothing that belongs in a
  document.
- **A due item worked as though the agent could answer it** → §What a due item
  is.
