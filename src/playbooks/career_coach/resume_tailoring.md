# Resume Tailoring — career_coach playbook

Lazy workstream. Trigger only on request. Produces a tailored resume in two
formats plus a tailored cover letter (see `cover_letter.md` for the letter
rules in full; this file covers the resume).

Inputs are all in the user's personal project: the base resume, the always-on
context core, and any on-demand context module named in the index (see
`jd_evaluation.md`'s fit-rubric section for the always-on/load-on-demand
split). The ATS source of truth is the plain-text resume file, not the
formatted docx.

Output file names (use exactly, substituting the user's own name from their
contact-info file):

```
[User_Name]_Resume.docx            -- formatted, human-facing
[User_Name]_Resume_Plain_Text.docx -- ATS/plain-text
[User_Name]_Cover_Letter.docx      -- cover letter
[Company]_Application.zip          -- zip of all three, [Company] from the JD
```

## Absolute rules

- Never let a tailored resume run shorter than the base. Check paragraph
  count after generating; if under the base's density, expand bullets before
  cutting anything, and don't compress Early Career or Education. Flag any
  length risk in delivery.
- Never invent experience, metrics, titles, companies, products, or
  technologies. Never fabricate outcomes, scope, or credentials.
- Never claim a skill or credential the user doesn't have.
- Never remove a positioning frame that honestly addresses a real background
  gap (e.g. a non-traditional path into the field) — check the instance's
  context file for what this framing point actually is; it's a feature to
  keep, not something to sand off.
- Never exceed two pages for the formatted resume. Length is unrestricted for
  the plain-text/ATS resume.
- Never produce a cover letter that sounds generic, templated, or
  AI-generated (full rules in `cover_letter.md`).
- Never keyword-stuff — relevance must feel earned, not forced.
- Never flag a keyword as [MISSING] if the context file documents it as real
  experience; check both the resume and the context modules before assigning
  a status (see `jd_evaluation.md`'s rubric).

## Section 1: Analysis (produce first, then stop and wait)

Analyze the JD and produce:

**Top ATS keywords**: the 10-15 most important keywords/phrases, each
checked against both the base resume and the context files before a status:
`[PRESENT]` (in the resume), `[CONTEXT-ONLY]` (not in the resume but a context
file documents it — incorporate before flagging a gap), `[MISSING]` (absent
from both — a true gap to flag and address). If a `[MISSING]` flag prompts a
correction from the user, queue that correction for the context-file update
in `session_closure.md`; don't ask them to edit the file mid-session.

**Match strengths**: where the background aligns strongly with this role, be
specific.

**Honest gaps**: where it falls short. Don't soften this — the user needs to
know what a hiring manager will notice.

**Positioning strategy**: 3-5 sentences on how to frame this application and
the single strongest narrative thread.

**Cover-letter flag**: anything the resume can't handle alone that the letter
must address directly (a career pivot, a domain gap, a background angle
relevant to this specific role).

Then pause: ask whether anything looks wrong or is missing before building
the documents. Wait for a response. Incorporate any clarification into all
three documents; accumulate new information in session memory rather than
asking for a context-file edit mid-session (see `session_closure.md`).

## Section 2A: Tailored resume (formatted, human-facing)

The base resume's design tokens (fonts, colors, rule weights, spacing,
page margins) are locked per the header-design spec at
`data/*/career/foundation/header_design_spec.md` — read it before touching the
docx; do not reinterpret design from the base file. Contact fields come from
`data/*/career/foundation/contact_info.md`.

Formatting rules: dates appear on the company row only, never repeated on
role-title rows. Group multiple roles at one company under one header with
sub-rows. A bullet that wraps to a short second line is a density failure —
expand or compress, never leave an orphan line (headers exempt). Do not force
page breaks; meet the length constraint through content and spacing.

Resume rules: exactly two pages. Rewrite the summary to open with the
strongest alignment to this specific role (4-5 lines, never generic).
Rewrite bullets to be one idea each, action-verb led, accomplishment-oriented,
free of filler, and density-compliant. Lead each role with its most relevant
bullets to this JD; compress roles more than ~8 years old aggressively.
Reorder and substitute the competencies table's items to surface JD
keywords — never add a skill the user doesn't have, but do substitute
terminology where an existing skill maps to the JD's preferred language.
Keep education/recognition as-is unless the JD gives specific reason to
adjust. ATS safety: standard section names, no text boxes, no
headers/footers for critical content, consistent date formatting, company
names and titles spelled out in full.

## Section 2B: Tailored resume (plain-text / ATS version)

Same experience content as 2A — same bullets, same summary, same tailoring
decisions. Only formatting and the skills section change.

Layout: single-column, fully linear, no tables/tab stops/multi-column/rules/
custom colors. Font: one plain font throughout, no accent colors. Length
unrestricted.

Each role is a self-contained record with explicit field labels mirroring
ATS form fields, each on its own line: `Job Title:` (bold), `Company:`,
`From:`, `To:` (month + year only), `Role Description:` then bullets. Use the
per-title date ranges stored in the context file (`COMPLETE EMPLOYMENT
DATES` or equivalent); never infer dates from the base resume's
company-level ranges. Multiple roles at one company each get their own full
labeled block, not a shared header. Job titles: actual title only, no
descriptors. Early career folds into the main experience section using the
same structure, no separate section. Education heading is "Education" only,
degree and institution, no awards. Avoid em dashes and glyphs that may not
parse; use double hyphens instead.

Skills section: heading "Skills," not "Competencies." Flat list, one skill
per line, no columns/commas/bullets/separators. Pull skills from the
instance's own master skills list (config, not this file), 20-25 items
prioritized by relevance to this JD, most relevant first, reordered per JD.
Substitute terminology to match the JD's exact language where an existing
skill maps to it; never add a skill not present in that list. Use shorter
keyword forms than the formatted resume's competencies table — this section
is for parser optimization, not human reading, so don't duplicate identical
phrasing between the two.

## Section 3: Context-file update check

After producing the documents, check: did this application surface any
experience, skill, or context not currently captured in the context file? If
yes, list the specific additions, factual and concise, ready to paste in. If
a `[MISSING]` flag was corrected by the user, always recommend adding that
clarification. If nothing new surfaced, say so briefly. Do not ask the user
to update the context file mid-session — accumulate across the session and
hand off a full draft at `session_closure.md` or on demand.

## Delivery

Package all three documents into `[Company]_Application.zip` and present it
as the primary download; individual files may also be presented for review.
