# crew_roles/ — external advisory role profiles

One profile per external crew role, same format. These are project-agnostic:
the same roles serve every active project. A role profile never contains a
particular project's content rules — those live in that project's own
content-rules file and are handed to the role in its brief (see
`../gemini_crew_handoff.md`).

| Role | Runs on | Writes to repo? | What it does |
|---|---|---|---|
| Quartermaster | `writers_room` itself | **Yes** | Reasons world/plot, keeps the story wiki coherent, hosts, distils voice, and summarizes accepted changes for the user to fold in. Not an external role — this is the agent's own identity; see `agent_identities/writers_room.md`. |
| [Editor](editor.md) | External (usually Gemini) | No (proposes) | Drafts, coaches, beat-engineers prose; hands back deltas |
| [Grammatizator](grammatizator.md) | External (usually Gemini) | No (returns pack) | Scouts voice specimens from the author's prose |
| [Proofer](proofer.md) | External, reserved | No (comments) | Reader-tests + AI-style scans finished prose. Not yet built. |

## The model

- **One external role per session.** At session start, the human tells the
  external client which role to be, and it adopts that profile.
- **Only `writers_room` writes to the repo.** Editor, Grammatizator, and
  Proofer are advisory — they propose through Handoff Envelopes
  (`../gemini_crew_handoff.md`); every change funnels through `writers_room`,
  which reconciles it and summarizes it to the shared agent-output dir for the
  user to fold into the wiki. No 'canon' concept, no ratification gate.
- **This directory is protocol material, not a separate agent roster.**
  These three roles have no roadmap epic and no identity in this
  framework — they are what an external AI is briefed to become for one
  session, per `../gemini_bootstrap.md`.
