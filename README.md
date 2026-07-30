# Bristol Tickets

A local, multi-agent simulation and orchestration layer designed to manage tasks, digital architecture, and file systems. 

This repository serves as the generic, forkable shell of the application. It provides the runtime architecture, agent identities, and structural modules required to operate the system. All user-specific runtime state, cloud backup targets, and personal drive configurations are intentionally excluded from version control.

## System Architecture

There are two ways to use the system, and both act on the same database and the same configuration.

1. **Bristol (`src/tools/bristol/`)** 
   A PySide6 desktop app: a Kanban board over `tickets.db`. You read the board, create and edit tickets, move them between columns, and attach links and images by hand, without an agent involved.

2. **The Claude session (`src/app.md`)** 
   A markdown-defined initialization pipeline. Claude reads `src/app.md`, resolves the local config, takes on one agent identity from the registry, restores state from `tickets.db`, and works the board. It is the surface that edits files and executes work.

Whichever surface acts, the other sees the change on its next read. `src/tools/` also holds the rest of the standalone utilities — schema tools, scrapers, renderers — each independently runnable.

## Repository Structure

├── requirements.in             # Dependency inputs, compiled to requirements.txt
├── requirements.txt            # Python dependencies (see docs/SETUP.md)
├── docs/                       # Setup and other documentation beyond this README
│   └── SETUP.md
├── src/
│   ├── app.md                  # Claude session initialization pipeline
│   ├── tools/                  # Standalone local scripts and UIs, incl. Bristol
│   ├── agent_identities/       # Operating mandates for the agent fleet
│   ├── protocols/              # Standard operating procedures
│   ├── playbooks/              # Execution steps for specific agent tasks
│   └── templates/              # Provisioning templates for new agents and docs
├── config/                     # (Git-ignored) Local path resolution mapping
│   └── config.local.json       # The only file here: paths, agent registry, active_agent,
│                               # and the personal software `stack` block
└── data/                       # (Git-ignored) Cross-session database state
    └── <instance>/tickets/tickets.db   # The SQLite single source of truth (one per instance)

## Configuration & State Management

To run this application locally, you must establish the links between the generic repository logic and your specific hardware.

* **Configuration (`/config`):** You must define `config/config.local.json` — the single structured source of truth — to resolve the pointers to your personal directories and targeted external drives. The tracked repository code uses generic relative paths (e.g., `data/*/tickets/tickets.db`) which map to this local config. Read individual fields with `python3 src/tools/config_tools/read_config.py <dotted.key>`.
* **State (`/data`):** The system relies on a JIRA-like SQLite database (`tickets.db`). Agents are strictly forbidden from maintaining parallel markdown ledgers for task tracking. The database is the ultimate, machine-readable cross-session memory. 

## Getting Started

See `docs/SETUP.md` for the full walkthrough (dependencies, non-pip system
packages, config, and DB init). Short version:

```bash
pip install pip-tools
pip-compile requirements.in
pip install -r requirements.txt
# + a couple of post-install/system steps — see docs/SETUP.md §3
# create config/config.local.json — see docs/SETUP.md §5
python3 src/tools/ticket_tools/create_tickets.py --instance <your_instance_name>
```