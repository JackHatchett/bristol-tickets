# Wiki Conventions

Reading and reconciling a wiki-shaped knowledge base. A domain's own file
layout, ID scheme and content rules live in the owning agent's charter and
skills.

- **The wiki is user-authored and read-only to every agent.** Propose a change
  by writing a summary to `markdown_notebook.agent_output_dir` for the user to
  fold in.
- **There is no ratification state.** Nothing in a wiki is pending, provisional
  or ratified, and no agent marks it so.

## Reconciling a proposed change

Input is a proposed change — from the user, from an advisory role, from another
agent. Output is a summary in the shared agent-output directory.

1. **Read it as a proposal, however confidently phrased.**
2. **Reconcile against the whole domain**, not only the file the change touches.
3. **Name the file and section in conflict**, never "there is a tension
   somewhere."
4. **Propose a synthesis where a conflict exists**, and the change as-is where
   none does.
5. **Write the fact and where it belongs** to the agent-output directory.

## The page skeleton

```
# Title
## Facts
## Reasoning
## Open questions
```

- **Facts** — what is true, stated as settled. Most reads consult only this.
- **Reasoning** — why a decision was made and what was rejected. Read it when
  revisiting that decision.
- **Open questions** — what is unsettled. Reasoning explains a settled choice;
  this marks an open one.

This is how a page tends to be organized, not a shape an agent enforces.

## On-demand lookup

- **Read the domain's router — topic to file — before pulling any wiki file**,
  once the domain runs past a handful of them.
- **Read one target file per question.** Needing three files for one question
  means the request is under-specified; ask rather than read everything.

## Domain state is not the board

A domain may keep a current-state file recording what is settled and what is
open in the subject matter. That is the domain's content. `tickets.db` holds the
agent's own work state — `src/app.md` §The board is the only channel. Neither
substitutes for the other, and the state file is user-authored like the rest of
the wiki, so an agent proposes updates to it as summaries.
