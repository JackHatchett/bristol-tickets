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

The database records dates and state; it contains no description of anybody. What a
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
- **Mark a friend with `--friend`**, and record `--reference-status` once a
  reference is in view. Email and LinkedIn are recorded when they turn up and
  never asked for.

## The introduction

- **Record one with `add-introduction`** — one application row, the friend as
  introducer and the person reached as target, the same contact for both when
  the friend refers the user at their own company.
- **Move its stage as it moves** — `update-application --intro-stage`. The
  stage alone says whose move it is, so an introduction needs no ask to carry
  the direction.

## Pacing introduction asks

A friend asked well and not too often stays a friend who helps. Every rule here
is applied by the session drafting the ask, so the user never has to remember
it.

- **One open introduction ask per friend at a time.** A second waits until the
  first resolves.
- **Make every ask specific**: a named person, a named role, a blurb the friend
  can forward as it stands, with the resume and the posting's link attached.
  "Let me know if you hear of anything" is not an ask.
- **Follow up once, after 7 to 10 days of silence.** Silence after that means
  the ask is no longer wanted: drop it quietly (`--intro-stage dropped`) and
  never repeat it.
- **Let a friend rest 3 weeks after an ask resolves** before the next one,
  unless the friend has offered more. `contacts_due.py` and the career
  dashboard show the day the next ask is fine while the rest runs, and nothing
  outside it.
- **A referral at the friend's own company starts no rest**, because it costs
  them little.
- **Never put a reference request in the same message as an introduction
  ask.**
- **Reconnect first with a dormant friend** — no exchange in roughly a year.
  The first touch carries no ask; the ask comes on the second.
- **Ask for the network map once per friend per search**, once they agree to
  help: which of these companies they know people at. Specific asks are then
  drawn from it and paced one at a time.
- **Close the loop on every resolved introduction.** The user tells the friend
  how it went and thanks them, and that exchange moves `last_contact_on`.

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
- **Close nothing by hand because time passed.** Silence is closed by the daily
  run of `close_stale.py`, which the user chose to be automatic: an application
  or introduction silent past its window becomes No response, and the open asks
  about it close as dropped. An introduction ask whose one follow-up went
  unanswered has stopped being wanted, under §Pacing introduction asks.
- **Reopen anything the user says is still alive**, however he puts it —
  "Optimum is still alive" is enough. `find-company` gives the row, and
  `personal_write.py reopen --id N` brings it back with a fresh window from
  today; pass `--status` where it stood further on than Applied.

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
  contains what a reader of the due list needs, and nothing that belongs in a
  document.
- **A due item worked as though the agent could answer it** → §What a due item
  is.
