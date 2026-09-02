---
name: resume-tailoring
description: Rewrites the resume for one job posting, in a formatted version and a plain-text version that machines can read. Use when the user asks for a resume aimed at a particular role.
license: MIT
compatibility: Needs python3 and the repository's document tools for the .docx output.
metadata:
  bristol.kind: playbook
  bristol.maintainer: career_coach
  bristol.scripts: src/tools/career_coach/voice_lint.py
---
# resume-tailoring

Produces a tailored resume in two formats plus a tailored cover letter. This
skill covers the resume; `src/skills/cover-letter/SKILL.md` owns the letter's
rules in full, and `src/skills/base-resume-update/SKILL.md` owns a content
change to the master made with no job description in play.

Inputs live in the user's career data root: the base resume, the always-on
context core, and any on-demand module the index names — see
`src/skills/jd-evaluation/SKILL.md` §The fit rubric for the split. **The ATS source of truth is
the plain-text resume, not the formatted docx.**

Output file names, substituting the user's own name from their contact-info
file:

```
[User_Name]_Resume.docx            -- formatted, human-facing
[User_Name]_Resume_Plain_Text.docx -- ATS/plain-text
[User_Name]_Cover_Letter.docx      -- cover letter
[Company]_Application.zip          -- zip of all three, [Company] from the JD
```

## Absolute rules

- **Never let a tailored resume run shorter than the base.** Check paragraph
  count after generating; where density falls below the base, expand bullets
  before cutting anything, never compress Early Career or Education, and flag
  any length risk at delivery.
- **Never invent experience, metrics, titles, companies, products,
  technologies, outcomes, scope or credentials.**
- **Never claim a skill or credential the user does not have.**
- **Never remove a positioning frame that honestly addresses a real background
  gap.** The instance's context file says what that framing point is; it is a
  feature to keep rather than something to sand off.
- **Never exceed two pages for the formatted resume.** Length is unrestricted
  for the plain-text version.
- **Never keyword-stuff.** Relevance has to read as earned.
- **Never flag a keyword as MISSING where a context file documents it as real
  experience.** Check the resume and the context modules before assigning a
  status, per `src/skills/jd-evaluation/SKILL.md`'s rubric.

## Section 1: Analysis

**Produce the analysis first, then stop and wait.**

- **Top ATS keywords** — the 10 to 15 most important, each checked against both
  the base resume and the context files before a status: `[PRESENT]` in the
  resume, `[CONTEXT-ONLY]` where a context file documents it (incorporate it
  before flagging a gap), `[MISSING]` where it is absent from both. **Queue any
  user correction to a `[MISSING]` flag for `src/skills/session-closure/SKILL.md`** rather than
  asking them to edit the file mid-session.
- **Match strengths** — where the background aligns strongly, specifically.
- **Honest gaps** — where it falls short, unsoftened. The user needs to know
  what a hiring manager will notice.
- **Positioning strategy** — 3 to 5 sentences on how to frame this application,
  and the single strongest narrative thread.
- **Cover-letter flag** — what the resume cannot handle alone and the letter
  must address: a career pivot, a domain gap, a background angle specific to
  this role.

**Then pause and ask whether anything looks wrong or missing before building the
documents.** Wait for a response, incorporate any clarification into all three
documents, and accumulate new information in session memory for
`src/skills/session-closure/SKILL.md`.

## Section 2A: Formatted resume

**Read `data/*/career/foundation/header_design_spec.md` before touching the
docx.** Fonts, colors, rule weights, spacing and page margins are locked there;
never reinterpret design from the base file. Contact fields come from
`data/*/career/foundation/contact_info.md`.

**Formatting**

- **Dates appear on the company row only**, never repeated on role-title rows.
- **Group multiple roles at one company under one header** with sub-rows.
- **A bullet that wraps to a short second line is a density failure** — expand
  or compress rather than leaving an orphan line. Headers are exempt.
- **Never force a page break.** Meet the length constraint through content and
  spacing.

**Content**

- **Exactly two pages.**
- **Rewrite the summary to open with the strongest alignment to this role**, 4
  to 5 lines, never generic.
- **One idea per bullet**, action-verb led, accomplishment-oriented, free of
  filler, density-compliant.
- **Lead each role with its most relevant bullets to this JD**, and compress
  roles more than about eight years old aggressively.
- **Reorder and substitute the competencies table to surface JD keywords.**
  Substitute terminology where an existing skill maps to the JD's preferred
  language; never add a skill the user does not have.
- **Keep education and recognition as-is** unless the JD gives specific reason
  to adjust.
- **ATS safety**: standard section names, no text boxes, no headers or footers
  carrying critical content, consistent date formatting, company names and
  titles spelled out in full.

## Section 2B: Plain-text resume

Same experience content as 2A — same bullets, same summary, same tailoring
decisions. Only formatting and the skills section change.

**Layout**: single-column and fully linear. No tables, tab stops, multiple
columns, rules or custom colors. One plain font throughout, no accent colors,
length unrestricted.

**Each role is a self-contained record** with explicit field labels mirroring
ATS form fields, each on its own line: `Job Title:` (bold), `Company:`, `From:`,
`To:` (month and year only), `Role Description:` then bullets.

- **Take per-title date ranges from the context file's employment-dates
  block**, never inferred from the base resume's company-level ranges.
- **Give each role at one company its own full labeled block**, not a shared
  header.
- **Job titles are the actual title only**, no descriptors.
- **Fold early career into the main experience section** using the same
  structure, with no separate section.
- **The education heading is "Education"** — degree and institution, no awards.
- **Use double hyphens in place of em dashes** and avoid glyphs that may not
  parse.

**Skills section**: heading "Skills," not "Competencies." Flat list, one skill
per line, no columns, commas, bullets or separators.

- **Pull skills from the instance's own master skills list** in config, 20 to 25
  items, most relevant to this JD first.
- **Substitute terminology to match the JD's exact language** where an existing
  skill maps to it; never add a skill absent from that list.
- **Use shorter keyword forms than the competencies table.** This section is for
  parser optimization, so identical phrasing between the two is wasted.

## Section 3: Context-file update check

**After producing the documents, check whether this application surfaced
experience, skill or context the context file does not capture.** List the
specific additions, factual and concise, ready to paste in; always recommend
adding a clarification that corrected a `[MISSING]` flag; say so briefly when
nothing new surfaced. **Never ask the user to update the context file
mid-session** — accumulate across the session and hand off a full draft at
`src/skills/session-closure/SKILL.md` or on demand.

## Delivery

**Run `tools/career_coach/voice_lint.py` on the plain-text resume before
packaging**, fix every HARD, dash and period-emphasis hit, review the FLAG hits,
and run it again on the packed file. The gate covers everything written in the
user's voice, and a resume is one of them —
`src/tools/career_coach/README.md` owns the tool.

**Package all three documents into `[Company]_Application.zip`** and present it
as the primary download. Individual files may also be presented for review.
