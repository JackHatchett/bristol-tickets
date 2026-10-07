#!/usr/bin/env python3
"""dashboards.py — the dashboards Bristol knows about, and which of them each
agent may write.

A dashboard is a page an agent keeps up for the user, and the files behind it.
The known ones are `dashboards` in config, one entry each:

    {"name": "<what the user calls it>", "url": "<where it is published>",
     "paths": ["<a file that produces its data>", ...]}

What an agent may do with them is its `dashboard_access`:

    {"write_all": true | false, "dashboards": ["<name>", ...]}

- **An agent with no entry writes to every dashboard.** `write_all` is on until
  someone switches it off.
- **With `write_all` off, the agent writes to the dashboards listed and no
  other.** There is no read-only level: a dashboard is published, and anyone may
  read it.
- **`dashboards` is kept while `write_all` is on**, so switching it off again
  brings every choice back.
- **chief_of_staff writes to every dashboard whatever its entry says.**
- **Removing a dashboard drops it from every agent's list**, and a name that is
  not a known dashboard is ignored wherever it is read.

Writing to a dashboard an agent may write is ordinary work, and `src/app.md`
§Content is yours; behavior is chief_of_staff's says so.

CLI
---
    python3 dashboards.py show [--json]
    python3 dashboards.py access <agent> [--json]
    python3 dashboards.py add --name NAME --url URL [--path FILE ...]
    python3 dashboards.py remove NAME
    python3 dashboards.py set-access <agent> --all | --chosen [--dashboard NAME ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import read_config  # noqa: E402

ALWAYS_ALL = "chief_of_staff"


def _load() -> dict:
    return read_config.load()


def _save(data: dict) -> None:
    path = read_config.config_path()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def known(data: dict | None = None) -> list[dict]:
    """The known dashboards, in the order they were added."""
    data = _load() if data is None else data
    out = []
    for d in data.get("dashboards") or []:
        if isinstance(d, dict) and str(d.get("name", "")).strip():
            out.append({"name": str(d["name"]).strip(), "url": d.get("url", ""),
                        "paths": [p for p in d.get("paths") or [] if isinstance(p, str)]})
    return out


def names(data: dict | None = None) -> list[str]:
    return [d["name"] for d in known(data)]


def normalised(entry, dashboards: list[str]) -> dict:
    """An agent's access, ignoring names that are not known dashboards."""
    entry = entry if isinstance(entry, dict) else {}
    chosen = entry.get("dashboards") if isinstance(entry.get("dashboards"), list) else []
    return {"write_all": entry.get("write_all") is not False,
            "dashboards": [n for n in dashboards if n in chosen]}


def writable(slug: str, entry, dashboards: list[str]) -> list[str]:
    """The dashboards this agent may write."""
    access = normalised(entry, dashboards)
    if slug == ALWAYS_ALL or access["write_all"]:
        return list(dashboards)
    return access["dashboards"]


def add(name: str, url: str, paths: list[str] | None = None,
        data: dict | None = None) -> dict:
    data = _load() if data is None else data
    name = name.strip()
    if not name:
        raise SystemExit("dashboards: a dashboard needs a name")
    entries = [d for d in data.get("dashboards") or [] if isinstance(d, dict)]
    if any(str(d.get("name", "")).strip() == name for d in entries):
        raise SystemExit(f"dashboards: {name} is already known")
    entry = {"name": name, "url": url, "paths": list(paths or [])}
    entries.append(entry)
    data["dashboards"] = entries
    return entry


def remove(name: str, data: dict | None = None) -> bool:
    """Forget a dashboard, and drop it from every agent's list."""
    data = _load() if data is None else data
    entries = [d for d in data.get("dashboards") or [] if isinstance(d, dict)]
    kept = [d for d in entries if str(d.get("name", "")).strip() != name]
    if len(kept) == len(entries):
        return False
    data["dashboards"] = kept
    for agent in (data.get("agents") or {}).values():
        access = agent.get("dashboard_access") if isinstance(agent, dict) else None
        if isinstance(access, dict) and isinstance(access.get("dashboards"), list):
            access["dashboards"] = [n for n in access["dashboards"] if n != name]
    return True


def set_access(slug: str, write_all: bool, chosen: list[str] | None,
               data: dict | None = None) -> dict:
    """Set an agent's toggle, and its list where one is given. A list not given
    is kept, so switching the toggle never loses it."""
    data = _load() if data is None else data
    agent = (data.get("agents") or {}).get(slug)
    if not isinstance(agent, dict):
        raise SystemExit(f"dashboards: no agent {slug}")
    current = agent.get("dashboard_access")
    kept = list(current.get("dashboards") or []) if isinstance(current, dict) else []
    if chosen is not None:
        unknown = [n for n in chosen if n not in names(data)]
        if unknown:
            raise SystemExit(f"dashboards: not a known dashboard: {', '.join(unknown)}")
        kept = list(dict.fromkeys(chosen))
    agent["dashboard_access"] = {"write_all": bool(write_all), "dashboards": kept}
    return agent["dashboard_access"]


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("--json", action="store_true")
    a = sub.add_parser("access"); a.add_argument("agent")
    a.add_argument("--json", action="store_true")
    ad = sub.add_parser("add"); ad.add_argument("--name", required=True)
    ad.add_argument("--url", default="")
    ad.add_argument("--path", action="append", default=[],
                    help="a file that produces the dashboard's data; repeatable")
    sub.add_parser("remove").add_argument("name")
    sa = sub.add_parser("set-access"); sa.add_argument("agent")
    which = sa.add_mutually_exclusive_group(required=True)
    which.add_argument("--all", dest="write_all", action="store_true")
    which.add_argument("--chosen", dest="write_all", action="store_false")
    sa.add_argument("--dashboard", action="append", default=None,
                    help="a dashboard this agent may write; repeatable")
    args = p.parse_args(argv)

    data = _load()
    if args.cmd == "show":
        shown = known(data)
        if args.json:
            print(json.dumps(shown))
        else:
            for d in shown or []:
                print(f"{d['name']}  {d['url'] or '(no address)'}")
                for path in d["paths"]:
                    print(f"  {path}")
            if not shown:
                print("no dashboard is known")
        return 0
    if args.cmd == "access":
        agent = (data.get("agents") or {}).get(args.agent)
        if not isinstance(agent, dict):
            print(f"no agent {args.agent}", file=sys.stderr)
            return 1
        known_names = names(data)
        entry = agent.get("dashboard_access")
        out = {**normalised(entry, known_names),
               "writable": writable(args.agent, entry, known_names),
               "always_all": args.agent == ALWAYS_ALL}
        if args.json:
            print(json.dumps(out))
        else:
            mode = "all" if out["always_all"] or out["write_all"] else "chosen"
            print(f"{args.agent}  writes={mode}")
            for n in known_names:
                print(f"  {'write' if n in out['writable'] else '-':<6} {n}")
        return 0
    if args.cmd == "add":
        print(json.dumps(add(args.name, args.url, args.path, data)))
    elif args.cmd == "remove":
        print(f"removed {args.name}" if remove(args.name, data)
              else f"{args.name} was not known")
    elif args.cmd == "set-access":
        print(json.dumps(set_access(args.agent, args.write_all, args.dashboard, data)))
    _save(data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
