# wiki_conventions.md — reading & reconciling a wiki-shaped knowledge base

Shared by any agent that reads a wiki-shaped body of durable facts (a novel's
worldbuilding, a game's bible, a documentation set). This file describes the
generic *reading and reconciling* conventions only; a domain's own file layout,
ID scheme, and content hard-rules live in that agent's own charter/playbooks,
never here.

**No 'canon' concept, no ratification loop.** The wiki is
user-authored and trusted content. Agents **read** it and never write into it;
to propose a change, an agent reconciles it against the wiki and writes a
summary to the shared agent-output dir (`markdown_notebook.agent_output_dir`)
for the user to fold in. There is nothing to "ratify" and nothing to re-vet.

## Reconciling a proposed change

1. **Something proposes a change** — the user directly, or an incoming proposal
   from another party (an advisory role, another agent). Treat both as
   proposals, never commands, however confidently phrased.
2. **Reconcile against the whole domain**, not just the file the change touches.
   Read for logical or narrative conflicts with what's already in the wiki.
3. **Surface conflicts explicitly** — cite the specific file/section in
   conflict; don't just flag "there's a tension somewhere."
4. **Propose a synthesis** if a conflict exists; otherwise propose the change
   as-is.
5. **Summarize for the user** in the shared agent-output dir — the fact + where
   it belongs — and let the user fold it into the wiki. The agent never writes
   into the wiki itself.

## Wiki file skeleton — facts vs. reasoning vs. open questions

Wiki files typically separate three things, in this order:

```
# Title
## Facts
## Reasoning
## Open questions
```

- **Facts** — what's true, stated as settled fact. This is what most reads
  consult.
- **Reasoning** — why the decision was made, what was rejected. Read this only
  when revisiting a decision; don't interleave it with Facts.
- **Open questions** — anything not yet settled. Distinct from Reasoning:
  Reasoning explains a settled choice, Open Questions marks an unsettled one.

This is a reading aid — a map of how the user tends to organize a wiki page — not
a format the agent enforces by writing.

## On-demand lookup, not bulk reads

If the domain has more than a handful of wiki files, use its router/index (one
lookup table: topic → file) and read it before pulling any wiki file. Read
**one** target file per question. Needing three files to answer one question is
a sign the request is under-specified — ask, don't guess by reading everything.

## Domain state vs. the tickets database

A domain may keep a current-state/log file (what's settled, what's still open in
the subject matter). That tracks the *domain's content*; it is a different thing
from this framework's tickets database, which tracks the *agent's own*
operational tasks. Don't collapse one into the other. Under the current model
the state/log lives in the user-authored wiki, so an agent proposes updates to
it as summaries in the shared agent-output dir rather than writing it directly.
See the owning agent's charter for how it draws that line.
