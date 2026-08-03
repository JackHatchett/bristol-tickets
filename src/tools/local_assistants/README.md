# Local Assistants

A local assistant is a small offline LLM running inside a host application on
the user's machine — a desktop chat window, an AI plugin in the Markdown
notebook — that executes narrow tasks a cloud agent sets up and returns results
through files on disk. It has a fraction of a cloud agent's reasoning and
context, so it assists one; it is never a copy of one.

## Index

No assistant is defined yet.

// A small local model handles agent-mode file navigation slowly and
// unreliably; the RAG/upload variant is fast but low quality. Weigh both
// against the cloud agent doing the work directly before building one.

## Invariants

These specialize `protocols/_shared/external_ai_bridge.md`; an assistant's own
bridge protocol adds only its delta.

- **The local model decides nothing canonical.** It never authors the thing it
  operates on; the cloud agent holds the pen.
- **The two coordinate through named files on disk** — the git-ignored data tree
  or a sanctioned notebook output directory, one appending and the other reading
  next session. They never run at once and there is no live channel.
- **Grant the least access that does the job** — append-only to one log,
  write-only to one subtree. Powers are set in the host app at deploy time,
  never chosen by the model.
- **Fill in the one absolute path each assistant needs by hand at install
  time.** Host apps often cannot expand `~` or an environment variable, and that
  path never enters a tracked file.
- **Redeploy after changing the source here.** The copy running inside the host
  app is a separate artifact.

## What belongs here

An assistant serves whichever agent set it up, and the concept spans host apps,
so the machinery lives here rather than under one agent. An assistant's
behavioural contract stays in its owning agent's protocols.
