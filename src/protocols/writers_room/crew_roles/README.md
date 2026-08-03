# crew_roles/

One profile per external advisory crew role, in a common format. **A role
profile is project-agnostic**: the same roles serve every active project, and a
project's own content rules reach the role through its brief
(`../gemini_crew_handoff.md`), never through this folder.

| Role | Runs on | Writes to repo | What it does |
|---|---|---|---|
| Quartermaster | `writers_room` itself | Yes | Reasons world and plot, keeps the story wiki coherent, hosts, distils voice, and summarizes accepted changes for the user to fold in. Its identity is `agent_identities/writers_room.md`. |
| [Editor](editor.md) | External | No — proposes | Drafts, coaches and beat-engineers prose, handing back deltas |
| [Grammatizator](grammatizator.md) | External | No — returns a pack | Scouts voice specimens from the author's prose |
| [Proofer](proofer.md) | External | No — comments | Reader-tests and AI-style-scans finished prose |

Each profile's capability header declares that role's permissions, modes and
status.

## The model

- **One external role per session.** The human tells the external client which
  role to be at session start, and it adopts that profile.
- **Only `writers_room` writes to the repo.** Every other role is advisory and
  proposes through a Handoff Envelope; every change funnels through
  `writers_room`, which reconciles it and summarizes it to the shared
  agent-output dir for the user to fold into the wiki.
- **This directory is protocol material, not an agent roster.** These roles have
  no board epic and no identity in this framework — they are what an external AI
  is briefed to become for one session, per `../gemini_bootstrap.md`.
