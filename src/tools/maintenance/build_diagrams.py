#!/usr/bin/env python3

import os
import sys
import json
from pathlib import Path



def _instance_dir() -> Path:
    """The single data/<instance>/ folder. The instance name is the user's, so
    it is discovered rather than named here."""
    data_root = _project_root() / "data"
    candidates = sorted(p for p in data_root.glob("*") if p.is_dir())
    if not candidates:
        raise SystemExit(
            f"no instance folder under {data_root} — run create_tickets.py first"
        )
    return candidates[0]


def _project_root() -> Path:
    """The project root: the nearest ancestor holding src/app.md.

    Located by marker rather than by folder name, so the install works whatever
    the user named the folder they cloned into.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "app.md").is_file():
            return parent
    raise SystemExit(
        "no project root above this file (no ancestor holds src/app.md)"
    )


# ---------------------------------------------------------------------------
# Load config.local.json. Default: resolved relative to this script's own
# location (RUNTIME_ROOT.parent / "config" / "config.local.json") — no
# hardcoded user path. An explicit path may still be passed as argv[1] to
# override (e.g. for a non-standard checkout).
# ---------------------------------------------------------------------------

RUNTIME_ROOT = _project_root() / "src"
DEFAULT_INDEX_PATH = _project_root() / "config" / "config.local.json"

explicit_arg = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
INDEX_PATH = Path(explicit_arg) if explicit_arg else DEFAULT_INDEX_PATH

if not INDEX_PATH.exists():
    sys.stderr.write("ERROR: config.local.json not found at: " + str(INDEX_PATH) + "\n")
    sys.stderr.write("Usage: build_diagrams.py [/path/to/config.local.json] [--check]\n")
    sys.exit(1)

with open(INDEX_PATH) as f:
    INDEX = json.load(f)

# ---------------------------------------------------------------------------
# Resolve diagrams directory under the discovered instance folder.
# ---------------------------------------------------------------------------

DIAGRAMS_DIR = str(_instance_dir() / "system" / "diagrams")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HEADER = (
    "%% GENERATED — DO NOT EDIT.\n"
    "%% Source: config.local.json\n"
)

def safe_id(name):
    return "".join(ch for ch in name if ch.isalnum())

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# ---------------------------------------------------------------------------
# Agents & Knowledge System Diagram
# ---------------------------------------------------------------------------

def build_agents_diagram(index):
    agents = index.get("agents", {})
    tools = index.get("tools", {})
    playbooks = index.get("playbooks", {})
    protocols = index.get("protocols", {})
    projects = index.get("projects", {})

    lines = [HEADER, "flowchart LR", ""]

    lines.append("subgraph Agents")
    for agent_name in agents.keys():
        aid = safe_id(agent_name)
        lines.append(f'    {aid}(["{agent_name}"])')
    lines.append("end\n")

    lines.append("subgraph Tools")
    for tool_path in tools.get("files", []):
        tid = safe_id(tool_path)
        lines.append(f'    {tid}(["{tool_path}"])')
    lines.append("end\n")

    lines.append("subgraph Playbooks")
    for pb_path in playbooks.get("files", []):
        pid = safe_id(pb_path)
        lines.append(f'    {pid}(["{pb_path}"])')
    lines.append("end\n")

    lines.append("subgraph Protocols")
    for pr_path in protocols.get("files", []):
        prid = safe_id(pr_path)
        lines.append(f'    {prid}(["{pr_path}"])')
    lines.append("end\n")

    lines.append("subgraph Projects")
    for p in projects.get("notebook_projects", []):
        pid = safe_id(p)
        lines.append(f'    {pid}(["{p}"])')
    lines.append("end\n")

    for agent_name, agent_info in agents.items():
        if agent_name.startswith("_") or not isinstance(agent_info, dict):
            continue
        identity = agent_info.get("identity")
        if identity:
            aid = safe_id(agent_name)
            iid = safe_id(identity)
            lines.append(f'{aid} -->|"identity"| {iid}')

    return "\n".join(lines) + "\n"

# ---------------------------------------------------------------------------
# Infrastructure Diagram
# ---------------------------------------------------------------------------

def _stack_item_names(items):
    """Yield display names from a stack category, tolerant of schema shape.

    Current schema: a category maps to {item_name: {details...}} (dict).
    Back-compat: a list of {"name": ...} dicts, or a list of bare strings.
    """
    if isinstance(items, dict):
        return [k for k in items if not k.startswith("_")]
    if isinstance(items, list):
        return [i.get("name") if isinstance(i, dict) else i for i in items]
    return [str(items)]


def build_infrastructure_diagram(index):
    drives = index.get("drives", {})
    stack = index.get("stack", {})

    lines = [HEADER, "flowchart LR", ""]

    lines.append("subgraph Drives")
    for drive_name in (k for k in drives if not k.startswith("_")):
        did = safe_id(drive_name)
        lines.append(f'    {did}(["{drive_name}"])')
    lines.append("end\n")

    lines.append("subgraph Stack")
    if isinstance(stack, dict):
        # Nested: one sub-group per category, item nodes inside.
        for category, items in stack.items():
            if category.startswith("_"):
                continue
            cid = safe_id(category)
            lines.append(f'    subgraph {cid}["{category}"]')
            for name in _stack_item_names(items):
                nid = safe_id(f"{category}_{name}")
                lines.append(f'        {nid}(["{name}"])')
            lines.append("    end")
    else:
        # Flat back-compat shape: a list of items directly under Stack.
        for name in _stack_item_names(stack):
            sid = safe_id(name)
            lines.append(f'    {sid}(["{name}"])')
    lines.append("end\n")

    return "\n".join(lines) + "\n"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    check = "--check" in sys.argv

    ensure_dir(DIAGRAMS_DIR)

    outputs = {
        "agents.mmd": build_agents_diagram(INDEX),
        "infrastructure.mmd": build_infrastructure_diagram(INDEX),
    }

    stale = []

    for filename, content in outputs.items():
        path = os.path.join(DIAGRAMS_DIR, filename)
        existing = None

        if os.path.exists(path):
            with open(path) as f:
                existing = f.read()

        if check:
            if existing != content:
                stale.append(filename)
        else:
            with open(path, "w") as f:
                f.write(content)
            print("wrote " + path)

    if check:
        if stale:
            sys.stderr.write("DIAGRAM DRIFT: " + ", ".join(stale) + "\n")
            sys.exit(1)
        print("diagrams up to date.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
