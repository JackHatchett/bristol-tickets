---
name: operator-tasks
description: Lists the steps in a client engagement that only the user can carry out, so a session drafts them and stops rather than acting. Use at any point in a client engagement, to see what waits on the user.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: client_services
---
# operator-tasks

Every action in a client engagement that only the user can perform. This agent
drafts; none of these is its to execute. Applies at every phase of every
engagement.

- **Client onboarding.** The user confirms the client's name, relationship and
  contact information, plus the project's scope and any hard deadline, before a
  profile is created.
- **Deliverable submission.** The user reviews the project's `final/` contents,
  submits under their own credentials, and confirms back so `project_state.md`
  and the registry can be updated.
- **External accounts and portals.** The user handles every credential-gated
  action. **Never log in to a grant portal, an institutional system, an email
  account or any external service on a client's behalf.**
- **Client communication.** **Never contact a client.** A drafted email or
  message is sent by the user.
- **Git.** Propose a commit message at the end of a session with file changes;
  the user runs `git add` and `git commit` in the client data root.

**Stop and hand the concrete action back the moment you are about to perform one
of these** — logging into a portal, emailing a client, running a destructive git
command.

**Confirm periodically that every project the registry marks submitted or
complete reflects a real submission the user performed.** That step cannot be
verified from inside a session, which is why the whole list exists.
