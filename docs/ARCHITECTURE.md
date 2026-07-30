# Architecture — `agent_system`

This document is the engineering-depth companion to the root `README.md`'s
**System Architecture** section. The README gives the one-paragraph-per-surface
overview; this file explains *why* the system is shaped this way, how the
surfaces share state, what is built versus planned, and the design principles
that constrain future work. Setup and configuration mechanics live in
`docs/SETUP.md` and are not repeated here.

## 1. One substrate, several runtime surfaces

`agent_system` is a single application exposed through several *runtime
surfaces* (the README calls them "heads"). A runtime surface is an interface a
different kind of actor uses to drive the same underlying system — a
programmatic API, a human clicking a GUI, or an LLM reading instructions. The
surfaces are deliberately not peers layered on top of each other; they are
parallel front-ends over one shared substrate:

- **Shared state** — a single SQLite database (`data/<instance>/roadmap/roadmap.db`)
  is the sole source of cross-session truth: epics, scopes, tasks, their comment
  log, links, image attachments, and a transition log. There is no inbox table
  and no handoff ledger — a card left mid-flight *is* the handoff. No surface
  keeps a parallel record; markdown task ledgers are explicitly forbidden.
  Whichever surface acts, the others observe the change on their next read.
- **Shared configuration** — one git-ignored `config/config.local.json` resolves
  every generic, relative path the tracked code uses (`data/*/…`) to a concrete
  machine, drive, and agent registry. Surfaces never hardcode a personal path;
  they resolve it through the config helper or declared `agents.*.env` vars.

Because state and config are shared and authoritative, a surface can be added,
rebuilt, or left unbuilt without the others losing coherence. This is the
central architectural bet: **invest in the data and config contract, and the
interfaces become swappable.**

## 2. The runtime surfaces

### 2.1 Python application head (`src/app.py`) — planned, not yet created
The intended long-term programmatic core: a structured, API-driven entry point
that will eventually operate the whole system without a human or an LLM in the
loop. It is the reference implementation the other surfaces are measured
against. Status: **no such file exists** — `src/` holds `app.md` and the
package folders, and nothing else at its top level. This is a direction, not a
runtime; do not expect a module or a stub at that path.

### 2.2 Local tooling head (`src/tools/…`) — built, in daily use
A collection of *modular, standalone* utilities that let an operator act on a
specific database or system state directly, without agent mediation — verifying
a schema, editing the Kanban board, running a protocol. The flagship is the
PySide6 app **Bristol** (`src/tools/bristol/`), a desktop GUI over
`roadmap.db`. The defining property of this head is *modularity*: each tool is
independently runnable and independently comprehensible. See §4 for why that
fragmentation is a feature, not debt to be consolidated.

### 2.3 Cowork chat head (`src/app.md`) — built, primary editor today
A markdown-defined runtime for an LLM (Claude, via Cowork). On launch it reads
`src/app.md` and follows an initialization pipeline: load config, instantiate an
agent identity, restore state from `roadmap.db`, then act on user direction. It
is currently the only surface that runs end-to-end, and in practice it is the
primary file-system editor and workflow executor. It also stands in as a working
prototype of the future programmatic head: the sequence-of-documents pattern it
follows is a hand-run simulation of what `src/app.py` will eventually do in code.

## 3. Planned fourth surface — a packaged Mac GUI

A fourth surface is planned: a native Mac application that presents the
specialized tools the project accumulates — Bristol today, and the
other single-purpose utilities built over time — as click-through features of one
packaged product.

The interesting property is *recursive*: tools are built as instruments for
building the system, and then those same instruments become the shipped product
surface. A utility written to inspect or edit internal state graduates, largely
unchanged, into a user-facing feature. The system's construction history and its
feature set converge. This surface is a direction, not yet an implementation, and
it explicitly does **not** imply merging the tools into a monolith (see §4) — it
implies presenting independently-built tools behind one launcher.

## 4. Design principles

### 4.1 Keep fragmented tools fragmented
The local tooling head is intentionally a set of small, separate programs rather
than one integrated application. Each tool should stay independently runnable and
small enough to be read and modified in a single pass. Bristol in
particular must **not** be absorbed into a monolith: its value depends on being a
self-contained, standalone surface. When the packaged GUI (§3) arrives it
composes these tools behind a common launcher; it does not fuse their codebases.
Fragmentation keeps each surface legible, and legibility is a first-class goal
here (§4.2).

### 4.2 Built to be learned from, alongside AI
The intended audience is people learning to build software *mostly alongside AI*
rather than by writing every line unaided. That audience shapes the architecture:
surfaces are kept small and legible, the data/config contract is explicit and
inspectable, and the metaphor-free separation of concerns is meant to be readable
by someone still building fluency. The system is simultaneously a working tool
and a worked example.

### 4.3 Bristol as a deliberate practice surface
Bristol doubles as a hands-on practice ground for a less-experienced
developer to work on a *standalone copy*, deliberately kept separate from the
AI-driven main development flow. This is why it stays a clean, self-contained
PySide6 app with no dependency on the rest of the runtime: a learner can open it,
change it, and run it in isolation without needing to understand — or risk — the
whole system. Keeping this surface fragmented (§4.1) is what makes it usable as a
sandbox.

### 4.4 One authoritative store, no shadow ledgers
State lives in `roadmap.db` and configuration in `config.local.json`; nothing
else is a source of truth. Agents and tools read and write these, never a
parallel markdown tracker. This is what lets multiple surfaces coexist without
drift, and it is enforced culturally (agent charters forbid shadow ledgers) as
well as structurally.

## 5. What is built vs. planned (at a glance)

| Surface | File(s) | Status |
| --- | --- | --- |
| Python application head | `src/app.py` | Planned — no file exists yet, a direction only |
| Local tooling head | `src/tools/…` (e.g. `bristol/`) | Built, in use |
| Cowork chat head | `src/app.md` | Built, primary runtime today |
| Packaged Mac GUI | — | Planned — composes existing tools, not a merge |

For how to install, configure, and run any of the built surfaces, see
`docs/SETUP.md`.
