"""smoke_targets/check_notebook_access.py — the `notebook_access` smoke target, run by smoke.py."""

from __future__ import annotations

import sys

from qt_headless import TOOLS
from smoke_targets.failure import SmokeFailure


def check_notebook_access() -> list[str]:
    """What an agent may do in the notebook, and every location config contains.

    Pure functions over a configuration kept in memory, so nothing on disk is
    read or written.
    """
    sys.path.insert(0, str(TOOLS / "config_tools"))
    import locations
    import notebook

    ok: list[str] = []
    data = {
        "markdown_notebook": {
            "notes_dir": "/nb",
            "folders": ["inbox", "journal", "journal/private"],
        },
        "agents": {
            "a": {
                "notebook_access": {
                    "mode": "per_folder",
                    "folders": {
                        "inbox": "write",
                        "journal": "read",
                        "journal/private": "hide",
                        "gone": "write",
                    },
                }
            }
        },
    }
    folders = notebook.attached(data)
    entry = data["agents"]["a"]["notebook_access"]
    if notebook.effective(entry, folders) != {
        "inbox": "write",
        "journal": "read",
        "journal/private": "hide",
    }:
        raise SmokeFailure("a choice for a folder that is not attached was honoured")
    if (
        notebook.may(entry, folders, "journal/private/x.md") != "hide"
        or notebook.may(entry, folders, "journal/2026/x.md") != "read"
        or notebook.may(entry, folders, "elsewhere/x.md") != "hide"
    ):
        raise SmokeFailure("the deepest attached folder does not decide a path")
    ok.append("per folder: the deepest attached folder decides, and unattached is hidden")

    notebook.set_access("a", "read_all", None, data)
    if notebook.may(data["agents"]["a"]["notebook_access"], folders, "elsewhere/x.md") != "read":
        raise SmokeFailure("Read All does not reach the whole notebook")
    notebook.set_access("a", "per_folder", None, data)
    if notebook.effective(data["agents"]["a"]["notebook_access"], folders)["inbox"] != "write":
        raise SmokeFailure("a per-folder choice was lost going through Read All")
    ok.append("Read All reaches everything, and Per Folder comes back with its choices")

    notebook.detach("journal", data)
    if "journal" in data["agents"]["a"]["notebook_access"][
        "folders"
    ] or "journal" in notebook.attached(data):
        raise SmokeFailure("detaching a folder left it with an agent")
    notebook.repoint("/other", data)
    if notebook.attached(data) or data["agents"]["a"]["notebook_access"]["folders"]:
        raise SmokeFailure("repointing the notebook kept the old notebook's folders")
    if data["agents"]["a"]["notebook_access"]["mode"] != "per_folder":
        raise SmokeFailure("repointing the notebook changed an agent's mode")
    ok.append("detaching drops a folder from every agent; repointing clears the list")

    found: list = []
    locations._walk(
        {
            "markdown_notebook": {
                "notes_dir": "/nb",
                "folders": ["x"],
                "reports_dir": "/nb/reports",
            },
            "important_paths": {"tickets_db": "data/i/tickets.db"},
            "agents": {
                "a": {
                    "identity": "src/agent_identities/a.md",
                    "env": {"HOME_DIR": "/somewhere", "MODE": "fast"},
                    "key_data_paths": [{"path": "data/i/a", "access": "write"}],
                }
            },
            "keyword_scan": {"keywords": ["x/y"]},
        },
        [],
        found,
    )
    got = {tuple(p) for p, _ in found}
    wanted = {
        ("markdown_notebook", "reports_dir"),
        ("important_paths", "tickets_db"),
        ("agents", "a", "identity"),
        ("agents", "a", "env", "HOME_DIR"),
        ("agents", "a", "key_data_paths", 0, "path"),
    }
    if got != wanted:
        raise SmokeFailure(f"Locations lists the wrong keys: {sorted(got ^ wanted)}")
    ok.append(
        "Locations lists every path config contains and nothing else, "
        "leaving the notebook folder to the Notebook window"
    )
    return ok
