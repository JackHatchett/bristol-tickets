---
name: cover-letter
description: Writes a complete cover letter for one job, from company research through drafting to the finished file. Use once a posting has been judged worth applying to and the letter is the next thing.
license: MIT
compatibility: Needs python3 and the repository's document tools for the .docx output.
metadata:
  bristol.kind: playbook
  bristol.maintainer: career_coach
  bristol.scripts: src/tools/career_coach/cl_lint.py
---
# cover-letter

The user's answer to `src/skills/jd-evaluation/SKILL.md`'s Step 3 context
question is full authorization. Research, approach selection, drafting, linting
and packing happen in the same turn, with no further prompt-back.

## Precedence

- **A convention of the form beats a voice guideline.** Voice operates inside
  the genre's rules and never overrides one; where the two appear to conflict,
  the voice guideline is what needs correcting.
- **The enforceable phrase list is the instance's own blacklist file**, in the
  user's career data root. This skill holds the rules that shape a letter,
  not the wordings that fail it.
- **The account-level banned phrases and constructs bind here too**, and are not
  restated in this file.

## Rules of the letter

**Truth**

- **Never invent experience, metrics, titles or outcomes**, and never stretch a
  real fact onto the wrong role. Verify every claim against the resume and
  context files before it ships.
- **Never address the letter to the wrong company.** Identity was confirmed at
  triage; inherit it, with the cold-letter exception in Step 0.
- **Never quote or reference a research source in the letter** — app-store
  complaints, review sites, anything gathered in Step 0. Research selects which
  story to tell; it never appears on the page.

**Length and shape**

- **One page**, never two.
- **Never summarize the resume.** The letter carries what a resume structurally
  cannot: judgment, reasoning, the story behind a line. No resume sentence
  appears verbatim.
- **Never write a sentence that could appear unchanged in another applicant's
  letter.**
- **Never let the letter sound generic, templated or AI-generated.**

**Address and stance**

- **Write to a reader.** Name the company early and use the second person; a
  letter with no "you" in it is a personal essay.
