"""smoke_targets/check_config_resolution.py — the `config_resolution` smoke target, run by smoke.py."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from qt_headless import TOOLS, tool_on_path
from smoke_targets.failure import SmokeFailure


def check_config_resolution() -> list[str]:
    """Which configuration file the app reads.

    The instance pointer outranks the tree the app runs from, so a pointer left
    by an installation that is gone would make every configured field read as
    absent while a good configuration sat beside the running code.
    """

    ok: list[str] = []
    tool_on_path("bristol")
    import config_file
    import instance

    orig_get_path = instance.get_path
    orig_project_root = config_file.project_root
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            live = root / "config" / "config.local.json"
            live.write_text(
                '{"active_agent": "chief_of_staff", '
                '"agents": {"chief_of_staff": {}, "librarian": {}}}'
            )
            config_file.project_root = lambda: root

            gone = root / "removed" / "config" / "config.local.json"
            instance.get_path = lambda key: gone if key == "config_path" else None
            if config_file.path() != live:
                raise SmokeFailure(
                    "a pointer naming a config that is not there won over the "
                    "one beside the running tree"
                )
            if config_file.agent_slugs() != ["chief_of_staff", "librarian"]:
                raise SmokeFailure("the configured agents did not survive a stale pointer")
            ok.append("a stale instance pointer does not hide the configuration in use")

            other = root / "elsewhere" / "config.local.json"
            other.parent.mkdir(parents=True)
            other.write_text("{}")
            instance.get_path = lambda key: other if key == "config_path" else None
            if config_file.path() != other:
                raise SmokeFailure("a pointer naming a real config was ignored")
            ok.append("a pointer naming a config that exists still wins")
    finally:
        instance.get_path = orig_get_path
        config_file.project_root = orig_project_root

    # Which project a session opens on, when an agent has one, two or none.
    sys.path.insert(0, str(TOOLS / "config_tools"))
    import active_project

    def grant(p):
        return {"path": p, "access": "write"}

    cfg = {
        "projects": {
            "notebook_projects": ["notes/novel_a", "notes/novel_b", "notes/course"],
            "local_projects": [],
        },
        "agents": {
            "writer": {"key_data_paths": [grant("notes/novel_a")]},
            "nobody": {"key_data_paths": [grant("data/x")]},
        },
    }
    if active_project.active("writer", data=cfg) != ("notes/novel_a", "the only project"):
        raise SmokeFailure("one project did not open as it always has")
    cfg["agents"]["writer"]["key_data_paths"].append(grant("notes/novel_b"))
    if active_project.active("writer", data=cfg)[0] != "notes/novel_a":
        raise SmokeFailure("two projects and no choice did not open on the first")
    cfg["agents"]["writer"]["active_project"] = "notes/novel_b"
    if active_project.active("writer", data=cfg)[0] != "notes/novel_b":
        raise SmokeFailure("a chosen project did not stay")
    cfg["agents"]["writer"]["active_project"] = "notes/course"
    if active_project.active("writer", data=cfg)[0] != "notes/novel_a":
        raise SmokeFailure("a choice outside the agent's projects was honoured")
    if active_project.active("nobody", data=cfg)[0] is not None:
        raise SmokeFailure("an agent with no project was given one")
    ok.append(
        "a session opens on its only project, on the chosen one of two, "
        "and on none where it has none"
    )

    # An environment value written as a reference resolves through the key
    # that owns its folder, and Locations lists that folder once.
    import json as _json
    import os as _os

    import data_paths
    import locations

    with tempfile.TemporaryDirectory() as tmp:
        logs = Path(tmp) / "logs"
        logs.mkdir()
        cfg_path = Path(tmp) / "config.local.json"
        cfg_path.write_text(
            _json.dumps(
                {
                    "bristol_data": {"folders": {"logs": str(logs)}},
                    "personal_db": {
                        "env": {"PERSONAL_SNAPSHOT_BASE": "@bristol_data.folders.logs"}
                    },
                    "agents": {
                        "a": {
                            "env": {
                                "SNAP": "@personal_db.env.PERSONAL_SNAPSHOT_BASE/applications_snapshots",
                                "NAME": "personal.db",
                                "LOOP": "@agents.a.env.LOOP",
                                "GONE": "@nowhere.at_all",
                            }
                        }
                    },
                }
            )
        )
        saved = _os.environ.get("CONFIG_LOCAL_JSON")
        _os.environ["CONFIG_LOCAL_JSON"] = str(cfg_path)
        try:
            if data_paths.resolve("@personal_db.env.PERSONAL_SNAPSHOT_BASE") != logs:
                raise SmokeFailure("a reference to a reference did not reach the owning folder")
            env = data_paths.agent_env("a")
            if env.get("SNAP") != str(logs / "applications_snapshots"):
                raise SmokeFailure(f"a reference with a sub-path resolved to {env.get('SNAP')}")
            if env.get("NAME") != "personal.db":
                raise SmokeFailure("a value that is not a reference was changed")
            if "LOOP" in env or "GONE" in env:
                raise SmokeFailure("a looping or dangling reference was handed to a tool")
            at_logs = [r["label"] for r in locations.locations() if r["resolved"] == str(logs)]
            if len(at_logs) != 1:
                raise SmokeFailure(f"Locations lists the logs folder as {at_logs}")
        finally:
            if saved is None:
                _os.environ.pop("CONFIG_LOCAL_JSON", None)
            else:
                _os.environ["CONFIG_LOCAL_JSON"] = saved
    ok.append(
        "a reference resolves through the key that owns the folder, "
        "and Locations lists that folder once"
    )
    return ok
