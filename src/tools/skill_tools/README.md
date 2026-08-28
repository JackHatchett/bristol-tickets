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
- **An installed skill carries its provenance in a `.origin.json` beside its
  `SKILL.md`** — repository, path inside it, resolved commit, licence, and where
  that licence was read from. Written inside the skill directory so the record
  moves with it through quarantine and trust and cannot orphan; dotted, so a
  client reading the skill by the specification never sees it. It is written
  only under the git-ignored install root, never into `src/skills/`.
- **A licence is recorded as it is found, never detected.** The skill's own
  frontmatter first, then a licence file beside the skill, then one at the
  repository root; a file is recorded by its own first line. A source stating no
  licence anywhere is recorded as `absent`, which is a different fact from a
  blank field.
- **Nothing here runs a skill's code.** `audit` scans and prints it; a session
  reads it and decides. A report never promotes a skill: `trust` is a separate
  command a person runs, and it consults no scanner.
- **No personal data.** Every path comes from config or from the project root
  marker.

## skills.py

```
python3 skills.py list
python3 skills.py view <name>
python3 skills.py install <repo-url> <path-in-repo> [--name NAME]
python3 skills.py convert <file.md> [--name NAME] [--description TEXT]
python3 skills.py audit <name>
python3 skills.py trust <name>
```

- **`list`** — every loadable skill as name, origin and description, plus a
  closing line naming anything quarantined. Origin is `native`, or the
  repository and commit a skill was installed from; a skill carrying no record
  reads as its root, which is all that is known about it.
- **`view`** — one skill's `SKILL.md` in full. This is the on-demand load.
- **`install`** — shallow-clones the hub repository into a temporary directory,
  copies the named skill into quarantine, and prints the inventory. It refuses a
  name already present in either root.
- **`convert`** — writes a foreign markdown definition into quarantine as a
  skill. A subagent definition, a slash command and a prompt-pack entry are one
  object, a markdown body under frontmatter, and the half of that frontmatter
  which routes work — `tools`, `model`, a client's own extensions — has no reader
  here, because a Bristol session's model and tool surface belong to its host.
  `name`, `description` and `license` cross; everything else is dropped and named
  in the output. A source stating no description is refused rather than given
  one, since a skill without a trigger never routes; `--description` supplies it.
  **The skills the source declares it depends on are named too**, from its
  frontmatter's `skills`, `required_skills`, `dependencies` or `requires` key,
  so they can be installed instead of being noticed later; a dependency stated
  in the body alone is not a declaration and the output says as much.
- **`audit`** — the skill's provenance record, then a scan of its code, then its
  `SKILL.md`, then the full text of every script it carries.
- **`trust`** — moves a quarantined skill into the install root, where `list`
  and `view` can reach it.

## The scanner

`audit` runs **bandit**, invoked as a module of the interpreter running
`skills.py` so it is found wherever that interpreter's packages are. Bristol
never installs it, and an interpreter without it produces a report saying so
above the source, which is then the whole of the evidence.

- **What it checks.** Python source, parsed to an AST and matched against its
  published tests for known-dangerous calls: a shell in `subprocess`, `eval` and
  `exec`, `pickle` and `yaml.load` over untrusted bytes, weak hashes and ciphers,
  credentials written into the source, disabled certificate verification,
  predictable temporary files.
- **What it does not.** Any language but Python, so a skill's shell, JavaScript,
  Ruby and PowerShell go unread and the report names them. Dataflow across
  files. Intent — a call it names may be the right one and a call it passes may
  be the wrong one. Code that is obfuscated, encoded, or fetched at run time,
  which reads to it as ordinary Python.
- **A finding is a place to look, not a verdict**, and a clean report says only
  that these tests matched nothing.
