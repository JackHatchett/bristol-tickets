# {{PLAYBOOK_NAME}} — Playbook Template

## Purpose
Describe the purpose of this playbook in one short paragraph.  
A playbook is a repeatable, provider‑agnostic procedure that Claude executes when a task matches its purpose.

## Preconditions
List any conditions that must be true before running this playbook.  
Examples:
- Required tools in tools/
- Required context mode
- Required mounted drives
- Required user confirmation (if any)

## Procedure
Describe the step‑by‑step workflow.  
Keep steps abstract and provider‑agnostic.  
Example structure:

1. Identify target items.
2. Stage items in a temporary working directory.
3. Apply classification or transformation.
4. Route results to the correct destination (the owning agent's own data root, per its charter — not a shared routing config).
5. Log structural changes via `tools/roadmap_tools/roadmap_write.py` (add-task / add-issue-log) against the shared roadmap.db — never a markdown state file, and never a handoff note (there is no such mechanism).

## The board is the only channel (applies to every playbook)

Do not write a procedure that violates any of these. Full rule:
`src/tools/roadmap_tools/README.md` (§The board is the only channel).

- Work state — done / next / in progress / awaited / who owes whom / order —
  lives in `roadmap.db` and nowhere else.
- **Never derive a next action from a file.** No scanning a folder, no reading
  a JSON status field, no "take the latest file by name." A step that does this
  is a second tracker.
- Task another agent with a ticket (`assignee` = them, `reporter` = you), never
  a file, a folder drop, or a message passed through the user.
- Never require the user to carry work between the board and an agent.
- No phases and no deferral in prose — no "phase 1," "later," "next pass," or
  "TODO." Either it is in scope or it is another card.
- A file an outside party must be shown because it cannot read `roadmap.db` is
  a **payload**: a ticket names it, the ticket holds the state, deleting it
  loses nothing.

## Provider-Specific Logic
If the procedure requires Gmail, Outlook, or other provider‑specific behavior, state:

Provider‑specific logic is handled live via the provider's connected MCP (e.g. Gmail MCP) — not hardcoded here, and not routed through a static config file.

This playbook must not contain provider‑specific rules.

## Tools Used
List any scripts in tools/ that this playbook calls.  
Example:
- tools/document_tools/normalize_recipes.py
- tools/maintenance/build_diagrams.py

## Logging Requirements
Describe what must be logged via `roadmap_write.py` against the shared roadmap.db.  
Examples:
- Items processed
- Items routed
- Errors encountered
- Structural changes

## Failure Modes
Describe what Claude should do if:
- A required file is missing
- A script fails
- A classification is ambiguous
- A routing target is unclear

## Human Audit Notes
Describe what the user should periodically check.  
Examples:
- Outdated assumptions
- Stale references
- Missing cross‑links


