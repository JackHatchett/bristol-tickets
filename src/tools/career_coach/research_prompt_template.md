# Company Research Prompt

Input is a company name. Operation is handing the user the block below, filled
in, to run in a search-capable tool. Output is the research packet they paste
back.

- **Offer it on an Apply or Borderline verdict, and before a cold letter**,
  where the user has supplied no research. Never on a Skip.
- **Hand the block over verbatim**, adjusting wording only where a particular
  tool reads a different phrasing better.

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
6. EMPLOYEE SENTIMENT: Any employee-review signals about management, culture,
   or the product organization.
7. COMPETITIVE CONTEXT: Main competitors and what differentiates this company.
Format as plain numbered sections, 3-5 sentences each. Plain text only.
```

`playbooks/career_coach/jd_evaluation.md` and `cover_letter.md` own the
web-research policy this stands in for.