- **Name the role by its actual posted title, once.**
- **Never use a generic salutation** ("Dear Hiring Team," "To Whom It May
  Concern"). Default to no salutation and open at paragraph 1; a named contact
  is addressed by name.
- **Never open in media res.** Dropping the reader into a scene is a fiction
  move and reads as aggressive here.
- **Never frame anything as a problem** — not the company's, not the industry's,
  not one the role exists to solve, and never with the user as the answer. The
  word "problem" does not appear.
- **Never explain the company's own product, market or users back to it.**
- **Never flatter the company.** "Industry leader" and its relatives are
  invisible to the reader at best.
- **Never mention the application process**: no "as you can see from my attached
  resume," no "per the job posting," no reciting the requirements list back.

**Claims**

- **Concrete over abstract** — named systems, named decisions, real outcomes.
- **No superlatives attached to the user's own work.**
- **Never offer enthusiasm as a qualification.**
- **Use a number only where it is real and load-bearing.** A letter of
  statistics reads as a resume with worse formatting.
- **Past work in past tense**, consistently.

**Weakness**

- **Never open a paragraph with a weakness.** The negative goes in a subordinate
  clause with the strength in the main clause: "Although I have never done X, I
  did Y for four years."
- **Name a gap once, honestly, and never elaborate past the clause that concedes
  it.** Never hope a gap past the reader, and never apologize or pre-empt a
  rejection on their behalf.

**Close**

- **The closing is a courtesy formality, not a pitch.** Express interest in
  talking and hope that it is a good fit; that is the whole genre.
- **Never presume a process** — no imagined conversation to be joined, no
  assumed next step, no proposed date, no "I will follow up on Tuesday."
- **Never raise salary, competing offers, timelines or other applications**
  unless the posting asks.
- **Sign-off, then the name, then nothing.**

**Punctuation**

- **No en-dashes, em-dashes, double hyphens or repetitive punctuation** anywhere
  in the letter or its delivery notes. A single hyphen inside a compound term is
  fine ("full-time"). Enforce this while drafting, not only at lint time.
- **No exclamation points.**

## Step 0: Research

**Identity.** Reuse the company confirmed in `src/skills/jd-evaluation/SKILL.md`'s Step 0; do not
re-derive it. **Run the identity check now when the user pasted a JD and asked
for a letter with no triage this session.** Where the company name is shared
with a larger or more famous organization, confirm against a primary source by
matching JD fingerprints — verbatim benefit strings, size and funding-stage
language, product nouns, methodology tells. **Stop and ask when two candidates
stay plausible**; a wrong-company letter is worse than any voice flaw.

**Deep research.** Research the product and organization so the letter speaks to
what they actually build. Priority order: company site and product pages,
product or engineering blog, recent news with dates verified, the app and its
store reviews for a consumer product, culture-signal sites last. Keep it
proportional — one confirming pass plus one earned hook, not a company report.
**This agent does not browse the web**; hand the user the research prompt (see
§Research handoff) unless the session already has research to work from.

**Guardrails.** Use only specifics verifiable against a primary source. **Treat
review sites as a hypothesis generator rather than truth** — they skew negative.

**Internal fit read**, which drives emphasis and is never printed: which
high-weight JD keywords are PRESENT, CONTEXT-ONLY or a true gap per
`src/skills/jd-evaluation/SKILL.md`'s rubric; the strengths; the one honest gap a sharp
interviewer will exploit; and the single strongest narrative thread connecting
the user's background to this role.

**Seniority altitude.** For Senior and above, **at least one body paragraph
operates at portfolio altitude** — a roadmap tradeoff, a build-versus-buy call,
resource allocation across teams, a feature deliberately killed. Pull the one
altitude-appropriate proof point from the anecdotes and employment-history
context files; do not stack several, and do not invent one.

## Approach menu

**Choose silently.** Never recommend an approach or ask the user to pick one.
Refer to the chosen one by descriptive name in the delivery note, never a code.

- **User experience is my passion** — the user is a real user of this product or
  a close competitor, and research confirms plausible use. Opens from honest
  personal use, arrives at wanting to own the UX. Positive only, never a product
  audit.
- **Personal history coincidence** — something in the user's real history maps
  honestly to the company's mission or users. Only where the connection is real;
  a forced one is worse than none.
- **Specific technical observation** — a genuine, specific observation about a
  problem the company is solving, matched to a named experience from the context
  files. "I find this space fascinating" is not this approach.
- **Pivot toward meaning** — the user's industry history is the elephant in the
  room and naming it memorably beats hoping the reader overlooks it. Honest
  reckoning, then a specific reason this role would feel different. Best where
  the mission is itself the draw; which sectors those are lives in the user's
  context files.
- **Mixed** — combine approaches where there is a clear structural reason.

## Structure

**Read `data/*/career/foundation/cl_reference.md` before drafting.** That file
is the binding structural spec — word count, paragraph count, paragraph and
sentence length, the composition rules and the model letter. This skill holds
the process; those numbers live there and are not copied here.

- **Cut to the spec's ceiling before packing**, never deliver long and offer to
  trim. A recruiter gives the page about fifteen seconds, so visible white space
  is part of the deliverable.
- **One anecdote per letter, maximum**, carrying no sentence explaining what it
  meant. Let it land and stop.

1. **Opening in the chosen approach.** Specific, honest, non-generic, grounded
   in the user's own work or a concrete contrast. It leads with work the user
   has done and carries the target job title within its first two sentences;
   the spec's composition rule 1 governs where the company's name goes.
2. **Strongest alignment**, told briefly with context and outcome. For Senior
   and above, this paragraph or the next operates at decision altitude.
3. **Second alignment, or the honest gap** named directly and pivoted to
   transferable value.
4. **Something unusual and hard to find in other candidates at this level**,
   from the anecdotes file. Framed as one thing that might be useful context,
   not a trophy.
5. **Close plainly** — one or two sentences of interest in talking and hope that
   it is a good fit.

Sign off with the closing line and name format the user's own template
specifies.

## Voice

Register: confident, not brash. Personable, not performing. Understated, plain
language, no hype and no flourish for its own sake. Dry humor survives when it
is situational and never telegraphed. **The voice profile's
self-promotional-revolt framing describes how the user feels about writing
these, not the register the letter adopts** — reading it the other way produces
an aggressive letter.

- **Read the instance's voice-profile file in full once per session**, at the
  first composition rather than at session start, and not again that session.
- **Read the voice-interview appendix only on an explicit recalibration
  request.**
- **Inhabit the voice rather than imitate it**, per the profile's own
  anti-overfitting guidance. Specific voice patterns belong to that file and are
  not restated here.

## Docx output

Build the letter to `data/*/career/foundation/header_design_spec.md` — page
setup, fonts, colors, spacing, contact-line segment colors and body-text tokens.
That markdown spec is the template and carries the exact OOXML tokens needed to
rebuild the header; there is no separate `.docx` template file. Populate the
header's name, title, location, phone, email and profile link from
`data/*/career/foundation/contact_info.md`.

**Run the AI-ism self-review by reading, before linting.** The lint blacklist
catches known wordings only, so a novel phrasing has to be caught here. Rewrite
anything that trips:

- recurring-thought framing ("I keep coming back to…")
- pre-emptive hedges ("not to imply…", "just to clarify…")
- explaining the company's own product back to it
- "gap"-labeling language instead of naming the gap plainly
- mapping metaphors ("maps to…")
- any construction announcing that the writer is being honest, plain or
  not-exaggerating — directness is the default, so stating it is a tell
- vague reaction statements with no content

**Then run `tools/career_coach/cl_lint.py` on the draft text**, fix every HARD,
dash and period-emphasis hit, review FLAG hits, pack the docx, and run the lint
tool again on the packed docx. It must pass before delivery. The tool finds the
instance's blacklist in the user's career data root, where the list lives
because it is their content rather than the tool's.

## Delivery

Surface a compact note of three to five lines: what research found (the
confirmed company plus the one earned hook), one line naming the chosen approach
descriptively, then the plain-text letter and the docx. **Offer corrections
after delivery, never before.**

**Save the plain text and the packed docx into `applications/cover_letters/` in
the user's data root** as well as sending them to chat, every time. A letter
that exists only in chat scrollback is not part of the record.

## Referral check

**Where the JD or the user names a contact inside the target company and no
outreach has happened, stop and remind them to make that touchpoint before
submitting.** This overrides the rest of this flow.

## Redraft analysis

When the user edits a draft, analyze the structural deltas to sharpen the model
of their voice. **Flag objective errors and respect stylistic variance.** Queue
valid voice nuances and newly discovered banned phrasings for
`src/skills/session-closure/SKILL.md`.

## Research handoff

When research would improve triage or letter quality and none has been given,
hand the user the prompt in `tools/career_coach/research_prompt_template.md`,
filled in with the target company name, to run externally and paste back. Offer
it for Apply and Borderline verdicts and before a cold letter with no preceding
triage; never for a Skip.
