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

### Design constraints

* **The tools stay small and separately runnable.** `src/tools/` is a set of independent programs, each readable and modifiable in a single pass. They are not consolidated into one program, and a launcher that presents several of them composes them rather than fusing their codebases.
* **Bristol is self-contained.** `src/tools/bristol/` imports nothing from the rest of `src/tools/`. It opens, runs and changes in isolation, without requiring an understanding of the rest of the system.
* **Legibility beats cleverness.** The repo is written to be read by people learning to build alongside AI. The data and config contract is explicit and inspectable, separation of concerns is stated plainly rather than through metaphor, and a clever construction that costs a reader is the wrong choice.

## Repository Structure

├── requirements.in             # Dependency inputs, compiled to requirements.txt
├── requirements.txt            # Python dependencies (see docs/install.md)
├── docs/                       # The user manual (start at docs/index.md)
├── src/
│   ├── app.md                  # Claude session initialization pipeline
│   ├── tools/                  # Standalone local scripts and UIs, incl. Bristol
│   ├── agent_identities/       # Operating mandates for the agent fleet
│   ├── protocols/              # Standard operating procedures
│   ├── playbooks/              # Execution steps for specific agent tasks
│   └── templates/              # Provisioning templates for new agents and docs
├── config/                     # Local path resolution mapping (contents git-ignored)
│   ├── config.example.json     # Tracked template: every key, placeholder values
│   └── config.local.json       # Your real file: paths, agent registry, active_agent,
│                               # and the personal software `stack` block
└── data/                       # (Git-ignored) Cross-session database state
    └── <instance>/tickets/tickets.db   # The SQLite single source of truth (one per instance)

## Configuration & State Management

To run this application locally, you must establish the links between the generic repository logic and your specific hardware.

* **Configuration (`/config`):** Copy `config/config.example.json` to `config/config.local.json` — the single structured source of truth — and fill in the placeholders to resolve the pointers to your personal directories and targeted external drives. The tracked repository code uses generic relative paths (e.g., `data/*/tickets/tickets.db`) which map to this local config. Read individual fields with `python3 src/tools/config_tools/read_config.py <dotted.key>`.
* **State (`/data`):** The system relies on a JIRA-like SQLite database (`tickets.db`). Agents are strictly forbidden from maintaining parallel markdown ledgers for task tracking. The database is the ultimate, machine-readable cross-session memory. 

## Getting Started

See `docs/install.md` for the full walkthrough — the Claude Desktop and Cowork
prerequisite, dependencies, non-pip system packages, and the first-run setup
wizard. Short version:

```bash
pip install -r requirements.txt
python3 src/tools/bristol/app.py    # opens the setup wizard on first run
```

Setting up by hand instead of using the wizard, and every configuration key:
`docs/configuration.md`.