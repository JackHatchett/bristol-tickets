---
name: session-closure
description: Opens a job-hunting session with a readout of where the applications stand and closes it with the tracker left correct. Use at the start and the end of a session spent on job applications.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: career_coach
  bristol.scripts: src/tools/personal_db/personal_write.py
---
# session-closure

What career_coach does at the open and close of a session, on top of the shared
mechanics in `src/skills/manage-tickets/SKILL.md` §Session closure.

## Session start echo

**Open with a short tracking block before anything else**, sourced from
`agent_status.py career_coach`: the active epic's name and its ordered task
queue. That gives the user a one-glance continuity check without re-reading
anything.

## Session closure

Triggered when the user indicates the session is ending, or at the natural end
of an evaluation, letter or resume workflow.

1. **Sweep the session for novel experience, skills and corrections** — an ATS
   keyword the user confirmed as real, a voice nuance from a redraft, a newly
   discovered banned phrasing. Format each as a clean, ready-to-paste block and
   name which context module or blacklist file it belongs in.
2. **Reflect everything that changed into this agent's epic and cards**, per
   `src/skills/manage-tickets/SKILL.md` §Session closure.

## The applications tracker is a scoped exception

Application rows live in the `applications` table of
`data/*/personal/db/personal.db`, written through
`src/tools/personal_db/personal_write.py` (`add-application`,
`update-application`). **Keep logging applications there as usual** — the
charter grants that record its own home, and nothing in this skill's
closure steps touches it.
