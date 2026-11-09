---
name: working-a-benefit
description: Takes one public program a family member may use - Medicaid, SSI and its state supplement, a Medicare Savings Program, a housing subsidy, an assisted-living or home-care program - from "does she qualify" to the agency, the application, the test she has to pass, the residency rule, the waitlist and the lead time, each cited to the administering agency's own page, and says whether it follows her across a state line. Use when a benefit has to be worked out, when a move or a change in income reopens one, or when a renewal comes due.
license: MIT
compatibility: Runs where the agencies' own pages can be fetched; needs python3 to resolve the declared data folder and to write the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: care_manager
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/ticket_tools/ticket_write.py
  bristol.subtitle: Work out a benefit or program
---
# working-a-benefit

Input: one person's profile from `src/skills/assessing-a-care-recipient/SKILL.md`
and the place she lives or is moving to. Operation: the procedure below.
Output: a record for each program worked, in her benefits document, and a card
for every date and every question to be put to an office.

Applying, enrolling, signing and calling are the user's or the person's own
acts, and an eligibility rule written without the agency's page behind it is
the failure this skill exists against - `src/agent_identities/care_manager.md`
§2.2 owns both.

## Finding what applies

- **Start at the place's own front door** - the state's aging and disability
  resource center, its benefits screener, the county office for the aging - and
  run it on her profile. The federal Eldercare Locator finds the local one.
- **Then work by who pays**: federal (Social Security, Medicare, HUD), state
  (Medicaid, the SSI supplement, state housing and aging programs), county and
  city. One level's list is never the list.
- **Take eligibility from the agency's own text.** A program applies because
  the published test matches her profile; a benefits website's summary is a
  lead to the agency's page, never the rule.
- **Work programs together where one opens another.** Medicaid often opens an
  assisted-living or home-care program; SSI often opens Medicaid; a subsidy's
  rent often counts toward another program's income test.

## What one program records

Eleven fields. A program missing any of the first eight is not worked yet.

- **Name**, as the agency gives it.
- **Jurisdiction** - the state, and county or city where it is local.
- **Administering agency** - the office that decides, not the website that
  takes the form.
- **The test** - income, assets, age, level of care, citizenship, in the
  agency's own words, with figures dated the day read.
- **Residency rule** - what makes her a resident for this program, and whether
  any length of residence is required before she may apply or be placed on a
  list. `none published` where the agency states none.
- **Application** - the form's designation, how it is filed, and the documents
  it asks for.
- **Waitlist** - whether there is one, who keeps it, whether she may join it
  before she lives there, how a place is kept (yearly renewal, answering mail),
  and any published wait.
- **Lead time** - the agency's published processing time, or `none published`.
- **Portability** - what happens to it if she moves: follows her, is
  transferred, ends and must be applied for again, or ends with no equivalent.
- **Source** - the agency's own page, as a link.
- **Unresolved**, where a question stays open.

- **Write `none published` rather than an estimate**, and never write a
  figure, a rule or a form designation without its link.

## Moving across a state line

- **Sort every program she has into three**: follows her (federal cash
  benefits paid to the person, with an address change), transfers through a
  process (a tenant-based housing voucher's portability), and ends at the old
  state's line (Medicaid, a state supplement, a building's subsidy, state
  programs). Each sorting cites the program's own page.
- **For each that ends, record when it ends** - on the move, at the end of a
  month, at the old state's next review - and what the new state's equivalent
  is, with its residency rule. The gap between the two is the hazard.
- **Record how living with family changes a benefit** where the program counts
  household or support received, because a stay with the family before her own
  housing opens is the common bridge.

## Citing and what stays open

- **Cite the agency's own page**; an advocate's guide, a law firm's article and
  this system's notes are leads.
- **Date every figure in the sentence that states it.**
- **Record an open question with the fact that settles it and who answers it**
  - the agency's office, a SHIP counselor for Medicare, an elder-law attorney
  for asset transfers and planning - in the words to put to them.

## Where it goes

- **One benefits document per person**, beside her profile in the folder
  `agents.care_manager.key_data_paths` declares, containing programs and nothing
  about what has been done about them.
- **A date becomes a card** - a renewal, a recertification, a waitlist to
  confirm, a window that closes - `ticket_write.py add-task --assignee
  care_manager`, signed with the running agent's slug.
- **A question to an office becomes a card for the user**, saying whom to call,
  what to ask and which decision waits on it.

## Procedure

1. **Read her profile**, and ask for what the test needs and it lacks.
2. **Run the place's front door** on her profile and list what it returns.
3. **Work outward by who pays**, adding what the front door missed.
4. **Fill the eleven fields from each program's own page**, dropping one whose
   test she plainly fails, and recording the drop with its reason.
5. **Sort by portability** where a move is in view.
6. **Write the document**, then file a card for each date and each question.
7. **Read it back against three checks**: every figure has a link, every rule
   has its jurisdiction, every open question has who answers it.

## Failure modes

- **A residency rule assumed from another program** -> each program states its
  own, and a waitlist's rule differs from the benefit's.
- **"She can apply when she gets there" with no date her old coverage ends** ->
  §Moving across a state line; the gap was never measured.
- **An income limit with no date** -> limits change every year.

## Audit

**Whether the user could call the agency tomorrow with the form, the documents
and the one question that matters.**
