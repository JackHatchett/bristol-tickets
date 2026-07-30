# local_assistants — shared home for external local-LLM helpers

A **local assistant** is a small, offline, lower-capability LLM (an Ollama-class
model) running inside a *host application on the user's own machine* — e.g.
AnythingLLM's chat window, or an AI plugin embedded in the Markdown notebook
(Obsidian) — that assists a cloud Cowork agent with bounded, cheap, offline
work. It is **not a copy of an agent**. A local model has a fraction of the
reasoning and context budget of the cloud agents, so it can only ever be an
*assistant* to one: it executes narrow, well-specified tasks the cloud agent
sets up, and hands results back through shared files on disk.

This folder is the single home for that machinery so **any** agent can own a
local assistant, rather than each burying its own copy under its agent folder.

## Members

- *(none)*

// A small local model handles agent-mode file navigation slowly and
// unreliably; the RAG/upload variant is fast but low quality. Weigh both
// against the cloud agent doing the work directly before building one.

## Shared invariants (every local assistant obeys these)

These specialize `protocols/_shared/external_ai_bridge.md`; each assistant adds
its own bridge protocol for the delta.

1. **Assistant, not authority.** The local model never makes canonical
   decisions, never designs the thing it operates on (it doesn't author
   lessons, or decide library structure). The cloud agent remains the pen.
2. **Coordinate through shared disk.** The two brains never run at once. They
   sync through named files in the git-ignored data tree or a sanctioned
   notebook output dir — one appends, the other reads next session. No live
   two-way channel.
3. **Scoped, narrow powers.** An assistant gets the least access that lets it
   do its job (e.g. append-only to one log file; write-only to one notebook
   subtree). Powers are configured at deploy time in the host app, never
   chosen by the model.
4. **Paths resolve from `/config`, never hardcoded.** Host apps (AnythingLLM's
   setup args, plugin config boxes) often can't expand `~` or env vars, so the
   *one* real absolute path each assistant needs is filled in by hand at
   install time on the machine — never committed to a tracked file.
5. **Deployed copies are manual.** The source of truth lives here in `/src`;
   the copy running inside the host app (e.g. an AnythingLLM agent skill) is a
   separately-deployed copy. Change it here, then redeploy.

## Why this is its own top-level tool folder

The "external local-LLM assistant" concept spans agents and host apps: it may
run in AnythingLLM today and an Obsidian plugin tomorrow, serving the teaching
assistant, the librarian, or a future agent. Housing it under any one agent
would mis-signal ownership. It lives here as shared infrastructure; each
assistant's *behavioral* contract stays with its owning agent's protocols.
