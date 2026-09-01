# Notebook-assistant bridge — chief_of_staff protocol

Specializes `src/skills/external-ai-bridge/SKILL.md`, which holds the six common
invariants. This file carries only the delta for how the notebook assistant and
`chief_of_staff` coordinate: the assistant runs the custom prompts
`chief_of_staff` authors, inside the user's Markdown notebook and nowhere else.
**Which tool the assistant is resolves from
`stack.external_agent_roles.notebook_prompt_library`** — reference the role,
never the product (`src/skills/external-ai-bridge/SKILL.md` §1d).

- **Memory model:** stateless, re-pointed each request. Each prompt note is the
  whole brief for the run it drives, and the assistant keeps nothing between
  runs.
- **Direction:** `chief_of_staff` authors the prompts; the assistant executes
  one when the user invokes it. The assistant designs no prompt and edits none.
- **Payload:** one prompt note from `markdown_notebook.assistant_prompts_dir`,
  plus whatever notebook context the user selects when invoking it.
- **Return format:** a note or a passage inside the user's notebook, written by
  the assistant's own agent, which has `writeFile` and `editFile` enabled.
- **Guardrail cited, never restated:** an external AI is a consultant whose
  output is checked against the real files before it is adopted
  (`src/agent_identities/chief_of_staff.md` §2.5).

## The contract

Two parties, two roles, never overlapping.

- **`chief_of_staff`** owns the prompt library: it writes, corrects and indexes
  the prompt notes, and it is the only party that edits one.
  `src/skills/notebook-prompt-library/SKILL.md` is how.
- **The assistant** executes a prompt against the notebook. **Nothing it
  produces is authoritative**: a note it writes is a draft the user keeps or
  discards, and a claim it makes is checked against the file that owns the fact
  before any agent acts on it.

**The board is still the only channel** — `src/app.md` §The board is the only
channel. A prompt never records work state, never files a card, and never
carries a request from one agent to another; anything the assistant produces
that would be work state is discarded rather than filed.

**The assistant writes only where any agent may write** — `config`'s
`markdown_notebook` §ZONES. A prompt that emits a note names a destination in a
writable zone, and a prompt aimed at a folder the user authors returns its
output to the user instead.

## How any party should use this

1. **`chief_of_staff` writes or corrects a prompt note** to the frontmatter and
   emission contract in `src/skills/notebook-prompt-library/SKILL.md`.
2. **The user invokes it** from the assistant's slash menu or context menu,
   with whatever note or web page is the context.
3. **The assistant returns a note or a passage** in the notebook.
4. **The user keeps or discards it.** Nothing here is filed by an agent on the
   strength of the assistant having produced it.

## Cross-links

- `src/skills/external-ai-bridge/SKILL.md` — the archetype this specializes.
- `src/skills/notebook-prompt-library/SKILL.md` — the procedure that maintains
  the library.
- `src/agent_identities/chief_of_staff.md` §2.5 — external AI is a consultant.
