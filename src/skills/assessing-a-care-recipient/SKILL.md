---
name: assessing-a-care-recipient
description: Writes the profile a care plan is built on for one family member - what she needs help with, what she lives on and from which program, where she lives and what keeps her there, who may decide for her, and what she wants - each fact with where it came from. Use when a family member's care is first taken up, and again when her health, income, housing or wishes change.
license: MIT
compatibility: Needs python3 to resolve the notebook folder and to write the board.
metadata:
  bristol.kind: playbook
  bristol.maintainer: care_manager
  bristol.scripts: src/tools/config_tools/notebook.py src/tools/ticket_tools/ticket_write.py
  bristol.subtitle: Assess a family member's care
---
# assessing-a-care-recipient

Input: one person the user names, and what he and the people around her can
tell. Operation: the procedure below. Output: one profile document for that
person, and a card for every fact the profile needs and nobody present knows.

An Aging Life Care Manager opens every engagement with this assessment, and
every later answer - which housing, which benefit, which move - is read off it.
A plan built before the profile stands is built on guesses about the person.

## What the profile records

Seven sections, in this order.

- **Who she is** - name, age, the state, county and city she lives in, who in
  the family is closest to her day to day, and the languages she reads.
- **What she wants** - where she wants to live, what she will and will not
  accept, in her own words where anyone has them. Her wishes are a section of
  the profile, never a footnote to the family's.
- **What she needs help with** - each activity of daily living (bathing,
  dressing, eating, toileting, moving from bed to chair, continence) and each
  instrumental one (medication, meals, money, transport, the phone, housework),
  marked independent, needs some help or needs full help, with who said so.
  Diagnoses only as the person or her doctor gives them.
- **What she lives on** - each income source by program (Social Security
  retirement, SSDI, SSI, a state supplement, a pension, wages), the monthly
  figure, and the document it was read from. Assets by kind and rough size,
  because a means-tested program counts them.
- **Her coverage** - Medicare parts she has and any plan by name, Medicaid and the
  state that pays it, a Medicare Savings Program, a drug plan, anything private.
- **Where she lives and what keeps her there** - the kind of housing, and for
  subsidized housing which kind: a voucher she has (tenant-based), a subsidy
  attached to the building (project-based, public housing, an elderly-housing
  building), or a reduced rent tied to her income. Which kind it is decides
  whether the help can move with her.
- **Who may decide** - a power of attorney, a health-care proxy, a
  representative payee, a guardian, each with who has it and in which state
  it was made; or that none exists.

## How a fact enters it

- **Every figure carries its source** - the award letter, the lease, the
  statement, or the person who said it and when. A figure from memory is
  marked as one.
- **Write an unknown as a question**, with the person who could answer it.
  Each becomes a card for the user, worded as what to ask whom.
- **Take the level of care from the person and her doctors.** The profile
  records what was observed and by whom; a judgment about the care she needs is
  her physician's.

## Where it goes

- **One profile per person**, named for her, in her own folder under the
  notebook folder `family`, shaped by
  `src/skills/note-formatting/SKILL.md`. `python3
  src/tools/config_tools/notebook.py access care_manager` gives the notebook's
  root; create her folder at the moment of the write.
- **Her health, income and benefits notes and the scans of her documents sit in
  the same folder**, each scan named for the document it shows and linked from
  the note that names it.
- **The folder `agents.care_manager.key_data_paths` declares takes only data a
  desk query reads**, if any.
- **The profile states the person as she is.** What has been done for her lives
  on the board.

## Procedure

1. **Ask the user for the seven sections** in one message, saying which
   documents would answer each: an award letter, a lease, a Medicare card's plan
   name, a Medicaid notice, a power of attorney.
2. **Write what he gives** into the profile, each fact with its source.
3. **File a card for each unknown that blocks a plan**, assigned to the user,
   saying what to ask, of whom, and which decision waits on it.
4. **Read the profile back to him** in plain words and correct it in place.

## Failure modes

- **A housing subsidy recorded without its kind** -> every move plan built on
  it may be wrong, because a voucher can move and a building's subsidy cannot.
- **The family's wishes written as hers** -> §What the profile records, second
  section.

## Audit

**Whether a stranger could tell, from the profile alone, which of her benefits
end if she leaves her state.** If not, the coverage, income or housing section
is missing what decides it.
