---
name: working-a-licence
description: Takes the licences and permits a business triggers from "does this apply to me" to the issuing authority, the form, the fee, the lead time and what has to be true first, each one cited to the authority's own page. Use when a business needs to know what it has to be licensed for, when one requirement has to be worked as far as the point of filing, or when a new activity, a new address or a renewal reopens the question.
license: MIT
compatibility: Runs where the issuing authorities' own pages can be fetched; needs python3 to resolve where the research is filed and to write the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: business_advisor
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/ticket_tools/ticket_write.py
  bristol.subtitle: Work out a licence or permit
---
# working-a-licence

Input: a business described by what it does, where it does it and who it
employs. Operation: the procedure below. Output: one research document holding
every requirement that combination triggers, and one card for every requirement
carrying a date.

Filing, submitting, signing, paying and registering are the user's own acts, and
a number written without the issuing authority's page behind it is the failure
this skill exists to prevent — `src/agent_identities/business_advisor.md` §2.2
owns both.

## What the input has to name

- **Activities** — everything the business does for money, and everything it
  does on the premises that it does not charge for.
- **Place** — down to the address wherever an answer can turn on the building,
  the zoning lot or the street.
- **People** — how many are employed, whether any are minors, and whether
  anyone works there who is not an employee.
- **Ask for a missing one rather than working without it.** Each of the three
  changes the list, so a list built on two of them is a list that has to be
  built again.
- **Work the exact combination, never one activity at a time.** Two activities
  in one room trigger requirements that neither triggers alone, and the
  eligibility question the combination raises is usually the hardest one in the
  set.
- **Re-run the whole list when any of the three changes.** An address chosen
  after the first pass is a new input, not an amendment.

## Finding what applies

- **Start at the jurisdiction's own trigger tool where one exists** — a city's
  step-by-step wizard, a state's licence lookup — and run it on the whole
  combination.
- **Then work outward by regulator**, one level of government at a time:
  federal, state, county, city. A single level's list is never the list.
- **Take the trigger from the authority's own eligibility text.** A requirement
  applies because the text the authority publishes matches the business as
  described, and nothing else makes one apply.
- **Read the statute or rule where the authority's page does not say whether it
  applies.** The page is the first source and the law behind it the second, and
  a question neither answers is unresolved rather than decided.
- **Treat a repealed licence as a live question.** Rules outlive the licence
  that carried them, and a search that returns no licence is not a finding that
  nothing is required.
- **Name the requirements an activity exempts as well as those it triggers**,
  where an authority publishes an exemption the business appears to meet. An
  exemption is a record with a citation like any other requirement.

## What one requirement records

Ten fields. A requirement missing any of the first seven is not worked yet.

- **Name**, as the authority itself names it.
- **Jurisdiction**, stated in the record rather than inferred from the document
  it sits in.
- **Issuing authority** — the office that grants it, not the portal it is
  filed through.
- **Trigger** — the authority's own eligibility words, quoted or closely
  paraphrased.
- **Form and where it is filed** — the form's own designation, and the system
  or address that receives it.
