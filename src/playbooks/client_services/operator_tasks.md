# Operator Tasks — client_services Playbook

## Purpose
Enumerate every action in a client engagement that only the user can
perform — credentials, direct contact, submission, git. Claude drafts;
these are never Claude's to execute.

## Preconditions
None — this applies to every client engagement, at every phase.

## Procedure

1. **Client onboarding.** Before a profile is created, the user must confirm
   the client's name, relationship, and contact information, plus the
   project's scope and any hard deadline.

2. **Deliverable submission.** Claude drafts; the user submits. For any
   deliverable going to an external party (a portal, email, form), the user
   must review the project's `final/` contents, submit using their own
   credentials, and confirm back to Claude that submission is complete so
   `project_state.md` and the registry can be updated.

3. **External accounts and portals.** Claude cannot log in to grant portals,
   institutional systems, email accounts, or any external service on a
   client's behalf. The user handles every credential-gated action.

4. **Client communication.** Claude does not contact clients. If Claude
   drafts an email or message for a client, the user sends it.

5. **Git.** At the end of a session with file changes, Claude proposes a
   commit message; the user runs the actual `git add` / `git commit` in the
   client data root.

## Tools Used
None.

## Logging Requirements
None beyond the standard session-end board update — this playbook is a
boundary reference, not something that produces its own artifacts.

## Failure Modes
If Claude finds itself about to perform any action listed above (logging
into a portal, emailing a client, running a destructive git command),
stop and hand the concrete action back to the user instead.

## Human Audit Notes
Periodically confirm that every "submitted"/"complete" project in the
registry actually reflects a real submission the user performed — this
playbook's whole point is that Claude cannot verify that step itself.
