# tools/wiki_tools/ — shared wiki/knowledge-base conventions

Not owned by any one agent. Any agent that reads a wiki-shaped body of durable
facts — a novel's worldbuilding, a game's bible, a documentation set — can point
at these conventions instead of re-deriving the same pattern.

**No 'canon' concept.** There is no ratification model. The
wiki is user-authored, trusted content; agents read it and never write into it,
and propose changes by writing summaries to the shared agent-output dir
(`markdown_notebook.agent_output_dir`) for the user to fold in.

## What's here

- `wiki_conventions.md` — how to read and reconcile a wiki-shaped knowledge
  base: the reconcile-then-summarize flow, the Facts/Reasoning/Open-Questions
  reading aid, and the on-demand-lookup (router/index) principle. No ratification
  loop, no writing into the wiki.

## How an agent uses this

An agent's own charter and playbooks stay the source of truth for *that* agent's
specific wiki (its file layout, its ID scheme, its content hard-rules). Point at
`wiki_conventions.md` for the generic reading/reconciling conventions, and
describe only the domain-specific parts locally — don't copy the conventions into
the agent's own playbook. `playbooks/writers_room/story_proposals.md` and
`playbooks/game_designer/design_proposals.md` are the reference examples of this
pattern in use.

## Human Audit Notes

If two or more agents' playbooks start describing the same reconcile/summarize
conventions slightly differently, that's drift — reconcile back to the one
version here.
