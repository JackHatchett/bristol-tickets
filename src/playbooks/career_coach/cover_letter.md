# Cover Letter — career_coach playbook

Runs automatically once the user answers `jd_evaluation.md`'s Step 3 context
question — that answer is full authorization. Do research, approach
selection, drafting, linting, and packing in the same turn, no further
prompt-back.

## Absolute rules

The full enforceable list is the instance's own blacklist file (in the user's
personal project, never in this shared playbook). The headline rules,
restated so they're never missed:

- Never produce a letter that sounds generic, templated, or AI-generated.
- Never use the account-level banned phrases or constructs (see the global
  voice rules; this agent does not restate them).
- Never frame anything in the letter as a problem: not the company's, not the
  industry's, not one the role exists to solve, and never with the user
  positioned as the answer. The word "problem" does not appear in a letter.
  The first sentence names the company and what the user has done that fits
  the role, because the letter is addressed to a reader and opens facing them.
- Never open in media res. Dropping the reader into the middle of a scene is a
  fiction-mode move and reads as aggressive in a letter.
- Never open a paragraph with a weakness. The negative belongs in a
  subordinate clause with the strength in the main clause ("Although I have
  never done X, I did Y for four years"). Gaps are still named honestly and
  never hoped past, but leading with one, or elaborating past the clause that
  concedes it, is a craft error.
- Never use a generic salutation ("Dear Hiring Team," "To Whom It May
  Concern").
- Never write a sentence that could appear unchanged in another applicant's
  letter.
- Never summarize the resume — the reader already has it.
- Never use en-dashes, em-dashes, double hyphens, or repetitive punctuation
  anywhere in the letter or its delivery notes. Single hyphens inside
  compound terms are fine ("full-time"). Enforce this on the draft itself,
  not just at lint time.
- Never invent experience, metrics, titles, or outcomes, and never stretch a
  real fact onto the wrong role. Verify every claim against the resume and
  context files before it ships.
- Never address the letter to the wrong company — identity was confirmed at
  triage; inherit it (see Step 0 below for the cold-letter exception).
- Never quote or reference a review source in the letter itself (app-store
  complaints, Glassdoor). Research informs the letter; it never appears in it.

## Conventions of the form (always true, never voice-dependent)

These are the genre's rules, not the user's preferences. They hold for every
letter, every company, every verdict. Voice operates inside them; it never
overrides them. When a voice guideline and a convention here appear to
conflict, the convention wins and the voice guideline is the thing that needs
correcting.

**Length and shape**
- One page. Never two, under any circumstance.
- The letter adds what a resume structurally cannot carry: judgment, reasoning,
  the story behind a line. It never restates the resume, and never repeats a
  resume sentence verbatim.

**Address and stance**
- The letter is written to a reader. Name the company early and use the second
  person. A letter with no "you" in it is a personal essay.
- Name the role by its actual posted title, once.
- Never explain the company's own product, market, or users back to it.
- Never flatter the company. "Industry leader," "incredible mission," and
  their relatives are invisible to the reader at best.
- Never mention the application process itself: no "as you can see from my
  attached resume," no "per the job posting," no "you asked for X, I have X"
  requirements recitation.

**Claims**
- Concrete over abstract. Named systems, named decisions, real outcomes.
- No superlatives attached to your own work.
- Enthusiasm is not a qualification and is never offered as one.
- Numbers only where they are real and load-bearing. A letter of statistics
  reads as a resume with worse formatting.
- Past work in past tense, consistently.

**Weakness**
- Never apologize, and never pre-empt a rejection on the reader's behalf.
- A gap, if named at all, is named once, in a subordinate clause, and never
  elaborated past that clause.

**Close**
- The closing is a courtesy formality, not a pitch. Express interest in
  talking and hope that it is a good fit. That is the whole genre.
- Never presume a process: no imagined conversation to be joined, no assumed
  next step, no proposed date, no "I will follow up on Tuesday."
- Never raise salary, competing offers, timelines, or other applications
  unless the posting asks.
- Sign-off, then the name. Nothing after it.

**Punctuation**
- No exclamation points.
- Em-dashes, en-dashes, and double hyphens are hard-banned (see below).

## Step 0: Research

**Identity**: reuse the company confirmed in `jd_evaluation.md`'s Step 0; do
not re-derive it. Cold-letter exception: if the user pasted a JD and asked
for a letter with no preceding triage this session, run the identity check
now, before anything else. If the company name is shared with a larger or
more famous organization, do not assume the famous one; confirm against a
primary source by matching JD fingerprints (verbatim benefit strings, size
and funding-stage language, product nouns, methodology tells). If two
candidates stay plausible, stop and ask which one — a wrong-company letter is
worse than any voice flaw.

**Deep research**: research the product and organization so the letter speaks
to what they actually build, not just the JD text. Priority order: company
site and product pages, product/engineering blog, recent news (verify
dates), the app and its app-store reviews for consumer/app companies,
Glassdoor for culture signal. Keep it proportional: one confirming pass plus
one earned hook, not a company book report. This agent does not browse the
web itself for this research — hand the user a research prompt to run
externally and paste back (see "Research handoff" below) unless the session
already has research to work from.

**Guardrails**: use only specifics verifiable against a primary source. Treat
review sites as a hypothesis generator, not truth — they skew negative.
Research is targeting input for which of the user's stories to foreground,
never letter content; none of it is ever named or quoted in the letter.

**Internal fit read** (drives emphasis, never printed as a block): which
high-weight JD keywords are PRESENT in the resume, which are CONTEXT-ONLY,
which are true gaps (per `jd_evaluation.md`'s rubric). The strengths, and the
one honest gap a sharp interviewer will exploit. The single strongest
narrative thread connecting the user's background to this role.

**Seniority altitude**: for Senior-level roles and above, at least one body
paragraph must operate at portfolio altitude — a roadmap tradeoff, a
build-vs-buy call, resource allocation across teams, or a feature
deliberately killed, not "I shipped X." Pull the ONE altitude-appropriate
proof point from the user's anecdotes and employment-history context files;
do not stack several, and do not invent one.

## Approach menu (choose silently — never recommend or ask)

Refer to the chosen approach only by descriptive name if you must mention it
in the delivery note; never by a letter code.

- **"User experience is my passion"**: the user is a real user of this
  product or a close competitor. Research must confirm plausible use. Opens
  from honest personal use, arrives at "I have opinions about this UX and
  would like to own it." Positive only, never a product audit.
- **"Personal history coincidence"**: something in the user's real history
  maps honestly to the company's mission or users. Only if the connection is
  real — a forced one is worse than none.
- **"Specific technical observation"**: the user has a genuine, specific
  observation about a technical problem the company is solving, matched to a
  named experience from their context files. "I find this space fascinating"
  is not this approach.
- **"Pivot toward meaning"**: the user's industry history is the elephant in
  the room, and naming it memorably beats hoping the reader overlooks it.
  Honest reckoning with the previous work, then a specific reason this role
  would feel different. Best where the role's mission is itself the draw; which
  sectors those are for this user is in their context files.
- **Mixed**: combine approaches with a clear structural reason.

## Structure

**Read `data/*/career/foundation/cl_reference.md` before drafting.** That file
is the central reference for what a finished letter looks like: the binding
structural spec (word count, paragraph count, paragraph and sentence length),
the composition rules, and the model letter. This playbook holds the process;
that file holds the shape.

Word count, paragraph count and paragraph length are that file's numbers, not
this one's — do not carry a second copy here. A recruiter gives the page about
fifteen seconds, so visible white space is part of the deliverable. If a draft
exceeds the spec's hard ceiling, cut before packing; do not deliver and offer to
trim afterward.

One anecdote per letter, maximum, and it carries no sentence explaining what
the anecdote meant. Let it land and stop.

No salutation by default — open directly with Paragraph 1; exception: a named
contact, addressed by name.

1. Opening in the chosen approach. Specific, honest, non-generic. Ground it
   in the user's own work or a concrete contrast, not the company's pain.
2. Strongest alignment, told briefly with context and outcome. For Senior and
   above, this or paragraph 3 must operate at decision altitude.
3. Second alignment, or the honest gap named directly, no apology, then
   pivot to transferable value.
4. Something unusual and hard to find in other candidates at this level —
   pull it from the user's anecdotes file. Frame as "one thing that might be
   useful context," not a trophy.
5. Close plainly. One or two sentences expressing interest in talking and hope
   that it's a good fit. No clever framing, no invented scenario, and never a
   conversation imagined to be underway that the user asks to be let into.

Sign off with the closing line and name format the user's own template
specifies (their personal project, not this file).

## Voice

Register: confident, not brash. Personable, not performing. Understated, plain
language, no hype and no flourish for its own sake. Dry humor survives when it
is situational and never telegraphed. The voice profile's self-promotional-
revolt framing describes how the user feels about writing these, not the
register the letter should adopt; do not let it produce an aggressive letter.

Read the instance's voice-profile file in full once per session, at the
moment of the first composition this session — not at session start, and not
again later the same session. Read the full voice-interview appendix only on
an explicit recalibration request. Follow its anti-overfitting guidance:
inhabitation, not imitation. This playbook does not restate specific voice
patterns; they belong entirely to the instance's own voice-profile file.

## Docx output

Build the letter to the header design spec at
`data/*/career/foundation/header_design_spec.md` (page setup, fonts, colors,
spacing, the contact-line segment colors, and the body-text tokens) — there is
no separate `.docx` template file; that markdown spec *is* the template, and it
carries the exact OOXML tokens needed to rebuild the header. Populate the
header's contact fields (name, title, location, phone, email,
professional-profile link) from `data/*/career/foundation/contact_info.md`;
never hardcode them here.

Before packing, run the AI-ism self-review pass: check for recurring-thought
framing ("I keep coming back to..."), pre-emptive hedges ("not to imply...",
"just to clarify..."), explaining the company's own product back to it,
"gap"-labeling language instead of naming the gap plainly, mapping metaphors
("maps to..."), candor/truth-telling assertions (any construction announcing
you're being honest / plain / not-exaggerating — e.g. "I want to name that
plainly rather than stretch it": directness is the default, so stating it is a
tell; see the voice profile's Never rule), and vague reaction statements with
no content. This is a *concept* pass, applied by reading, not a phrase-match —
the `cl_lint` blacklist below is only a backstop that catches known wordings,
so novel phrasings must be caught here, at draft time. Rewrite anything that
trips these.

Then: run the lint tool (`tools/career_coach/cl_lint.py`) on the draft text. It
finds this instance's blacklist in the user's own career data root, where the
list lives because it is their content and not the shared tool's. Fix every
HARD, dash, and period-emphasis hit, review FLAG hits, pack the docx, and run
the lint tool again on the packed docx as a final backstop. It
must pass before delivery. There is no separate validator; if you want to
confirm the docx is well-formed, unzipping it and checking that
`word/document.xml` parses is optional, not a blocking step.

## Delivery

Surface a compact note, three to five lines: what research found (the
confirmed company plus the one earned hook), one line naming the chosen
approach descriptively, then the plain-text letter and the docx. Offer
corrections after delivery, not before.

Save the finished letter (plain text and the packed docx) into
`applications/cover_letters/` in the user's own data root, not just into
chat. A cover letter that only exists in chat scrollback isn't part of the
long-term record; delivery to chat and delivery to disk both happen, every
time, unconditionally.

## Referral check

If the JD or the user names a contact inside the target company and no
outreach has happened yet, stop and remind them to run that networking
touchpoint before submitting. This overrides the rest of this flow.

## Redraft analysis

When the user edits a draft, analyze the structural deltas to sharpen the
model of their voice. Flag objective errors; respect stylistic variance.
Queue valid voice nuances and any newly discovered banned phrasings for
`session_closure.md`.

## Research handoff (when the user should run research externally)

When research would improve triage or letter quality and this agent hasn't
been given research already, hand the user the fixed prompt in
`tools/career_coach/research_prompt_template.md`, filled in with the target
company name. Offer it for Apply and Borderline verdicts and before composing
a cold letter with no preceding triage; never for a Skip.
