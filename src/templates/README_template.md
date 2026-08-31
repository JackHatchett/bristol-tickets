# {{FOLDER_NAME}} — folder README template

Builds a folder's own `README.md`: a structural description of what the folder
is for, written for a human browsing the repository. **No user-specific data and
no runtime state.** Style contract:
`src/templates/identity_template.md` §The governing-doc style contract.

---

```markdown
# {{Folder name}}

{{One or two sentences: what this folder holds and which conceptual layer it
belongs to — runtime, config, data, tools, skills, templates.}}

## What belongs here

{{One rule per bullet: the kinds of file that belong, and the kinds that do
not. Name where an out-of-scope file goes instead.}}

## Contents

{{Key files and subfolders, one line each: what it is responsible for, and
whether it is human-facing, agent-facing or both.}}

## Relationships

{{Which other folders this one depends on or is depended on by, and how it
participates in the architecture. Structural, never situational.}}

## Audit

{{Neutral structural checks that keep the folder healthy — references worth
confirming against the current architecture, cross-folder links that go stale
when structure changes, patterns that accumulate noise. Never tied to a
specific event.}}
```