- **Fee**, with the date the fee page was read beside it.
- **Lead time** — the authority's published processing time, or `none
  published`.
- **Prerequisites** — what has to be true, held or finished before the
  application may be filed.
- **Source** — the authority's own page, as a link.
- **Unresolved**, where the record leaves a question open.

- **Write `none published` rather than an estimate.** An authority publishing
  no processing time is a fact about the requirement and belongs in the record;
  a guess in that field is read later as something an authority said.
- **Never write a fee, a deadline, a threshold, an eligibility rule or a form
  designation without its link.** Leave the field empty and record what would
  fill it.

## Citing

- **Cite the authority's own page.** A summary, a law firm's article, an
  aggregator, a trade association and this system's own notes are each evidence
  that somebody said it, and none of them is the requirement.
- **Date every fee, threshold and deadline in the sentence that states it**, not
  in the document's frontmatter. Fees change on a schedule the document does
  not.
- **Name the jurisdiction at the point the requirement is stated.** A rule that
  holds in one city is false in the next one over.
- **Record both readings where the authority's page and the statute disagree**,
  and mark the disagreement unresolved.

## What stays unresolved

- **Record the question, the fact that would settle it, and who answers it.**
  All three, or the question is a shrug.
- **Never resolve a genuinely open question to the likelier reading.** The
  likelier reading is what the buildout is priced against and what the
  application is refused for.
- **Name the office to ask, or the kind of licensed professional who settles
  it**, and write the question in the words it should be put in.
- **Keep the record.** An unresolved requirement is still a requirement, with
  every field it has; unresolved is a value in the record rather than a reason
  to leave it out.

## The sequence and the long pole

- **Order the requirements by prerequisite**, so each one sits after everything
  that has to be true before it can be filed.
- **Count everything that happens before the form may be filed** in a
  requirement's path — a notice period, a publication run, a board or committee
  that meets monthly, an inspection, a lease, a buildout.
- **Name the long pole**: the requirement whose path from today to in-hand is
  longest, and what it blocks.
- **Name the long pole even where its processing time is unpublished**, and say
  the duration is unavailable rather than filling it. A requirement nobody can
  time is the one most likely to set the opening date.
- **Say which requirements run in parallel with it**, because that is what the
  ordering is for.

## Where the output goes

- **A note this stage contributes to the business's packet takes the shape
  `src/skills/road-to-opening/SKILL.md` §The packet shape defines**, which this
  skill restates no part of.
- **The research is one document per business**, named for the business, in the
  folder `agents.business_advisor.key_data_paths` declares, resolved with
  `data_paths.ensure_dir()` at the moment of the write.
- **The document holds requirements and nothing about what has been done about
  them** — `src/app.md` §What a file may say.
- **A requirement carrying a date becomes a card** — a deadline, a renewal, a
  window that opens before filing, a certificate due within so many days —
  `ticket_write.py add-task --assignee business_advisor`, signed with the
  running agent's slug.
- **A question that has to be put to an office or a professional becomes a
  card**, because the asking is an act the user takes on a day.
- **The card carries the date, the link and what it blocks; the document carries
  the research.** Neither restates the other, and the document cites no card.

## Procedure

1. **Take the three inputs**, and ask for whichever is missing.
2. **Run the jurisdiction's own trigger tool** on the combination, and list what
   it returns.
3. **Work outward by regulator** through the levels of government, adding what
   the trigger tool does not cover.
4. **Open each candidate's own page** and fill the ten fields from it, dropping
   a candidate whose eligibility text does not match the business.
5. **Put the eligibility question the combination raises to the statute**, and
   record it unresolved where the statute does not settle it.
6. **Order by prerequisite and name the long pole** and what it blocks.
7. **Write the document**, then file a card for every date and every question to
   be asked.
8. **Read the document back against three checks**, fixing what fails: every
   number carries a link, every requirement carries its jurisdiction, and every
   open question carries who answers it.

## Failure modes

- **A fee with no link** → step 4 was filled from memory, and the whole skill
  has failed at that line.
- **A list built from one level of government** → step 3 stopped at the city, or
  at the state.
- **Each activity researched alone** → §What the input has to name, and the
  eligibility question the combination raises was never asked.
- **An open question written as a conclusion** → §What stays unresolved; the
  likelier reading was taken because it made the document finishable.
- **A lead time that counts only the authority's processing** → step 6 left out
  the month before filing, which is where the calendar is usually lost.
- **A renewal date recorded in the document alone** → it is a card, and a date
  in a document is a date nobody is reminded of.
- **A search that returned no licence read as nothing being required** → the
  licence was repealed and its rules were not.

## Audit

**Whether the user can walk into the first appointment with the form, the fee
and what the office will ask him for.** A document that tells him a licence
exists has answered the question he did not need answered.
