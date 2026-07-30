# {{FOLDER_NAME}} — Folder README

> Human-facing description of this folder’s role in the system.  
> No user-specific data.

---

## 1. Purpose & Scope
Briefly describe:
- Why this folder exists in the overall system design
- Which conceptual layer it belongs to (runtime, config, data, tools, playbooks, protocols, architecture, templates)
- What kinds of files are appropriate here
- What kinds of files are out of scope for this folder

---

## 2. Contents Overview
Summarize the contents at a structural level:
- Key files and subfolders
- What each is generally responsible for
- Whether each is primarily human-facing, agent-facing, or both
- Any important dependencies on other folders or generic system components

Avoid any user-specific details or runtime state.

---

## 3. System Relationships
Describe how this folder fits into the broader system:
- Which other folders it interacts with
- Which generic components it conceptually relates to (agents, tools, playbooks, protocols, drives, stack)
- How it participates in the overall architecture (for example: “part of the toolchain”, “part of configuration”, “part of data layer”)

Keep this high-level and structural, not situational or personal.

---

## 4. Human Audit Checklist
List neutral, non-personal checks that help keep this folder healthy:
- Files that may need periodic review for relevance
- References that may need confirming against the current architecture
- Cross-folder links that may need updating when structure changes
- Any patterns that tend to accumulate noise and may need occasional cleanup

These checks should be generic and structural, never tied to specific user events or state.
