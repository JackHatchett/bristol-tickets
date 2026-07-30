# Company research prompt template

A fixed, reusable prompt structure for handing the user a company-research
request to run externally (a search-capable assistant, a research tool) when
this agent's own web-research policy (see `jd_evaluation.md` and
`cover_letter.md`) means it won't self-browse. Fill in the company name and
hand this to the user verbatim; paste their result back as research input for
triage or the cover letter.

```
Please research [COMPANY NAME] and return a structured research packet I can
use for a job application cover letter. Include:
1. WHAT THEY DO: Core product or service in 2-3 sentences.
2. BUSINESS MODEL AND STAGE: B2B/B2C/B2B2C, funding stage, approximate
   headcount, recent funding rounds.
3. TECH AND PRODUCT SIGNALS: Tech stack, platform type (mobile/web/API/etc.),
   any known product methodology or notable technical details.
4. CULTURE AND VALUES: Stated mission, values, or culture signals from their
   website, job postings, or press.
5. RECENT NEWS: Notable milestones, launches, partnerships, or press coverage
   from the last 12 months.
6. EMPLOYEE SENTIMENT: Any Glassdoor or Blind signals about management,
   culture, or the product organization.
7. COMPETITIVE CONTEXT: Main competitors and what differentiates this company.
Format as plain numbered sections, 3-5 sentences each. Plain text only.
```

When to offer it: for Apply and Borderline verdicts at the triage stage, and
before composing a cold letter (one with no preceding triage this session)
if the user hasn't already supplied research. Never offer it for a Skip.

Tune the actual wording per external tool if a specific assistant responds
better to a different phrasing; this template is the default, not a rigid
requirement.
