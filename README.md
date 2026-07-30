# Agentic System Architecture

A local, multi-agent simulation and orchestration layer designed to manage tasks, digital architecture, and file systems. 

This repository serves as the generic, forkable shell of the application. It provides the runtime architecture, agent identities, and structural modules required to operate the system. All user-specific runtime state, cloud backup targets, and personal drive configurations are intentionally excluded from version control.

## System Architecture

The ecosystem operates on a tri-interface architecture. All three interfaces share unified data and configuration layers, ensuring that whether a human, a local script, or an LLM is acting, the system state remains perfectly synchronized.

1. **The Python Application Head (`src/app.py`) — planned, not yet created** 
   The intended programmatic core: a structured, API-driven entry point that would eventually operate the entire system. No such file exists yet — this is a direction the other two heads are built against, not a runtime you can run.

2. **The Human / Tooling Head (`src/tools/...`)** 
   A collection of modular, standalone Python utilities (such as Bristol, the PySide6 roadmap-board GUI). These localized scripts allow a user to jack directly into specific databases and system states to verify schemas, edit Kanban boards, or execute protocols without agent mediation.

3. **The Cowork Head (`src/app.md`)** 
   A hierarchical, markdown-based runtime environment designed for Claude. It simulates the future programmatic API by reading documents in sequence and operating as a configured agent (e.g., Chief of Staff). It is the primary file-system editor, executing workflow state changes directly on the local machine.

For the engineering-depth treatment — how the surfaces share one data/config substrate, what is built versus planned (including a planned packaged Mac GUI), and the design principles behind keeping the tools fragmented — see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Repository Structure

├── requirements.in             # Dependency inputs, compiled to requirements.txt
├── requirements.txt            # Python dependencies (see docs/SETUP.md)
├── docs/                       # Setup and other documentation beyond this README
│   ├── ARCHITECTURE.md         # Engineering-depth design doc (multi-surface architecture)
│   └── SETUP.md
├── src/
│   ├── app.md                  # Head 3: Claude Cowork initialization pipeline
│   ├── tools/                  # Head 2: Modular local scripts and UIs
│   ├── agent_identities/       # Operating mandates for the agent fleet
│   ├── protocols/              # Standard operating procedures
│   ├── playbooks/              # Execution steps for specific agent tasks
│   └── templates/              # Provisioning templates for new agents and docs
├── config/                     # (Git-ignored) Local path resolution mapping
│   └── config.local.json       # The only file here: paths, agent registry, active_agent,
│                               # and the personal software `stack` block
└── data/                       # (Git-ignored) Cross-session database state
    └── <instance>/roadmap/roadmap.db   # The SQLite single source of truth (one per instance)

Head 1 (`src/app.py`) is planned and has no file in the tree.

## Configuration & State Management

To run this application locally, you must establish the links between the generic repository logic and your specific hardware.

* **Configuration (`/config`):** You must define `config/config.local.json` — the single structured source of truth — to resolve the pointers to your personal directories and targeted external drives. The tracked repository code uses generic relative paths (e.g., `data/*/roadmap/roadmap.db`) which map to this local config. Read individual fields with `python3 src/tools/config_tools/read_config.py <dotted.key>`.
* **State (`/data`):** The system relies on a JIRA-like SQLite database (`roadmap.db`). Agents are strictly forbidden from maintaining parallel markdown ledgers for task tracking. The database is the ultimate, machine-readable cross-session memory. 

## Getting Started

See `docs/SETUP.md` for the full walkthrough (dependencies, non-pip system
packages, config, and DB init). Short version:

```bash
pip install pip-tools
pip-compile requirements.in
pip install -r requirements.txt
# + a couple of post-install/system steps — see docs/SETUP.md §3
# create config/config.local.json — see docs/SETUP.md §5
python3 src/tools/roadmap_tools/create_roadmap.py --instance <your_instance_name>
```