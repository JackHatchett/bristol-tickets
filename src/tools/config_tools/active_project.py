#!/usr/bin/env python3
"""active_project.py — which project a session opens on.

An agent's projects are the entries of `projects.notebook_projects` and
`projects.local_projects` that sit at or under one of the folders the agent is
granted in `agents.<slug>.key_data_paths`. A session opens on one of them by
this rule, and names it before reading any of its content:

1. `agents.<slug>.active_project`, where it names one of the agent's projects;
2. otherwise the agent's first project, in the order config lists them.

An agent with one project always opens on it. An agent with none has nothing to
open, and the session asks which folder is meant.

When the user says he is working the other project, the session moves with
`--set`, which writes `agents.<slug>.active_project` into the git-ignored
config, so the choice holds for later sessions and no tracked file changes.

CLI
---
    python3 active_project.py writers_room
        -> obsidian_notes/30_chiropterad  (the only project)
    python3 active_project.py writers_room --list
    python3 active_project.py writers_room --set obsidian_notes/31_other_novel

Exit status is non-zero when the agent has no project, or `--set` names a folder
that is not one of its projects.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_paths  # noqa: E402
import read_config  # noqa: E402
import write_config  # noqa: E402


def _under(path: str, folder: str) -> bool:
    path, folder = path.strip("/"), folder.strip("/")
    return path == folder or path.startswith(folder + "/")


def projects(slug: str, *, data: dict | None = None) -> list[str]:
    """The agent's projects, in the order config lists them."""
    listed = [*read_config.get("projects.notebook_projects", [], data=data),
              *read_config.get("projects.local_projects", [], data=data)]
    grants = data_paths.folder_grants(
        read_config.get(f"agents.{slug}.key_data_paths", [], data=data))
    return [p for p in listed
            if any(_under(p, grant["path"]) for grant in grants)]


def active(slug: str, *, data: dict | None = None) -> tuple[str | None, str]:
    """The project a session opens on, and why it is that one."""
    mine = projects(slug, data=data)
    if not mine:
        return None, "no project is configured for this agent"
    if len(mine) == 1:
        return mine[0], "the only project"
    chosen = read_config.get(f"agents.{slug}.active_project", None, data=data)
    if chosen in mine:
        return chosen, "the one last chosen"
    return mine[0], "the first listed, none having been chosen"


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print("usage: active_project.py <agent slug> [--list | --set <project>]",
              file=sys.stderr)
        return 2
    slug, rest = argv[0], argv[1:]
    if rest[:1] == ["--list"]:
        for p in projects(slug):
            print(p)
        return 0
    if rest[:1] == ["--set"] and len(rest) == 2:
        target = rest[1].strip("/")
        if target not in projects(slug):
            print(f"active_project: {target} is not one of {slug}'s projects",
                  file=sys.stderr)
            return 1
        write_config.set_key(f"agents.{slug}.active_project", target)
        print(f"{target}  (chosen)")
        return 0
    project, why = active(slug)
    if project is None:
        print(f"active_project: {why}", file=sys.stderr)
        return 1
    print(f"{project}  ({why})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
