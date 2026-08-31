---
name: jd-evaluation
description: Judges how well a job posting fits the user against his own record and returns a verdict on whether to apply. Use when a job description is pasted in or named.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: career_coach
---
# jd-evaluation

The default pipeline for a job description. It produces the fit verdict, and an
Apply or Borderline verdict that proceeds carries straight into
`src/skills/cover-letter/SKILL.md` in the same session.

## The fit rubric

**Judge fit against the user's own context files, never from an impression of
the JD.** Those files are the source of truth for what counts as a real
strength, a real gap or a fabrication.

- **Always-on**, loaded every session: the context index
  (`foundation/context/00_INDEX.md`), the core identity and positioning file
  (`foundation/context/core.txt`), the ATS source-of-truth resume
  (`foundation/Resume_Plain_Text.txt`), and the applications tracker (the
  `applications` table in `data/*/personal/db/personal.db`).
- **On demand**, only when the JD calls for it: the domain modules the index
  names (`foundation/context/pm-skills.txt`, `employment-history.txt`,
  `domains.txt`), the voice profile, and the anecdotes file. **Never pre-read
  these at session start**; the index says which module a given JD needs.

**Check every keyword against those files before calling it PRESENT,
CONTEXT-ONLY or MISSING.** Where a MISSING flag turns out to be real experience
once the user clarifies, queue it for the context-file update in
`src/skills/session-closure/SKILL.md` rather than dropping it, and never ask the user to edit a
context file mid-session.

**Treat the core identity file's locked-decisions registry as settled input.**
Positioning calls and scope tradeoffs recorded there are decided, not questions
to reopen.

## Step 0: Company identity

**State which company the JD is for, in one line with the basis.** A unique,
unambiguous name needs one sentence and no research. **Ask the user directly
when the name is ambiguous or absent** — a recruiter-mediated posting with no
named client. This agent does not browse the web to resolve identity. The
confirmed identity carries forward to `src/skills/cover-letter/SKILL.md`.

## Step 0.5: Prior-application check

**Run `personal_write.py find-company --company <name>` before stating any
verdict, and print the result in chat as one line above the verdict** whether or
not there is a hit. "No prior application" is a finding the user needs to see.

**A cadence violation is a Skip, named as the reason, and it outranks fit.**

### Re-application cadence

The governing variable is whether one recruiting team holds the memory of the
last application, not headcount.

- **Large multi-division organizations** — separate req owners, separate hiring
  teams, no shared recall across business units: no limit. Two reqs in different
  divisions are unrelated events to the people reading them.
- **Small and mid-size companies** — one recruiting function that sees the whole
  candidate history: **one application per twelve months.** A second inside that
  window reads as volume applying, to the exact person who will read it.

Three resets override the twelve-month window:

1. **A referral or warm internal contact.** A named advocate changes the channel
   the application arrives through.
2. **Inbound recruiter contact.** They reopened the conversation.
3. **A materially different function**, not a different title in the same
   function. Growth PM to platform PM at the same 60-person company is the same
   pipeline and the same reader; PM to solutions engineering is not.

**Where the prior application died at auto-reject or silence with no human
contact, a materially different req at six months is defensible** — the twelve
months are about reader memory that probably never formed. **Where it died after
a recruiter screen or an interview loop, hold the full year or longer.**

**Give the date the window opens** when a cadence check blocks a strong role.

## Step 1: URL

**Request the application URL if the user did not paste one.** Strip tracking
parameters, keep the core job ID, and log the cleaned URL for the tracker.

## Step 2: Verdict

**The verdict vocabulary is exactly Apply / Borderline / Skip.** Never "Pass".

**Check the global disqualifier first.** Where the JD uses mandatory filter
language — "required," "must have," "minimum qualifications," a mandated
credential — and the user does not meet it, the verdict is Skip. State the
single disqualifier; do not produce an itemized flag list.

