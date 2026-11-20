"""smoke_targets/check_dashboard_access.py — the `dashboard_access` smoke target, run by smoke.py."""

from __future__ import annotations

import sys

from qt_headless import TOOLS
from smoke_targets.failure import SmokeFailure


def check_dashboard_access() -> list[str]:
    """Which dashboards an agent may write. Pure functions over a configuration
    kept in memory, so nothing on disk is read or written."""
    sys.path.insert(0, str(TOOLS / "config_tools"))
    import dashboards

    ok: list[str] = []
    data = {
        "dashboards": [{"name": "A", "url": "u"}, {"name": "B"}],
        "agents": {
            "x": {},
            "chief_of_staff": {"dashboard_access": {"write_all": False, "dashboards": []}},
        },
    }
    known = dashboards.names(data)
    if dashboards.writable("x", data["agents"]["x"].get("dashboard_access"), known) != ["A", "B"]:
        raise SmokeFailure("an agent with no entry does not write to every dashboard")
    if dashboards.writable(
        "chief_of_staff", data["agents"]["chief_of_staff"]["dashboard_access"], known
    ) != ["A", "B"]:
        raise SmokeFailure("chief_of_staff lost a dashboard to its toggle")
    ok.append("no entry writes to all, and chief_of_staff writes to all whatever it says")

    dashboards.set_access("x", False, ["B"], data)
    entry = data["agents"]["x"]["dashboard_access"]
    if dashboards.writable("x", entry, known) != ["B"]:
        raise SmokeFailure("with Write to All off, the chosen list is not what decides")
    dashboards.set_access("x", True, None, data)
    dashboards.set_access("x", False, None, data)
    if data["agents"]["x"]["dashboard_access"]["dashboards"] != ["B"]:
        raise SmokeFailure("the chosen list was lost going through Write to All")
    ok.append("off, the chosen dashboards decide, and they survive the toggle")

    dashboards.remove("B", data)
    if data["agents"]["x"]["dashboard_access"]["dashboards"] or "B" in dashboards.names(data):
        raise SmokeFailure("removing a dashboard left it with an agent")
    if dashboards.normalised({"dashboards": ["nope"]}, ["A"])["dashboards"]:
        raise SmokeFailure("a name that is not a known dashboard was honoured")
    ok.append("removing a dashboard drops it from every agent; unknown names are ignored")
    return ok
