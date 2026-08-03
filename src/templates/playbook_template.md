# {{PLAYBOOK_NAME}} — playbook template

Builds `playbooks/<agent>/<name>.md`, or a top-level `playbooks/<name>.md` for
chief_of_staff: a repeatable, provider-agnostic procedure a session runs when a
task matches its purpose. Style contract:
`src/templates/identity_template.md` §The governing-doc style contract. What
belongs in the folder: `src/playbooks/README.md`.

---

```markdown
# {{playbook_name}} — {{agent}} playbook

{{One or two sentences: what this procedure does and what triggers it. Name the
playbook that owns an adjacent stage rather than restating it.}}

## Preconditions

{{One rule per bullet: what must be true before this runs, and what to do when
it is not. Omit the section when there are none.}}

## Procedure

{{Numbered steps in execution order. Each step opens with the imperative that is
the rule; the rest of the step is its boundary. Command lines exact, in a fenced
block.}}

## Failure modes

{{One bullet per failure the procedure will actually meet, in the form
"**what went wrong** → what to do". Omit the section when there are none.}}

## Audit

{{Structural checks that keep this procedure honest over time. Omit the section
when there are none.}}
```

---

## Rules for this template

- **State a rule once**, in the file that owns it. A playbook cites `src/app.md`
  and the agent's charter rather than restating either.
- **Never restate the board rules.** `src/app.md` §The board is the only channel
  owns work state, cross-agent tasking and the ban on deriving a next action
  from a file. A playbook step that scans a folder, reads a JSON status field or
  takes the latest file by name is a second tracker and a defect.
- **Name the tool, never reimplement it.** Where a procedure calls a script,
  give the exact command line and let `src/tools/` hold the behavior.
- **Provider-specific behavior goes to that provider's connected MCP**, never
  into a playbook and never into a shared config file.
- **A file an outside party must be shown, because it cannot read
  `tickets.db`, is a payload**: a ticket names it, the ticket holds the state,
  and deleting it loses nothing.
