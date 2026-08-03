# project_intake — client_services playbook

Onboard a new client, or a new project for an existing client, into a consistent
structure any later session can resume without a briefing.

## Preconditions

- **The user has confirmed the client's identity and contact info**, and the
  project's scope, deadline (or that it is open-ended) and domain.
- **A clients data root exists** at `data/*/clients/`, resolved via `/config`.

## Procedure

1. **Confirm the intake checklist before scaffolding anything:**
   - client name and contact confirmed
   - client profile exists, or is created in step 2
   - project name and slug agreed
   - deadline confirmed, or explicitly noted as open-ended
   - domain established (grant, creative, technical, research)
   - deliverables defined — what "done" looks like
   - the user's role defined (drafter, advisor, researcher)
   - the client's own responsibilities defined (approvals, submissions,
     credential-gated actions)

2. **Create the client record if the client is new.** `<client_slug>/profile.md`
   in the clients data root, carrying contact, relationship, notes and
   client-since date, plus an entry in `registry.md`. Skip to step 3 for an
   existing client.

3. **Scaffold the project folder**, its location resolved via `/config`:

   ```
   <project_name>/
     CLAUDE.md           — project-specific instructions (domain, schema, phases)
     project_state.md    — current phase, gathered data, drafted sections, next steps
     README.md           — one-paragraph summary
     drafts/             — working drafts, one file per section
     final/              — finalized deliverables ready for submission
     archive/            — superseded versions
     docs/               — reference materials, RFPs, briefs, external documents
   ```

   **Adjust folder names to the domain** — `budget/` for a grant, `chapters/`
   for a creative project — and keep the same underlying phases and one source
   of truth per project.

4. **Seed `project_state.md`** with the client (a pointer to their profile), the
   phase (`open` plus the current phase name), the deadline, a one-paragraph
   summary of the project and the user's part in it, a session log opened at the
   creation date, and next steps.

5. **Seed the project's `CLAUDE.md`** with its purpose, an instruction to read
   `project_state.md` first, its phase list, its deliverables, and any
   domain-specific conventions.

6. **Cross-reference the new project** into the client's `<client_slug>/
   projects.md` and into `registry.md`.

## Failure modes

- **Client identity or project scope unconfirmed** → stop and ask; never
  scaffold a guessed structure.

## Audit

**Check periodically that every project in `registry.md` resolves to a real
folder**, and that a closed or archived project is marked as such in both the
client's `projects.md` and the registry.
