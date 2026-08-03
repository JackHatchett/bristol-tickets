# crew_dispatch — writers_room playbook

Triggered when the user wants to start or continue work with an external
advisory crew role. This is the decision procedure for when and what to package,
and how to reconcile a reply; the envelope format and the folder-drop courier
are `protocols/writers_room/gemini_crew_handoff.md`.

## The channel is the board

A dispatch is a ticket. **The JSON envelope is a payload file**, existing only
because an external Gem cannot read `tickets.db` — bytes to show an outsider,
never a message between sessions and never a place work state lives.

- **Open or update the card that owns the exchange before writing any
  envelope** — `ticket_write.py add-task --assignee writers_room --reporter
  writers_room` — and name the envelope file in its description. The ticket is
  the only record that a dispatch is outstanding.
- **Never scan `handoff/` to discover what is in flight.** An empty board means
  nothing is in flight.

## Dispatching an outbound brief

1. **Confirm which role the work needs.** Editor for drafting and coaching,
   Grammatizator for voice-sample scouting, Proofer for read-and-react critique.
   Each role's file in `protocols/writers_room/crew_roles/` declares its
   capabilities and status.
2. **Assemble the Reference Pack** — file and section pointers scoped tightly to
   what the job needs, never the whole project. Include the voice-profile
   pointer for any prose-drafting job.
3. **Name explicit constraints**: the active project's content-rules file, what
   the role may invent freely, and what it must never touch — settled beats,
   settled terms.
4. **Default to `delivery: pointers`.** Use `delivery: embedded`, with verbatim
   excerpts inline, only where the counterpart is a no-repo-access Gem the user
   must paste content into by hand.
5. **Write the envelope as a new file in `handoff/to-gemini/`**
   (`YYYY-MM-DD-HHMM-quartermaster-to-<role>.json`), validated against
   `protocols/writers_room/handoff.schema.json`, and record its filename on the
   ticket.
6. **Tell the user the brief is ready**, pointing them at
   `protocols/writers_room/gemini_bootstrap.md` where the counterpart needs
   bootstrap instructions to paste into the external client.

**A brief is onboarding, not a task order.** It does not commit the external
role to a mode; that choice belongs to the user and the role, worked out in
their session.

## Receiving a reply

1. **Read the envelope the ticket names.** Never take the latest file by name —
   that is deriving state from a folder listing. **Where the named file is
   absent, say so on the ticket and stop.**
2. **Route it into `story_proposals.md`.** Every delta or specimen is a
   proposal, reconciled and summarized to the shared agent-output dir for the
   user to fold in, however well-formed the envelope is.
3. **Route a Grammatizator reply — a Specimen Pack — into
   `voice_distillation.md` instead.** It is raw material for the distillation
   loop rather than a story delta.
4. **Move the ticket to `doing` and record the reconciliation as a comment on
   it. Never open a second card for the reply half of an exchange.** A
   superseded envelope may be deleted; `handoff/` is not an audit trail and
   holds no authority.

## Failure modes

- **The envelope the ticket names is absent** → say so plainly on the ticket.
  Do not guess at what the reply would have contained, and do not substitute a
  different file found in the folder.
- **The envelope fails schema validation** → tell the user the exchange needs
  redoing from the external side. Never hand-patch it into something that
  parses.
- **A reply proposes something outside its granted constraints**, such as an
  Editor envelope touching a `do_not_touch` item → flag it as a conflict during
  reconciliation; never silently drop or silently apply it.
