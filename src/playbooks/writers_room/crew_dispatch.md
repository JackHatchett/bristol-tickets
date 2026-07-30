# crew_dispatch.md — writers_room playbook

**Triggered:** when the user wants to start or continue work with an
external advisory crew role (Editor, Grammatizator, or — once built —
Proofer). Mechanics of the envelope and the folder-drop courier are in
`protocols/writers_room/gemini_crew_handoff.md`; this playbook is the
decision procedure for *when* and *what* to package, and how to reconcile a
reply.

## The channel is the board

A dispatch is a **ticket**. The JSON envelope is a payload file that exists
only because a Gemini Gem cannot read `roadmap.db` — it is bytes to show an
outsider, never a message between sessions and never a place work state lives.

Before writing any envelope, open or update the card that owns the exchange
(`roadmap_write.py add-task --stage active --assignee writers_room
--reporter writers_room`) and name the envelope file in its description. The
ticket is the only record that a dispatch is outstanding. Never scan
`handoff/` to discover what is in flight — an empty board means nothing is in
flight.

## Dispatching an outbound brief

1. Confirm which role the work needs (Editor for drafting/coaching,
   Grammatizator for voice-sample scouting, Proofer once built for
   read-and-react critique).
2. Assemble the Reference Pack: file + section pointers scoped tightly to what
   the job actually needs — not the whole project. Include the voice
   profile pointer for any prose-drafting job.
3. Name explicit constraints: the active project's content-rules file,
   what the role may invent freely, and what it must never touch (settled
   beats, settled terms).
4. Default to `delivery: pointers`. Use `delivery: embedded` (verbatim
   excerpts inline) only when the counterpart is a no-repo-access Gem the
   user has to paste content into by hand.
5. Write the envelope as a new file in `handoff/to-gemini/`
   (`YYYY-MM-DD-HHMM-quartermaster-to-<role>.json`), validated against
   `protocols/writers_room/handoff.schema.json`, and record its filename on
   the ticket.
6. Tell the user the brief is ready and, if the counterpart needs bootstrap
   instructions, point them at `protocols/writers_room/gemini_bootstrap.md`
   to paste into the external client.

A brief is onboarding, not a task order — it does not commit the external
role to a specific mode. That choice belongs to the user and the role,
worked out in that external session.

## Receiving a reply

1. Read the envelope **the ticket names**. Do not take "the latest file by
   name" — that is deriving state from a folder listing. If the named file is
   absent, say so on the ticket and stop.
2. Route it into `story_proposals.md`'s procedure — every delta or
   specimen is a proposal, reconciled and summarized to the shared
   agent-output dir for the user to fold in, regardless of how well-formed the
   envelope is.
3. A Grammatizator reply (a Specimen Pack) routes instead into
   `voice_distillation.md` — it isn't a story delta, it's raw material for
   the distillation loop.
4. Move the ticket to `doing` and record the reconciliation as a comment on
   it. Never open a second card for the reply half of an exchange.
   Superseded envelopes may be deleted; `handoff/` is not an audit trail and
   holds no authority. The board is the record.

## Failure modes

- **The envelope the ticket names is absent** when one was expected: say so
  plainly on the ticket; don't guess at what the reply would have contained,
  and don't substitute a different file you found in the folder.
- **Envelope fails schema validation:** don't hand-patch it into something
  that parses — tell the user the exchange needs to be redone from the
  external side.
- **A reply proposes something outside its granted constraints** (e.g. an
  Editor envelope touching a `do_not_touch` item): flag it as a conflict in
  the reconciliation step; don't silently drop or silently apply it.
