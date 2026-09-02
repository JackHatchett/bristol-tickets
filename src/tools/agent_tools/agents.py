#!/usr/bin/env python3
"""agents.py — read an agent that exists, and change what it says.

`create_agent.py` writes an agent that is not there yet. This reads the ones
that are, and edits them. The two are separate because creating checks that
nothing is in the way and editing checks that something is.

An agent is a charter under `src/agent_identities/` and an entry in the
git-ignored config. Both are written here, in one call, so a change cannot land
in one and not the other, and nothing is written until every change checks.

The charter is a Markdown document and is read and written whole. Nothing here
parses it into fields: a charter is prose a person wrote, and a tool that
recognized only the shapes it produces itself would refuse to edit the ones that
matter most.

Every key an entry holds travels through an edit, including one this build knows
nothing about, so an agent edited here keeps everything it had.

GitHub-safe: contains no personal data or absolute user paths.

CLI
---
    python3 agents.py list [--json]
    python3 agents.py read <slug> [--json]
    python3 agents.py skeleton <slug>
    python3 agents.py edit <slug> [options]

`edit` writes only the options given. A repeatable option that is given at all
replaces that whole list; its `--no-…` partner empties one.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "config_tools"))
sys.path.insert(0, str(HERE.parents[0] / "skill_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402
import write_config  # noqa: E402

# The keys this build gives a control of its own. Any other key an entry holds
# is carried in `extra` and written back unchanged.
KNOWN = ("identity", "description", "key_data_paths", "key_context_files",
         "notebook_access", "skills", "env")
IDENTITY_DIR = "src/agent_identities"


class EditError(Exception):
    """A change that cannot land. Nothing is written when one is raised."""


# ── Reading ──────────────────────────────────────────────────────────────────

def charter_path(declared: str) -> Path:
    return data_paths.project_root() / declared


def read_agent(slug: str) -> dict:
    """One agent, whole: its charter document and every key of its entry."""
    entry = read_config.get(f"agents.{slug}", None)
    if not isinstance(entry, dict):
        raise KeyError(slug)
    declared = entry.get("identity", f"{IDENTITY_DIR}/{slug}.md")
    path = charter_path(declared)
    try:
        charter = path.read_text(encoding="utf-8")
        charter_error = ""
    except OSError as exc:
        charter, charter_error = "", str(exc)
    notebook = entry.get("notebook_access")
    return {
        "slug": slug,
        "identity": declared,
        "charter": charter,
        "charter_error": charter_error,
        "description": entry.get("description", ""),
        "key_data_paths": list(entry.get("key_data_paths") or []),
        "key_context_files": list(entry.get("key_context_files") or []),
        "notebook_access": dict(notebook) if isinstance(notebook, dict) else {},
        "skills": list(entry.get("skills") or []),
        "env": dict(entry.get("env") or {}),
        "extra": {k: v for k, v in entry.items() if k not in KNOWN},
    }


def list_agents() -> list[dict]:
    configured = read_config.get("agents", {})
    return [read_agent(slug) for slug in configured if slug != "_notes"]


GUIDANCE = re.compile(r"\{\{.*?\}\}", re.S)
FENCE = re.compile(r"## The skeleton\s*\n+```markdown\n(?P<body>.*?)\n```", re.S)


def skeleton(slug: str) -> str:
    """The starting charter for a new agent, from the template that owns it.

    `src/templates/identity_template.md` §The skeleton holds the one copy of
    what a charter looks like. Its `{{…}}` spans are notes to whoever writes
    one; they are dropped here, leaving the headings and the fixed reference
    lines for the author to fill in.
    """
    template = (data_paths.project_root() / "src" / "templates"
                / "identity_template.md")
    found = FENCE.search(template.read_text(encoding="utf-8"))
    if found is None:
        raise EditError(f"{template.name} carries no skeleton to start from")
    body = GUIDANCE.sub("", found.group("body"))
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body.replace("<agent>", slug) + "\n"


# ── Writing ──────────────────────────────────────────────────────────────────

def _checked_identity(slug: str, declared: str, current: str) -> Path:
    if declared == current:
        return charter_path(declared)
    if not declared.endswith(".md"):
        raise EditError(f"a charter is a Markdown file: '{declared}' is not")
    if Path(declared).is_absolute() or ".." in Path(declared).parts:
        raise EditError(
            f"a charter lives inside the repository: '{declared}' does not")
    destination = charter_path(declared)
    if destination.exists():
        raise EditError(f"{declared} already exists")
    return destination


def edit(slug: str, changes: dict) -> dict:
    """Apply `changes` to one agent. Returns what was written.

    Every change is checked before the first write, so a refused edit leaves the
    charter and the config entry exactly as they were.
    """
    current = read_agent(slug)
    entry = dict(read_config.get(f"agents.{slug}"))

    charter = changes.get("charter", current["charter"])
    declared = changes.get("identity", current["identity"])
    if "charter" in changes and not charter.strip():
        raise EditError("an agent with no charter is not an agent")
    if "description" in changes and not changes["description"].strip():
        raise EditError("an agent with no description is not an agent")
    destination = _checked_identity(slug, declared, current["identity"])

    written = []
    moving = declared != current["identity"]
    if moving:
        destination.parent.mkdir(parents=True, exist_ok=True)
    if "charter" in changes or moving:
        destination.write_text(charter, encoding="utf-8")
        written.append(declared)
    if moving:
        was = charter_path(current["identity"])
        if was.exists():
            was.unlink()
        entry["identity"] = declared

    for key in ("description", "key_data_paths", "key_context_files",
                "notebook_access", "env"):
        if key in changes:
            entry[key] = changes[key]
    if "extra" in changes:
        for key in list(entry):
            if key not in KNOWN:
                del entry[key]
        entry.update(changes["extra"])

    touches_config = moving or any(
        k in changes for k in ("description", "key_data_paths",
                               "key_context_files", "notebook_access", "env",
                               "extra"))
    if touches_config:
        write_config.set_key(f"agents.{slug}", entry)
        written.append(f"agents.{slug}")
    return {"slug": slug, "written": written}


# ── CLI ──────────────────────────────────────────────────────────────────────

def _render(agent: dict) -> str:
    notebook = agent["notebook_access"]
    lines = [agent["slug"],
             f"  {agent['description']}",
             f"  charter    {agent['identity']} "
             f"({len(agent['charter'].splitlines())} lines)"]
    for declared in agent["key_data_paths"]:
        lines.append(f"  data       {declared}")
    for declared in agent["key_context_files"]:
        lines.append(f"  context    {declared}")
    lines.append(f"  notebook   read={bool(notebook.get('read'))} "
                 f"write_zones={','.join(notebook.get('write_zones') or []) or '-'} "
                 f"archive_moves={bool(notebook.get('archive_moves'))}")
    for name, value in agent["env"].items():
        lines.append(f"  env        {name}={value}")
    for name in agent["skills"]:
        lines.append(f"  skill      {name}")
    for key in agent["extra"]:
        lines.append(f"  {key}")
    if agent["charter_error"]:
        lines.append(f"  UNREADABLE {agent['charter_error']}")
    return "\n".join(lines)


def _pairs(given: list[str]) -> dict:
    out = {}
    for item in given:
        name, sep, value = item.partition("=")
        if not sep or not name.strip():
            raise EditError(f"an environment entry is NAME=value: '{item}' is not")
        out[name.strip()] = value
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subs = parser.add_subparsers(dest="command", required=True)

    listing = subs.add_parser("list", help="every configured agent")
    listing.add_argument("--json", action="store_true")

    reading = subs.add_parser("read", help="one agent, whole")
    reading.add_argument("slug")
    reading.add_argument("--json", action="store_true")

    starting = subs.add_parser("skeleton", help="a starting charter")
    starting.add_argument("slug")

    editing = subs.add_parser("edit", help="change what one agent says")
    editing.add_argument("slug")
    editing.add_argument("--identity", help="where the charter file lives")
    editing.add_argument("--description")
    editing.add_argument("--charter-file",
                         help="a file holding the whole charter document")
    editing.add_argument("--data-path", action="append")
    editing.add_argument("--no-data-paths", action="store_true")
    editing.add_argument("--context-file", action="append")
    editing.add_argument("--no-context-files", action="store_true")
    editing.add_argument("--notebook-read", choices=("yes", "no"))
    editing.add_argument("--write-zone", action="append")
    editing.add_argument("--no-write-zones", action="store_true")
    editing.add_argument("--archive-moves", choices=("yes", "no"))
    editing.add_argument("--env", action="append", metavar="NAME=VALUE")
    editing.add_argument("--no-env", action="store_true")
    editing.add_argument("--extra-file",
                         help="a JSON object replacing every other key")
    args = parser.parse_args(argv)

    if args.command == "list":
        agents = list_agents()
        if args.json:
            print(json.dumps(agents, indent=2))
        else:
            print("\n\n".join(_render(a) for a in agents) or "no agents")
        return 0

    if args.command == "skeleton":
        try:
            print(skeleton(args.slug), end="")
        except EditError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    try:
        agent = read_agent(args.slug)
    except KeyError:
        print(f"'{args.slug}' is not a configured agent. `agents.py list` "
              f"names the ones that are.", file=sys.stderr)
        return 1

    if args.command == "read":
        print(json.dumps(agent, indent=2) if args.json else _render(agent))
        return 0

    changes: dict = {}
    try:
        if args.identity is not None:
            changes["identity"] = args.identity.strip()
        if args.description is not None:
            changes["description"] = args.description.strip()
        if args.charter_file is not None:
            changes["charter"] = Path(args.charter_file).read_text(
                encoding="utf-8")
        if args.data_path:
            changes["key_data_paths"] = args.data_path
        elif args.no_data_paths:
            changes["key_data_paths"] = []
        if args.context_file:
            changes["key_context_files"] = args.context_file
        elif args.no_context_files:
            changes["key_context_files"] = []
        if args.env:
            changes["env"] = _pairs(args.env)
        elif args.no_env:
            changes["env"] = {}
        if args.extra_file is not None:
            loaded = json.loads(Path(args.extra_file).read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise EditError("--extra-file holds a JSON object or nothing")
            changes["extra"] = loaded

        notebook = dict(agent["notebook_access"])
        touched = False
        if args.notebook_read is not None:
            notebook["read"] = args.notebook_read == "yes"
            touched = True
        if args.write_zone:
            notebook["write_zones"] = args.write_zone
            touched = True
        elif args.no_write_zones:
            notebook["write_zones"] = []
            touched = True
        if args.archive_moves is not None:
            notebook["archive_moves"] = args.archive_moves == "yes"
            touched = True
        if touched:
            changes["notebook_access"] = notebook

        if not changes:
            print("nothing to change; name at least one field.", file=sys.stderr)
            return 1
        done = edit(args.slug, changes)
    except (EditError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for where in done["written"]:
        print(f"Wrote     {where}")
    if not done["written"]:
        print("Nothing changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