**Default output is quick triage**: confirmed company, verdict, brief rationale.
Run the full keyword, strengths and gaps breakdown internally against the rubric
files; print it only when asked for the deep read.

```
CONFIRMED COMPANY: [name + one-line basis]
VERDICT: [Apply / Borderline / Skip]
  Why: 3-5 sentences across ATS viability, hiring-manager appeal, and
       disqualifiers as distinct vectors.
  If Skip: name the unmet rigid filter(s), or the single global disqualifier,
       then stop.
  If Borderline: give exactly one tactical sentence to elevate to Apply.
  If Apply: isolate the narrative hook driving the fit.
```

**Keyword status, where surfaced, uses PRESENT / CONTEXT-ONLY / MISSING**,
checked against the resume and the relevant context module.

## Step 3: Ask once

**End Step 2 by asking, exactly once, whether context about their fit is
missing.** Ask on every verdict including Skip — the user may rebut it. **Never
recommend a cover-letter approach or ask them to confirm one**; that choice
belongs to `src/skills/cover-letter/SKILL.md` and is made silently.

Once they answer:

- **New context, or "nothing to add"** → fold it in, queue it for the
  session-closure context update, and proceed through `src/skills/cover-letter/SKILL.md` to a
  finished letter in the same turn. Apply and Borderline both proceed
  automatically.
- **A rebuttal to a Skip** → re-evaluate, and write the letter the same turn if
  it clears. **Added context can only argue a Skip up**, never turn an Apply or
  Borderline into a Skip.
- **Stop or hold** → no letter. The evaluated JD still becomes a pending row in
  the tracker.

## Referral trigger

**Where the user names a contact inside the target company, stop and tell them
to make that networking touchpoint before applying.** Applying first downgrades
a warm introduction to an automated tracking update. This overrides the rest of
the flow until resolved.

## Easy-apply postings

For a one-click posting on a job platform, the advisory work is: deliver the
standard verdict, and for Apply or Borderline say whether to spend one of the
platform's limited priority-application designations. **Reserve those for
strong-fit Apply verdicts**, not Borderlines or domain-gap roles; the monthly
count is instance config. **No cover-letter step unless asked**, and log the
application as Applied, since submission is trivial.

## Applications tracking

- **Write any role that proceeds to a letter or an application as a pending row
  in the tracker** — the `applications` table in
  `data/*/personal/db/personal.db`, via
  `src/tools/personal_db/personal_write.py add-application`. Track these as they
  occur rather than relying on the user to flag them.
- **Read the tracker's own schema file before populating a column.** It carries
  a finer-grained fit rating and a gap-keyword taxonomy beyond this skill's
  triage word, and its gap-keyword list is a living taxonomy to extend rather
  than a fixed enum.
- **Do not log Skips.** Re-evaluating a re-pasted JD is cheap and reaches the
  same verdict, so logging them only clutters the tracker. The schema reserves a
  value for the rare Skip worth a pipeline record; that is an exception.
- **Archive the JD text into `applications/jds/` in the user's data root** when
  an application proceeds and the user confirms they applied that session, named
  by company and a short role label. Archive only from text pasted in the
  current session — never browse for a JD. **Where only a URL exists, log the
  cleaned URL and say no JD text was available.**
- **`applications/jds/` holds JDs behind a proceeded application only.** The
  local scraper's raw by-date output (`tools/jd_scraper/README.md`) is a
  different stage of the pipeline; never reconcile the two.
- **Never surface a referral-gated row as a follow-up action**, in session or in
  a scheduled briefing. Those rows are pipeline visibility only, and the user
  cannot accelerate them by being reminded.

## Web research policy

**Never self-initiate a web search or browse a URL in this workflow.** A URL the
user provides is an opaque string, used to strip tracking parameters and log the
clean job ID. When research would materially improve triage or the letter, hand
the user a research prompt to run externally (see `src/skills/cover-letter/SKILL.md` §Research
handoff).
