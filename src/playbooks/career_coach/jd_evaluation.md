# JD Evaluation — career_coach playbook

Default pipeline. Trigger: the user pastes or names a job description. This is
the entry point for the whole career_coach workflow: it produces the fit
verdict, and (see `cover_letter.md`) a verdict of Apply or Borderline that
proceeds carries straight into a cover letter in the same session.

## The fit rubric (read this before judging fit — do not eyeball it)

Fit is never judged from general impressions of the JD. It is judged against
the user's own context files, which are the source of truth for what counts
as a real strength, a real gap, or a fabrication:

- **Always-on** (load every session, cheap): the context index
  (`foundation/context/00_INDEX.md`), the core identity/positioning file
  (`foundation/context/core.txt`), the ATS-source-of-truth resume
  (`foundation/Resume_Plain_Text.txt`), and the applications tracker (the
  `applications` table in `data/*/personal/db/personal.db`).
- **Load on demand** (only when the JD's content calls for it): domain modules
  (`foundation/context/pm-skills.txt`, `employment-history.txt`, `domains.txt`,
  or whatever modules this instance's index defines), the voice profile, and
  the anecdotes file. Do not pre-read these at session start; the index tells
  you which module a given JD needs.

Every keyword or requirement in Section 2 below gets checked against these
files before being called PRESENT, CONTEXT-ONLY, or MISSING. If a MISSING
flag turns out to be real experience once the user clarifies it, record that
for the context-file update (see `session_closure.md`) — never silently drop
it, and never ask the user to edit the context file mid-session.

The core identity file also holds a locked-decisions registry: strategic
choices the user has already settled (positioning calls, scope tradeoffs).
Do not re-debate anything recorded there; treat it as decided input to the
verdict, not a question to reopen.

## Step 0: Company identity

State which company the JD is for, in one line with the basis. If the name is
unique and unambiguous, that's one sentence, no research needed. If it's
ambiguous or absent (e.g. a recruiter-mediated posting with no named client),
ask the user directly rather than guessing. This agent does not self-browse
the web to resolve identity. The confirmed identity carries forward to the
cover-letter stage; don't re-derive it there.

## Step 0.5: Prior-application check (mandatory, and always surfaced)

Before stating any verdict, run `personal_write.py find-company --company
<name>` against the applications tracker. This is not optional and it is not
silent: **print the result in chat as one line above the verdict**, whether or
not there is a hit. "No prior application" is a finding the user needs to see,
not a null result to swallow.

If there IS a prior row, the re-application cadence policy below decides
whether the verdict may be Apply at all. A cadence violation is a Skip with the
prior application named as the reason, and it outranks fit.

### Re-application cadence policy

The governing variable is whether one recruiting team holds the memory of the
last application, not headcount for its own sake.

- **Large multi-division organizations** (separate req owners, separate hiring
  teams, no shared recall across business units): no limit. Apply as often as
  a genuinely different role appears. Disney Commerce and a Disney streaming
  req are unrelated events to the people reading them.
- **Small and mid-size software companies** (one recruiting function that sees
  the whole candidate history): **one application per twelve months.** A second
  application inside that window reads as volume applying to the exact person
  who will read it, and it costs more than the marginal shot is worth.

Three resets that override the twelve-month window for small and mid-size
companies:

1. **A referral or a warm internal contact.** A named advocate changes the
   channel the application arrives through; the clock does not apply.
2. **Inbound recruiter contact.** They reopened the conversation; that is not
   the user reapplying.
3. **A materially different function**, not a different title in the same
   function. Growth PM to platform PM at the same 60-person company is the same
   pipeline and the same reader; PM to solutions engineering is not.

One adjustment to the flat rule, applied by judgment: if the prior application
died at auto-reject or silence with no human contact, the twelve months are
about reader memory that probably never formed, and a materially different req
at six months is defensible. If it died *after* a recruiter screen or an
interview loop, hold the full year or longer, because that reader remembers.

When a cadence check blocks an otherwise strong role, say so plainly and give
the date the window opens.

## Step 1: URL

Request the application URL if the user didn't paste one. Strip tracking
parameters, keep the core job ID, and log the cleaned URL for the applications
tracker.

## Step 2: Verdict

Verdict vocabulary is exactly **Apply / Borderline / Skip** — never "Pass".

Check the global disqualifier first: if the JD uses mandatory filter language
("required," "must have," "minimum qualifications," a mandated credential)
and the user doesn't meet it, the verdict is automatically Skip. State the
single disqualifier; don't produce an itemized flag list.

Default output is quick triage only: confirmed company, verdict, and a brief
rationale (ATS viability, hiring-manager appeal, hard disqualifiers, next
step). Run the full keyword/strengths/gaps breakdown internally against the
rubric files above; print the full breakdown only if asked for the deep read.

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

Keyword status, if surfaced, uses PRESENT / CONTEXT-ONLY / MISSING, checked
against the resume and the relevant context module — never against memory or
assumption.

## Step 3: Ask once

End Step 2 by asking the user, exactly once, whether there's additional
context missing about their fit. Ask this on every verdict, including Skip —
the user may rebut it. Do not recommend a cover-letter approach or ask them to
confirm one here; that decision belongs entirely to `cover_letter.md`, made
silently.

Once the user answers:
- New context, or "no context to add": fold it in, queue it for the
  session-closure context-file update, and proceed straight through
  `cover_letter.md` to a finished letter in the same turn. Apply and
  Borderline both proceed automatically.
- Rebuts a Skip with new context: re-evaluate. If it clears, write the letter
  the same turn. Added context can only argue a Skip up, never turn an
  Apply/Borderline into a Skip.
- Says stop/hold: no letter. The evaluated JD is still logged as a pending
  row in the applications tracker.

## Referral trigger

If the user names a contact inside the target company at any point, pause and
tell them to run that networking touchpoint before applying — never after.
Applying first downgrades a warm introduction to an automated tracking
update. This overrides the rest of the flow until resolved.

## LinkedIn Easy Apply variant

When the user identifies a role as a LinkedIn Easy Apply posting, the only
advisory work is: (a) deliver the standard verdict; (b) if Apply or
Borderline, state whether to use a limited "Top Application" designation
(reserve these for strong-fit Apply verdicts, not Borderlines or domain-gap
roles — the exact monthly count is instance-specific config, not fixed here).
No cover-letter step unless asked. Log the application as Applied, since
LinkedIn Easy Apply is trivial to submit.

## Applications tracking (unconditional)

Any role that proceeds to a letter or an application is written as a pending
row directly to the applications tracker (the `applications` table in
`data/*/personal/db/personal.db`, via `src/tools/personal_db/personal_write.py`
`add-application`). There is no separate state-file "pending-updates" holding
area — the tracker itself is the record. Track these as they occur; don't rely
on the user to flag them. The tracker's own schema file documents its full column set
(including a finer-grained fit rating and a gap-keyword taxonomy beyond this
playbook's own Apply/Borderline/Skip triage word) and is authoritative for
populating those fields — read it rather than guessing a value, and treat its
gap-keyword list as a living taxonomy to extend, not a fixed enum.

Do not log Skips — re-evaluating a re-pasted JD is cheap and reaches the same
verdict, so logging Skips only clutters the tracker. State the verdict in
chat and move on. (The tracker's schema still reserves a value for the rare
case a Skip is worth a pipeline record anyway — that's an exception, not the
default.)

When an application proceeds and the user confirms they applied in the same
session, archive the JD text they pasted as plain text, named by company and
a short role label, into `applications/jds/` in the user's own data root.
This preserves the posting after the page goes offline. Archive only from JD
text pasted in the current session — never browse for a JD, and JDs pasted in
past sessions can't be reconstructed after the fact. If only a URL is
available with no pasted text, log the cleaned URL and note that no JD text
was available to archive.

`applications/jds/` is the curated archive for JDs behind a proceeded
application only. It is distinct from the local scraper pipeline's own raw,
by-date working output (any JD it touched, successful or not, pending
triage) — see `tools/jd_scraper/README.md`. Don't confuse the two or try to
reconcile them; they serve different stages of the same pipeline.

Rows the applications tracker marks as referral-gated (submitted through, or
paused for, a personal referral) stay in the tracker for pipeline visibility
only — never surface them as follow-up action items in session or in a
scheduled briefing; the user can't accelerate them by being reminded.

## Web research policy

Never self-initiate web searches or browse URLs in this workflow. URLs the
user provides are for stripping tracking parameters and logging the clean job
ID only; treat them as opaque strings. When research would materially improve
triage or the letter (company identity disambiguation, culture signals, the
letter's hook), hand the user a research prompt to run externally (see
`cover_letter.md`) rather than attempting it here.
