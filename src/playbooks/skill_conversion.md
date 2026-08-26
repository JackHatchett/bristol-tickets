# skill_conversion — Playbook

Convert a Bristol governing file into a skill folder under the Agent Skills
specification, so that a playbook and a skill are one object under one name, and
name the files that are not skills at all. The specification is at
`github.com/agentskills/agentskills`. Style contract:
`src/templates/identity_template.md` §The governing-doc style contract.

## Preconditions

- **The file is a playbook or a protocol.** Everything else is out of scope —
  §The mapping.
- **The file already satisfies the style contract.** A conversion moves a body;
  it does not rewrite one.

## The mapping

| Bristol object | Under the specification |
| --- | --- |
| `src/playbooks/**/*.md` | one skill |
| `src/protocols/_shared/*.md` | one skill |
| `src/protocols/<agent>/*_bridge.md` | `references/<agent>.md` inside that archetype's skill |
| `src/templates/*.md` | `assets/` inside the skill whose procedure writes that file |
| `src/tools/**` | not moved; the skill body names the command line |
| a folder `README.md` | not a skill; a skill's index is its own `description` |
| `src/agent_identities/*.md` | not a skill |
| `src/app.md` | not a skill |
| `src/host_notes/*.md` | not a skill |

### A charter is authority, not procedure

- **A charter states identity, mandate and the guardrails that halt execution**,
  and a skill states how to do one class of task. Only the second is a
  procedure.
- **A charter is resident and a skill is on demand.** `src/app.md` Phase 2 loads
  a charter at session start; the specification loads a skill's body only when a
  task activates it.
- **A guardrail does not travel with a borrowed capability** —
  `src/templates/identity_template.md` §Boundaries and coordination. Packaging a
  charter as a skill would make loading a capability import another agent's
  authority.

### A tool stays where it is

- **A tool is independently runnable and shared**, and any agent loads any of
  them: `src/tools/README.md`. A copy under one skill's `scripts/` is a second
  copy of a behaviour that has one owner.
- **The body names the exact command line**, which
  `src/templates/playbook_template.md` already requires.

## Frontmatter

Two fields are required and carry the whole routing surface.

- **`name` — the source file's basename, hyphenated.** One to sixty-four
  characters, lowercase `a-z` and `0-9` and hyphens, no leading or trailing
  hyphen, no consecutive hyphens, identical to the parent directory name.
- **`description` — one sentence, capability first, ending in a period.** The
  specification's ceiling is 1024 characters; write to sixty. A consuming
  client's always-loaded skill index truncates past sixty characters, and what
  is lost is the routing signal rather than detail.

Three optional fields are used, and one is not.

- **`license: MIT`** — the repository's license.
- **`compatibility`** — at most 500 characters, and only where the procedure
  needs something a host may not have.
- **`metadata`** — where every Bristol-specific field goes.
- **`allowed-tools` stays unset.** It is experimental, and Bristol procedures
  call command lines rather than a client's named tools.

**Never add a top-level key the specification does not define.** A
Bristol-specific field goes under `metadata`, whose values are strings, so a
Bristol key is a dotted string and never a nested map:

```yaml
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
```

- **`bristol.kind`** — `playbook` or `protocol`, the shape the file had.
- **`bristol.maintainer`** — the agent that maintains it, never who may run it.
- **No field carries state, order, status or assignment** — `src/app.md` §The
  board is the only channel owns all four.

## Folder shape

```
src/skills/
└── <skill-name>/
    ├── SKILL.md
    ├── references/
    └── assets/
```

- **One flat directory per skill.** The specification requires `name` to match
  the parent directory and describes no category level, so the maintaining agent
  lives in `metadata` and never in the path.
- **`references/` holds what the body would otherwise carry at length** — a
  protocol's per-agent specializations, a long table, a worked example — one
  level deep from `SKILL.md`.
- **`assets/` holds templates and other static resources.** `templates/` is a
  client extension rather than a specification directory; do not create one.
- **`scripts/` stays absent.** Executable behaviour is `src/tools/`.
- **Create only the directories the skill actually fills.** An empty
  `references/` is a placeholder — `src/app.md` §What a file may say.

## Procedure

### Step 1 — Confirm the file is in scope

Read §The mapping. A file that is not a playbook or a protocol archetype is
converted as part of another skill or not at all.

### Step 2 — Create the folder

```
mkdir -p src/skills/<skill-name>
```

`<skill-name>` is the source basename with underscores replaced by hyphens.

### Step 3 — Write the frontmatter

Write the required pair and only the optional fields the skill needs, per
§Frontmatter. Count the description's characters before saving.

### Step 4 — Move the body

The body moves verbatim: Preconditions, Procedure, Failure modes, Audit. The
specification puts no restriction on the body, and the style contract already
governs it. Two things change.

- **The trigger moves into `description`.** An agent's charter naming when to
  load a playbook does not travel with a published skill.
- **A cross-reference to a file that did not move becomes a command line or a
  repository path**, never a relative link out of the skill folder.

### Step 5 — Split past five hundred lines

`SKILL.md` stays under five hundred lines. Anything longer moves into a
`references/` file named for its subject, and the body gains one line naming it.

### Step 6 — Retire the source

Delete the converted file and update every citation of it: the maintaining
agent's charter, the folder README that indexed it, and any playbook that named
it.

### Step 7 — Validate

```
skills-ref validate src/skills/<skill-name>
```

The validator checks the frontmatter and the naming rules. A failure is a defect
in the conversion, not in the source.

## Failure modes

- **A description over sixty characters** → a consuming client truncates it and
  the skill stops routing. Cut it before saving.
- **A nested map under `metadata`** → the specification's metadata maps strings
  to strings. Flatten to dotted keys.
- **`name` and the directory disagree** → validation fails. Rename the
  directory rather than the field.
- **A tool copied into `scripts/`** → two copies of one behaviour. Delete the
  copy and name the command line.
- **A guardrail carried into the body** → the rule belongs to a charter. Cite
  the charter.
- **A converted file left beside its source** → two statements of one procedure.
  Step 6 is not optional.

## Audit

- Every directory under `src/skills/` holds a `SKILL.md` whose `name` equals the
  directory name.
- No `SKILL.md` carries a top-level frontmatter key outside `name`,
  `description`, `license`, `compatibility`, `metadata` and `allowed-tools`.
- No skill body restates a charter rule or a board rule.
- No converted playbook or protocol survives at its old path, and no file cites
  the old path.
