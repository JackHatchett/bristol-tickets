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
- **Every session runs `list` at start and `view` only when a task matches a
  description** — `src/app.md` Phase 2 owns that rule. It is what makes an
  installed skill reachable, and the reason `list`'s output is one line each.
- **A skill's name is its directory name.** The specification requires the two
  to match, and the roots are flat.
- **Attachment orders what a session matches first and fences nothing off.** A
  per-agent allowlist would be a smaller system than the one that exists, where
  any agent may load any skill; `list --agent` therefore prints every loadable
  skill and marks the attached ones rather than filtering.
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
- **A surface over this loader routes to the same decision and never makes its
  own.** Bristol Tickets' Skills tab performs the mechanical half of an import
  and files the judgment as a card, because judging a skill is a read of its
  body and every script it carries, and an application cannot read.
- **Nothing here runs a skill's code.** `audit` scans and prints it; a session
  reads it and decides. A report never promotes a skill: `trust` is a separate
  command, and it consults no scanner.
- **`chief_of_staff` decides what a session may load, and the board carries the
  decision.** The judgment follows a read of the body and of every script, never
  a report; the procedure and its four cases are
  `src/skills/importing-a-skill/SKILL.md`. A skill that does not clear stays in
  quarantine and the card returns to the user with what stopped it — a refusal
  the user may overrule, which is the only part of importing that is theirs.
- **Capability is judged here; authority is granted by the user.** A skill is a
  procedure a session may load, and judging one is reading. A mandate is the
  grant of power itself and is authored rather than imported —
  `src/templates/identity_template.md` §What of an agent can be imported.
- **No personal data.** Every path comes from config or from the project root
  marker.

## skills.py

```
python3 skills.py list [--agent <slug>] [--json]
python3 skills.py view <name>
python3 skills.py install <repo-url> <path-in-repo> [--name NAME]
python3 skills.py convert <file.md> [--name NAME] [--description TEXT]
python3 skills.py audit <name>
python3 skills.py trust <name>
python3 skills.py attach <name> --agent <slug>
python3 skills.py detach <name> --agent <slug>
python3 skills.py remove <name>
```

- **`list`** — every loadable skill as name, origin and description, plus a
  closing line naming anything quarantined. **`--json`** returns every skill
  including the quarantined ones, what each carries, and each agent's
  attachments, as data. It is one read, which is what stops a surface built on
  it and a session reading the same loader from disagreeing about a name, a
  description or an origin. `--agent <slug>` puts that agent's
  attached skills first and marks them. Origin is `native`, or the
  repository and commit a skill was installed from; a skill carrying no record
  reads as its root, which is all that is known about it.
  - **A `--json` record carries its three facts already worded** —
    `said_origin`, `said_contents`, `said_holders`, beside the raw `root`,
    `files`, `scripts` and `holders` they are built from. A surface shows the
    worded form so the app, a detail view and an import report tell a reader the
    same fact in the same words; the raw fields are for anything that has to
    count or compare, alongside `path`, `file_list` and `source_url` — the
    skill's directory, everything in it, and the web address of the exact
    commit and folder it came from, which is what a surface needs to open a
    skill rather than only name it. The wording is `origin_phrase`, `contents_phrase` and
    `holders_phrase`, and it is written for someone who has never seen this
    system: a skill came with Bristol or names where it was downloaded from, a
    count agrees with the noun beside it, and a skill carrying code does not
    read like one carrying none.
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
  and `view` can reach it. It moves a directory and asserts nothing; what makes
  the move safe is the read that preceded it.
- **`install` closes with a compatibility note where the skill's own
  frontmatter declares something with no reader here** — environment variables
  it expects credentials for, and the Hermes toolsets it gates or offers itself
  as a fallback for. Each says what will happen and names what it found. It is
  a statement, never a gate: a skill whose gate is inert here may still carry a
  body worth reading, and refusing it would decide something that is the
  person's to decide. A skill carrying only fields the specification defines,
  or declaring one of those keys and naming nothing under it, prints no note.
- **`remove`** — delete an installed or quarantined skill and detach it from
  every agent that held it. The directory goes before the detachments, so a
  filesystem that refuses the delete leaves the attachments intact rather than
  leaving an agent naming a skill that is gone. It refuses a native skill: those
  are source under version control, and removing one is an edit to the
  repository.
- **`attach` / `detach`** — add or remove one skill name in
  `agents.<slug>.skills`, written through `config_tools/write_config.py`. The
  attachment is a name in the agent's config entry and never a copy of the
  skill, so one skill serves as many agents as name it and detaching from one
  leaves the others as they were. `attach` refuses a name `list` does not show,
  which is what makes a quarantined skill unattachable until it is trusted.

## Where a skill comes from

`install` takes the address a repository shows while you are looking at a
skill's folder, so the whole of the discovery step is finding a folder in a
browser. These are the places worth browsing, each with what reviews it, because
nothing here is reviewed by Bristol.

| Hub | What it holds | What reviews it | Address |
| --- | --- | --- | --- |
| Anthropic's own | The specification, a skill template, and the skills behind a production assistant's document handling | Nothing published; it is one vendor's repository | `github.com/anthropics/skills` |
| The specification | The Agent Skills standard and its reference material, not a catalogue | Its own contribution process | `github.com/agentskills/agentskills` |
| awesome-hermes-skills | 258 entries — 72 built into Hermes, 101 shipped-but-disabled, 85 third-party | Curated by hand, and it says it is not an audit | `github.com/ZeroPointRepo/awesome-hermes-skills` |
| Nous's optional catalogue | ~150 skills in 22 categories, shipped with Hermes and inactive until installed | Nothing stated | `hermes-agent.nousresearch.com/docs/reference/optional-skills-catalog` |
| skills.sh | The largest directory, listing skills by their GitHub repository | A security-audit section, with no stated process | `skills.sh` |

**The claims about review, in their own words.** awesome-hermes-skills states
that "skills in this list are curated, not audited" and that maintainers can
change them after they appear, and it accepts a submission on four mechanical
tests — a working `SKILL.md`, commits in the last six months, a README with a
one-line install, and not already listed. Nous's optional catalogue states
nothing about review; its skills ship inside Hermes rather than being fetched.
Anthropic's repository carries a demonstration-and-education disclaimer and no
third-party submission process. The specification repository is a standard, not
a catalogue, and reviews contributions to itself.

**Scale and trust run in opposite directions**, which is the reason the two
smallest entries above are the two worth reading first. The figures behind that,
and Snyk's ToxicSkills population study, are the ecosystem survey in the user's
notebook rather than repeated here.

**Licence is a property of the skill, not of the hub.** awesome-hermes-skills is
CC-BY-4.0 as a list while each entry carries its own; the specification
repository is Apache-2.0 for code and CC-BY-4.0 for documentation; Anthropic's
repository is Apache-2.0 for most skills and source-available rather than open
source for the four document skills. `install` records what it finds beside the
skill and never infers one.

## What a session holds, and what it defers

- **At session start, one line per loadable skill** — its name, its origin and
  the sentence saying when it applies, the agent's own first. That is the whole
  of the standing cost, and it does not grow with what a skill contains.
- **On a match, one body, through `view`.** Every other body stays unread, and
  the session names the skill it opened.
- **Never a skill's scripts, references or assets.** A skill's own body says
  when to open one.

Attachment does not shrink that index, and is not what controls the cost.
Reaching a skill no agent attached has to stay possible, so every loadable skill
is listed whichever agent is running. What attachment buys is order — a session
matches its own set first and goes past it only when nothing there fits — and
what keeps the standing cost to one line each is progressive disclosure, a
property of `list`.

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
