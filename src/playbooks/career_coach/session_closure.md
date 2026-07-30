# Session Closure — career_coach playbook

career_coach has its own tagged epic in the shared `tickets.db`
(`epic.owner = 'career_coach'`; see
`src/tools/ticket_tools/ticket_write.py` and `agent_status.py`). Session
start and close both read/write that epic and its tasks, not `STATE.md` /
`CHANGELOG.md` in the personal data root — those two files are retired as
live state trackers. They're kept on disk as historical record
of the pre-tickets-db tracking era; don't overwrite or append to them.

## Session start echo

At the start of any session (per the charter's standard Phase 3 pattern —
`agent_status.py career_coach`, not `cos_status.py`), open with a short
tracking block sourced from that snapshot before doing anything else: the
active epic's name and its ordered task queue. This
gives the user a one-glance continuity check without re-reading anything.

## Session closure

Trigger: the user indicates the session is ending, or the natural end of an
evaluation/letter/resume workflow.

1. Sweep the session for novel experience, skills, or corrections (e.g. an
   ATS keyword the user confirmed as real, a voice nuance from a redraft, a
   newly discovered banned phrasing). Format these as clean, ready-to-paste
   blocks, and note which context module or blacklist each belongs in — this
   step is unchanged, since it targets the foundation/context modules, not
   state tracking.
2. For anything that changed this session — a task finished, a new
   follow-up surfaced, priorities shifted — update the tickets db directly
   via `ticket_write.py`: mark finished tasks done, `add-task --epic-id
   <career_coach's epic id>` for new follow-ups, and adjust `next_action` on
   the epic if it changed. Don't invent a parallel tracking file for this.
3. Leave nothing in prose. Anything still mid-flight ends the session as a
   `doing` card on the active board — high `priority`, `assignee` set — and
   anything worth saying about it goes in one short `add-issue-log` comment on
   that card. There is no handoff note; the card is the handoff.

Applications-tracker rows are a separate, explicitly scoped exception to all
of the above — see the charter's §2.2 applications-tracker paragraph. They
live in the `applications` table of the shared
`data/*/personal/db/personal.db`, written via
`src/tools/personal_db/personal_write.py` (`add-application` /
`update-application`). Keep logging new
applications there as usual; this playbook's session-closure rules don't
touch that record.
