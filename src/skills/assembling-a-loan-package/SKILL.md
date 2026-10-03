---
name: assembling-a-loan-package
description: Builds a small-business loan package in a fixed order — the document list the programme actually asks for, the records read on the machine they sit on, the plan, projections whose every assumption is written beside them, and a handover listing what is missing. Use when a loan, a line of credit or a grant application is being prepared, or when a lender has asked for a file.
license: MIT
compatibility: Runs where the lender's or agency's own pages can be fetched and the user's records are readable in place; needs python3 to resolve where the package is filed and to write the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: business_advisor
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/ticket_tools/ticket_write.py
  bristol.subtitle: Build a small-business loan package
---
# assembling-a-loan-package

Input: one lender or loan programme, the business it is for, and the user's own
records. Operation: the procedure below. Output: one package — the document
list, the plan, the projections with their assumptions, and a handover — in the
business's own folder.

Signing, submitting and paying are the user's own acts, and his financial
documents never leave the machine they are on —
`src/agent_identities/business_advisor.md` §2.2 owns both.

## Gather, then write

- **Assemble the documents before drafting a sentence of the plan.** The plan is
  written out of the records; a plan written first becomes a set of figures the
  records then have to be argued into.
- **Make every figure in the package traceable to one of five things** — a
  written quote, a signed lease or letter of intent, a tax return, a published
  rate or fee, or an assumption stated as one. A sixth kind of figure does not
  exist.
- **Never let two documents in the package disagree.** The same rent, the same
  injection, the same headcount, in the projections and on every form.

## The document list

- **Take the list from the lender's or the agency's own page**, and cite that
  page beside each item.
- **Record "the lender decides" as the answer where the programme says so**, and
  name what it turns on — the size of the loan, the processing method, the
  lender's own policy. An invented list is worse than a short one, because it is
  read as authority.
- **Separate the forms the programme supplies from what the applicant
  assembles.** The first set is downloadable and its version date is checkable;
  the second set exists only if someone gathers it.
- **Name each form by its designation and version date**, both read from the
  issuer's own page on the day.
- **Say which thresholds the programme publishes and which it does not.** A
  credit score, an equity injection and a collateral formula that an agency
  does not publish are set by each lender, and writing a number for them invents
  the underwriting standard.

## Reading the user's records

- **Read them where they are.** Nothing is uploaded, emailed, attached or copied
  to another machine, whoever is asking.
- **Say what was read and what was derived from it**, file by file and figure by
  figure, in the package itself.
- **Ask for a record rather than reconstructing it.** A tax return, a lease and
  an equipment quote each exist or do not, and a derived stand-in for one is the
  figure the underwriter finds.
- **Never write a figure the user must certify as though it were verified.** A
  personal financial statement is his assertion, and the package carries it as
  his.

## The plan

- **Take the section list from the programme's own guide**, and follow it in the
  order the guide gives.
- **Write the funding request and the projections to be read twice**, because
  they are the two sections that carry the decision.
- **State the strongest objection to the business in the plan itself**, and
  answer it in a sentence a stranger would accept. An objection a reader finds
  for himself is worth less to him than the same objection answered.
- **Say which part of the business carries the fixed costs and which carries the
  margin**, where the concept has more than one part.

## Projections and their assumptions

- **Every assumption is a number, a unit, and where it came from.** "Rent
  $6,500/month, signed lease" and "footfall 40 covers/night, assumed from
  nothing" are both complete; a figure with no third part is not an assumption
  but a guess wearing one's clothes.
- **Put the assumptions in one table beside the projection**, never inside cell
  formulas or a footnote.
- **Make the projection recomputable**: someone holding the assumption table and
  nothing else can rebuild every line of it. A line that cannot be rebuilt that
  way is removed or given the assumption it was hiding.
- **Run month by month through the first year, then by year.** An annual average
  hides the months before opening, which is where a startup's cash actually
  fails.
- **Carry the pre-revenue months at full cost** — licensing, construction, rent,
  insurance and payroll that run before the doors open.
- **Show the injection as its own schedule**: how much, from where, and on what
  date it arrives.
- **Name the two or three assumptions the projection turns on**, and what a
  plausible move in each does to the result. An underwriter finds them in
  minutes; a package that has already found them is answering rather than
  defending.
- **Never round an assumption into the projection.** Round in the presentation
  if at all, and keep the assumption at the figure its source gives.

## The handover

Four things, and a handover missing one is not finished.

- **What is in the package**, item by item, against the document list.
- **What is missing**, and which item on the list each gap belongs to.
- **What only the user can supply** — a signature, a certification, a personal
  statement, a document held by his accountant or his bank.
- **What the lender is most likely to push back on**, stated as the underwriter
  would name it, with where in the package the answer sits.

## Where the output goes

- **A note this stage contributes to the business's packet takes the shape
  `src/skills/road-to-opening/SKILL.md` §The packet shape defines**, which this
  skill restates no part of.
- **One folder per application**, named for the lender or the programme, in the
  folder `agents.business_advisor.key_data_paths` declares, resolved with
  `data_paths.ensure_dir()` at the moment of the write.
- **The package holds the plan, the projections and the handover**, and nothing
  about how far along the application is — `src/app.md` §What a file may say.
- **A date becomes a card** — a submission deadline, a quote that expires, a
  rate lock, a form whose version is superseded — `ticket_write.py add-task
  --assignee business_advisor`, signed with the running agent's slug.
- **A document only the user can supply becomes a card**, because it is an act
  on a day rather than a gap in a file.

## Procedure

1. **Name the lender or programme**, and read its own page for eligibility and
   for what it asks the applicant to bring.
2. **Build the document list** from that page, marking each item as
   programme-supplied or applicant-assembled.
3. **Inventory what the user already has**, reading in place, and record what
   was read and what each figure was derived from.
4. **Write the assumption table first**, from the quotes, leases, returns and
   rates in hand, marking every figure that rests on nothing but judgement.
5. **Build the projections from that table**, monthly for the first year.
6. **Write the plan** in the programme's own section order, with the funding
   request reconciled line by line to the projections.
7. **Write the handover**, and file a card for every date and every document
   only the user can supply.
8. **Read the package back against three checks**, fixing what fails: every
   figure traces to one of the five sources, no two documents disagree, and the
   projection rebuilds from the assumption table alone.

## Failure modes

- **A projection whose assumptions are not written down** → step 4 was skipped,
  and the package cannot be defended in the room.
- **A document list from a template** → step 2 took the list from experience
  rather than from the programme's page.
- **A credit score or equity minimum stated as the programme's** → §The document
  list; the agency publishes neither.
- **The plan written before the records were gathered** → §Gather, then write,
  and the rent in the projections will not match the lease.
- **An averaged first year** → the pre-revenue months were smoothed away, and
  the months the loan exists to cover are the ones no longer visible.
- **The user's statements copied somewhere to be processed** → the one thing
  §Reading the user's records forbids outright.
- **A handover that says the package is complete** → it lists no gaps because
  nobody looked for them.

## Audit

**Whether an underwriter could rebuild the projections from the package alone,
and reach the same numbers.** A package he cannot rebuild is one he has to take
on trust, and he will not.
