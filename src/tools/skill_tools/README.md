# Skill Tools

The loader for Agent Skills — the open format at
`github.com/agentskills/agentskills`, where a skill is a directory holding a
`SKILL.md` whose YAML frontmatter carries `name` and `description`. This file
owns the *mechanism*: the two roots, the disclosure contract, and the
quarantine. Converting a Bristol file into a skill is
`src/playbooks/skill_conversion.md`. Style contract:
`src/templates/identity_template.md` §The governing-doc style contract.

## Two roots

- **Native — `src/skills/`.** Bristol's own converted playbooks and protocols,
  published with the code and maintained by `chief_of_staff`.
- **Installed — the path declared at `skills.install_dir` in config**, resolved
  through `config_tools/data_paths.py` and git-ignored. Third-party skills only.

Neither root is created before a write, and finding one absent is a normal first
state — `src/tools/config_tools/README.md` §A missing data location is created,
never an error.

## Invariants

- **Progressive disclosure is enforced, not advised.** `list` reads each
  `SKILL.md` only as far as the frontmatter's closing delimiter; `view` is the
  only command that loads a body.
- **A skill's name is its directory name.** The specification requires the two
  to match, and the roots are flat.
- **A third-party skill lands in `<install_dir>/.quarantine/` and is invisible
  to `list` and `view` until `trust` promotes it.** Installing shows the file
  inventory with sizes and hashes, marking every file that is executable code.
- **Nothing here runs a skill's code.** `audit` prints it; a session reads it and
  decides.
- **No personal data.** Every path comes from config or from the project root
  marker.

## skills.py

```
python3 skills.py list
python3 skills.py view <name>
python3 skills.py install <repo-url> <path-in-repo> [--name NAME]
python3 skills.py audit <name>
python3 skills.py trust <name>
```

- **`list`** — every loadable skill as name, origin and description, plus a
  closing line naming anything quarantined.
- **`view`** — one skill's `SKILL.md` in full. This is the on-demand load.
- **`install`** — shallow-clones the hub repository into a temporary directory,
  copies the named skill into quarantine, and prints the inventory. It refuses a
  name already present in either root.
- **`audit`** — the skill's `SKILL.md` followed by the full text of every script
  it carries.
- **`trust`** — moves a quarantined skill into the install root, where `list`
  and `view` can reach it.
