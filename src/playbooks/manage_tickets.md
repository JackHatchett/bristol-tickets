## Purpose
Define how chief_of_staff uses the tickets DB as its cross‑session memory system:
- when to read it
- when to update it
- how to treat it as the canonical queue of next actions
- how to add small items during conversation
- how to keep the DB consistent with user intent

This playbook is conceptual; all mechanism lives in ticket_tools and bristol.

---

## When to read the board
- At **every session start**, run `ticket_tools/cos_status.py` to load:
  - milestone
  - active epics
  - ordered queue
  - next action

- When the user asks:
  - “what’s next”
  - “where were we”
  - “status”
  - “continue”

---

## When to update the board
Update the DB whenever the user expresses:
- a new task (“remind me to…”, “add…”, “we should…”, “later we need to…”)
- a change to an existing task (“mark this done”, “block this”, “increase priority”)
- a new epic or project
- a shift in priority or focus

All updates go directly into the DB via SQL.

---

## How to treat the board
- The tickets DB is the **single source of truth** for:
  - next actions
  - active work
  - backlog
  - strategic direction

- The DB replaces:
  - next_session.md  
  - roadmap.md  
  - ad‑hoc notes  
  - memory drift  

- The DB is **always authoritative** over conversation memory.

---

## How to add items during conversation
When the user casually mentions something to do later:
- parse it as a task
- insert into the DB under the appropriate epic
- confirm back to the user only if ambiguous

Examples:
- “We should fix X later.” → add task
- “Remind me to…” → add task
- “Let’s track this.” → add task

---

## Record types: Build vs Fix

Every ticket (the umbrella term; "issue" and "ticket" are synonyms for it) is
exactly one of two **record types**, stored in `task.record_type`:

- **Build** — a thing to *build*. Something new or changed. Its Description is
  a user story plus testable acceptance criteria.
- **Fix** — a *broken* thing. Its Description states the expected behaviour and
  the observed divergence. No story, no acceptance criteria.

These deliberately avoid Atlassian's "Story / Bug" vocabulary — the system's
own path. Default is **Build**; set `--record-type fix` (CLI) or pick *Fix* in
the viewer when the ticket is fixing something that misbehaves.

These are governing rules for how *you* (any agent) and the user write ticket
Descriptions; the DB only stores the type flag and the free-text body. When you
author a ticket, match its Description to its type. The viewer pre-fills these
same skeletons as mad-libs — constant words with short `[bracketed]` blanks;
replace the whole bracket (including the brackets) with your own words.

**Build Description format:**

```
Story:
As [owner] I want [what should change] so that [why it matters].

Acceptance Criteria:
1. Given [starting state], when [action], then [expected result].
```

Add a numbered line per acceptance criterion. A worked one, from the loading
protocol: "Given the active agent is chief_of_staff and Cowork is loading
Bristol Tickets, when a session loads tickets.db, then it treats its next priorities
as its own active-board tasks (stage='active') in precedence order."

**Fix Description format:**

```
Expected:
Given [precondition], when [action], then [expected result].

Observed:
[what happened instead]
```

**Template precedence (viewer):** on create, the Description is pre-filled with
the selected type's skeleton. Your own text always wins — switching Build⇄Fix
only swaps the skeleton while the field is still untouched boilerplate; once you
type anything of your own it is never overwritten. Emptying the field entirely
brings the skeleton back next time the record opens (blank ⇒ template).

## Description discipline — the template, and only the template

**This section governs agents. It does not govern the user.**

When you author or edit a ticket body, its Description contains exactly the
skeleton above for its record type: Story + Acceptance Criteria for a Build,
Expected + Observed for a Fix. Nothing precedes it, nothing follows it, and no
other header appears in it. Specifically banned, because each of these has
actually been written into a Description:

- `Source: <file> §4.1` or any other provenance header.
- "Addressed to chief_of_staff or librarian."
- "USER DECISION REQUIRED BEFORE EXECUTING."
- An options-and-recommendations essay, or a numbered implementation plan.
- Any note to whoever reads the ticket next.

You may rewrite a Description and its acceptance criteria whenever the work
changes — but only into that shape.

**Where the banned material goes instead:**

| What you wanted to write | Where it goes |
| --- | --- |
| Reasoning, findings, what you did, what's needed next | An `add-issue-log` comment |
| A decision the user must make before you proceed | An `add-issue-log` comment, plus `assignee` = `user` |
| "This came from that review / that note / that page" | A **link** (`link-add --uri`) |
| "This relates to ticket #153" | A **link** (`link-add --to-task 153`) |
| Durable technical detail (schema notes, a working pattern) | The file that owns it — a README or playbook — then link to it |

Comments are the elaboration channel and you should use them freely: they are
human prose, not a template, and they are what the board renders under the Log.
The only rule on a comment is §Format — scannable in about ten seconds.

## Links — a ticket's relations

Two kinds, both via `ticket_write.py link-add --task N`:

- `--to-task M` links two tickets. It is stored once and symmetrically, so it
  shows on **both** tickets immediately. Never run the mirror call, and note
  that `link-remove` clears it from both ends.
- `--uri "…"` links to an address: a web URL, a `zotero://` citation, an
  `obsidian://` note, or a file path. `--label` gives it a caption. Bristol
  hands the address to the OS, so an `obsidian://` URI opens Obsidian and a
  bare `.md` path opens in whatever owns that file type.

Read the links on a ticket before executing it, exactly as you read its attached
images. Since provenance no longer lives in the Description, a ticket's text on
its own is deliberately incomplete — the status scripts print a `LINKS` section
for precisely this reason.

**Keep tickets small.** was authored deliberately oversized (a record-
type redesign, a viewer feature, a handoff redesign, and an explainer, all in
one card) as a worked example of what *not* to do. When a ticket sprawls across
several independent outcomes, split it into one Build or Fix per outcome, each
with its own crisp acceptance criteria, rather than carrying a mega-ticket.

## When to open the viewer
Open the GUI when the user wants:
- to visually inspect the board
- to reorganize tasks manually
- to browse epics or scopes

Command:

python3 tools/bristol/app.py

---

## When to create or rebuild a tickets database
Use ticket_tools only when:
- creating a new agent
- migrating schema
- rebuilding from markdown archives

Never during normal operation.

---

## Consistency rules
- Every session ends with the cards telling the truth. There is no handoff
  note and no `add-handoff` — a per-agent "where things stand" block is work
  state outside the cards. Work left mid-flight ends as a `doing` card on the
  active board with a high `priority` and an `assignee`; the status scripts rank
  it first, so the next session picks it up without being told.
- Every new idea becomes a task.
- Every shift in focus updates epic status.
- The queue must always reflect the user’s real priorities.
- The DB must never fall behind the conversation.

---

## Human audit notes
- Ensure DB path in user.yaml is correct.
- Ensure no personal paths exist in mechanism tools.
- Ensure cos_status.py output matches DB state.
