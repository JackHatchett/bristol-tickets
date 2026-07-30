# Project Intake — client_services Playbook

## Purpose
Onboard a new client, or a new project for an existing client, into a
consistent structure so any future session can resume it without a
briefing.

## Preconditions
- The user has confirmed the client's identity/contact info and the
  project's scope, deadline (or open-ended), and domain before any file is
  created.
- A data root for this instance's clients exists (`data/*/clients/`,
  resolved via `/config`).

## Procedure

1. **Intake checklist** — confirm before scaffolding anything:
   - Client name + contact confirmed
   - Client profile exists (create if new — see step 2)
   - Project name/slug agreed
   - Deadline confirmed, or explicitly noted as open-ended
   - Domain/type of project established (grant, creative, technical,
     research, etc.)
   - Deliverables defined — what does "done" look like?
   - The user's role defined (drafter, advisor, researcher, etc.)
   - Client's own responsibilities defined (approvals, submissions,
     credential-gated actions)

2. **Client registry** — if the client is new:
   - Create `<client_slug>/profile.md` (contact, relationship, notes,
     client-since date) in the clients data root.
   - Add the client to `registry.md`.
   If the client already exists, skip to step 3.

3. **Project scaffold** — create the project's own working folder (location
   resolved via `/config`, not hardcoded here) with:
   ```
   <project_name>/
     CLAUDE.md           — project-specific instructions (domain, schema, phases)
     project_state.md    — current phase, gathered data, drafted sections, next steps
     README.md           — one-paragraph summary
     drafts/              — working drafts, one file per section/component
     final/                — finalized deliverables ready for submission/delivery
     archive/              — superseded versions; nothing deleted
     docs/                 — reference materials, RFPs, briefs, external documents
   ```
   Adjust folder names for the project's domain (e.g. `budget/` for a grant,
   `chapters/` for a creative project).

4. **Seed `project_state.md`** with: client (pointer to their profile),
   phase (`open` + current phase name), deadline, a one-paragraph summary of
   what this project is and what the user is helping with, a session log
   starting with the creation date, and a next-steps list.

5. **Seed the project's own `CLAUDE.md`** with: purpose, an instruction to
   always read `project_state.md` first, the project's own phase list,
   deliverables, and any domain-specific conventions (e.g. drafts vs. final
   folder rules).

6. **Cross-reference** — add the new project to the client's own
   `<client_slug>/projects.md` and to `registry.md`.

## Tools Used
None — this is a file-scaffolding procedure, not a script.

## Logging Requirements
Log the new client/project via `tools/roadmap_tools/roadmap_write.py
add-task` against this agent's own epic, not a separate tracking file.

## Failure Modes
- Client identity or project scope unconfirmed → stop and ask; do not
  scaffold a guessed structure.
- A project's domain doesn't fit the standard `drafts/final/archive/docs/`
  shape → adjust folder names, but keep the same underlying phases
  (`project_state.md`, one source of truth per project).

## Human Audit Notes
Periodically check that every project referenced in `registry.md` still
resolves to a real folder, and that closed/archived projects are actually
marked as such in both the client's own `projects.md` and the registry.
