# session_closure — career_coach playbook

What this agent does at the open and close of a session, on top of the shared
mechanics in `src/playbooks/manage_tickets.md` §Session closure.

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
   `manage_tickets.md` §Session closure.

## The applications tracker is a scoped exception

Application rows live in the `applications` table of
`data/*/personal/db/personal.db`, written through
`src/tools/personal_db/personal_write.py` (`add-application`,
`update-application`). **Keep logging applications there as usual** — the
charter's §2.2 grants that record its own home, and nothing in this playbook's
closure steps touches it.
