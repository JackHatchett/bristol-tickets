# playbooks/_shared/

The procedures that serve more than one agent. Maintained by `chief_of_staff`;
loading is `src/templates/identity_template.md` §Boundaries and coordination.

## Index

Each of these procedures is a skill folder under `src/skills/`, and a skill's
own `description` is its index entry. Read the set with:

```
python3 src/tools/skill_tools/skills.py list
```

`view <name>` is the on-demand load of one body —
`src/tools/skill_tools/README.md`. Converting a file into that shape is
`src/playbooks/skill_conversion.md`.

## What belongs here

- **Promote a procedure here once a second agent genuinely reuses the same
  shape.** A procedure only one agent runs stays in that agent's folder.
- **Keep a promoted procedure free of its origin domain.** A capability that
  still names one agent's subject matter has been moved rather than
  generalized.
