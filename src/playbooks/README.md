# Playbooks — Abstract Procedures

## Role in the System
Playbooks define **repeatable, provider‑agnostic procedures** that the agent can execute when performing operational tasks. They are not rules, not authority, and not global instructions. They are procedural modules that Claude loads **only when a task matches their purpose**.

Playbooks sit below:
- agent_identities/ (each agent's charter — authority, mandate, guardrails)
- protocols/ (coordination contracts with other agents or external AI)

Playbooks sit above:
- tools/ (scripts used by procedures)
- the shared roadmap.db (`data/*/roadmap/roadmap.db`, via `tools/roadmap_tools/`), where results and structural changes are logged — never a markdown state file

## What Belongs Here
A playbook is:
- a **procedure**  
- a **repeatable workflow**  
- a **step‑by‑step operational document**  
- a **provider‑agnostic pattern**  

A playbook is not:
- a rule  
- a safety gate  
- a policy  
- a personal workflow  
- a user‑specific configuration  
- a storage‑domain definition  

## Folder Structure
Playbooks are organized into two tiers: **CoS-level** procedures that live at the top of this folder, and **agent-scoped** subfolders that hold the procedures belonging to a single agent.

CoS-level (top-level) playbooks:
- create_agent.md — bootstrap a brand-new agent from nothing (identity charter, playbooks/tools/protocols scaffolding, roadmap epic)
- migrate_legacy_agent.md — convert a legacy pre-reorg agent bundle into the current framework pattern
- manage_roadmap.md — how chief_of_staff uses the roadmap DB as cross-session memory (when to read, when to update, how to treat it as the canonical queue)
- storage_audit.md — abstract procedure for monthly storage audits / cleanup inventory

Agent-scoped subfolders (each holds the playbooks for that agent; see the agent's charter for authority):
- career_coach/ — career_pivot, cover_letter, interview_prep, jd_evaluation, linkedin_editing, resume_tailoring, session_closure
- client_services/ — operator_tasks, project_intake
- game_designer/ — design_proposals, git_milestone_coaching, project_context, socratic_design_coaching
- librarian/ — add_book, data_safety
- teaching_assistant/ — content_generation, html_render, navigator
- writers_room/ — story_proposals, crew_dispatch, project_context, voice_distillation

## How Claude Should Use This Folder
- Load a playbook **only** when a task explicitly matches its purpose.
- Do not treat playbooks as global rules.
- Do not auto‑load playbooks at session start.
- Do not modify playbooks unless the task is explicitly “update this playbook.”
- When a playbook references a script, use tools/ as the execution layer.
- When a playbook produces structural changes, log them via `tools/roadmap_tools/roadmap_write.py` (add-task / add-issue-log) against the shared roadmap.db — never a parallel markdown ledger and never a handoff note (there is no such mechanism).

## Cross‑Links
- `src/agent_identities/<agent>.md` — each agent's own charter defines where that agent's durable content lives (its data root, per §2 of its charter); there is no shared routing file.
- `config/config.local.json` (Agent Registries) — the live registry of every agent and its data paths.
- tools/ — scripts used by playbooks.
- `data/*/roadmap/roadmap.db` — ledger of executed actions and handoffs.

## Human Audit Notes
- Review this folder when changing workflows or adding new procedures.
- Ensure no user‑specific logic leaks into this folder.
- Ensure each playbook is provider‑agnostic and references the user‑specific project when needed.

## Known Open Questions
- None at this abstraction level.

## Session Bootstrap (for Claude / Copilot)
- Role: Abstract procedural workflows.
- Source of Truth: `agent_system/src/playbooks/` (this repo).
- When to Load: Only when a task matches a playbook’s purpose.
- Allowed Operations: Read/write within this folder; structural changes elsewhere follow each agent's own charter guardrails.
- Do Not: Invent new rules or provider‑specific logic; those belong in the relevant agent's own data root or a connected MCP (e.g. Gmail).
- Routing: If a task requires provider‑specific behavior, use the provider's connected MCP directly, or the owning agent's data root as defined in its charter — there is no shared routing file.
