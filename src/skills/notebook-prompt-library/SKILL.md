---
name: notebook-prompt-library
description: Maintains the notebook assistant's custom prompts — their frontmatter, what a prompt may write into the notebook, and the index that lists them. Use when a prompt is being added, corrected, audited or indexed.
license: MIT
compatibility: Needs a Markdown notebook with markdown_notebook.assistant_prompts_dir declared in config.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/document_tools/check_prompts.py
---
# notebook-prompt-library

Input: a prompt to add, a prompt to correct, or the library to audit. Operation:
the checks below. Output: prompt notes that satisfy the frontmatter and emission
contracts, and an index that lists what exists.

The assistant that runs these prompts, and what its output is worth, are
`src/skills/external-ai-bridge/references/chief_of_staff.md`.

## Finding the library

- **Resolve `markdown_notebook.assistant_prompts_dir` through
  `src/tools/config_tools/data_paths.py`**, never a literal path. The folder
  sits in the notebook's workspace zone, so an agent may write in it —
  `config`'s `markdown_notebook` §ZONES.
- **The assistant's own `customPromptsFolder` setting must name that same
  folder.** The setting is the plugin's and the config key is Bristol's; a
  disagreement between them is what makes a prompt invisible.
- **One prompt is one note**, and the note's filename is the name the user sees
  in the slash menu.

## The frontmatter contract

Every prompt note carries the full key set. A missing key is what makes a prompt
behave differently from its neighbours rather than fail visibly.

```yaml
---
copilot-command-context-menu-enabled: <true|false>
copilot-command-slash-enabled: <true|false>
copilot-command-context-menu-order: <number>
copilot-command-model-key: ""
copilot-command-last-used: 0
tags:
  - ai/prompt
---
```

- **`tags: ai/prompt` is on every prompt note**, which is what makes the library
  findable from outside the assistant's own menu.
- **`copilot-command-model-key` is `""`** unless one prompt needs a model the
  rest do not, and `copilot-command-last-used` is the plugin's to write.
- **`copilot-command-context-menu-order` is unique across the library**, in
  steps of ten, so an insertion needs no renumbering.
- **No unresolved wikilink appears anywhere in a prompt note**, frontmatter or
  body. A link to a note that does not exist creates one on click and litters
  the vault.

## What a prompt may emit

A prompt that tells the assistant to generate a note states the note's shape,
because the assistant invents one otherwise.

- **Take the frontmatter from an existing template in
  `notes_dir/02_templates`**, copied key for key, rather than composing a new
  shape. A more specific template wins where one covers the note's kind.
- **Write a literal `YYYY-MM-DD` date** wherever a template's `created` field
  holds a Templater expression. The assistant does not execute
  `<% tp.file.creation_date() %>` and leaves it in the file as text.
- **Carry the global header's keys —** `aliases`, `tags`, `created`, `status`,
  `source_url` (`template_000_header.md`) — **on any note no more specific
  template covers.**
- **Name a destination in a writable zone.** A prompt whose output belongs in a
  folder the user authors returns the text to the user instead of writing it.
- **Emit the note and nothing else.** No preamble, no explanation of what it
  did — `src/skills/external-ai-bridge/SKILL.md` §1 invariant 4.

## The index

- **One note lists every prompt as a wikilink**, grouped by what the prompts are
  for, each with one line saying when to use it. It is
  `notes_dir/41_ai_workspace/prompt_library_hub.md`, and
  `ai_workspace_hub.md` links to it.
- **The index sits beside the library folder, never inside it.** The assistant
  loads every note in that folder as a runnable prompt, so an index filed there
  becomes a command in the slash menu and a finding in the checker.
- **Adding, renaming or removing a prompt updates the index in the same pass.**
  The folder is the source and the index is derived from it, so the two never
  land in separate sessions.
- **The index holds no work state** — no status column, no what-changed
  section, no dates. `src/app.md` §What a file may say.

## Auditing the library

1. **Run the checker**, which reads the folder from config and needs no
   argument:

   ```
   python3 src/tools/document_tools/check_prompts.py
   ```

   It reports a missing key, a missing tag, a repeated order number, a wikilink
   resolving to no note, and an emitted frontmatter block holding a Templater
   expression or carrying no template's keys. Exit status is 1 when any check
   matched.
2. **Read each note the checker names**, against the two contracts above.
3. **Fix what is wrong in place**, then rebuild the index.
4. **Re-run the checker** until it says every check matched nothing.
