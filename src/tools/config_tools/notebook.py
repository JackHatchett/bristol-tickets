#!/usr/bin/env python3
"""notebook.py — the Markdown notebook Bristol knows about, and what each agent
may do in it.

The notebook is one folder (`markdown_notebook.notes_dir`) and a list of its
subfolders Bristol has been told about (`markdown_notebook.folders`, each
written from the notebook down, `/` between parts). Nothing outside an attached
folder exists to an agent working folder by folder. The notebook itself can be
repointed and never removed; repointing clears the list, because the folders of
one notebook mean nothing in another.

What an agent may do there is its `notebook_access`:

    {"mode": "per_folder" | "read_all" | "write_all",
     "folders": {"<attached folder>": "read" | "write" | "hide", ...}}

- **read_all and write_all reach the whole notebook**, attached or not.
- **per_folder reaches each attached folder as `folders` says**, and a folder
  with no entry is hidden. A folder attached inside another takes its own
  setting for its own subtree; the deepest attached folder holding a path
  decides it.
- **`folders` is kept while the mode is read_all or write_all**, so returning to
  per_folder brings every choice back.
- **Detaching a folder drops it from every agent**, and a choice naming a folder
  that is not attached is ignored wherever it is read.

A configuration written before this shape carried `read`, `write_zones` and
`archive_moves`; `migrate` turns it into this one and is safe to run again.

CLI
---
    python3 notebook.py show [--json]
    python3 notebook.py access <agent> [--json]
    python3 notebook.py attach <folder>        # a folder inside the notebook
    python3 notebook.py detach <folder>
    python3 notebook.py repoint <path>         # a different notebook folder
    python3 notebook.py set-access <agent> --mode per_folder \\
        [--folder 00_inbox=write --folder 20_journal=read ...]
    python3 notebook.py migrate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_paths  # noqa: E402
import read_config  # noqa: E402

MODES = ("per_folder", "read_all", "write_all")
ACCESS = ("read", "write", "hide")
DEFAULT_MODE = "per_folder"
# A fresh installation's notebook: inside Bristol's own data, with these three.
DEFAULT_FOLDERS = ["inbox", "ai_workspace", "archive"]


# ── reading ──────────────────────────────────────────────────────────────────

def _load() -> dict:
    return read_config.load()


def _save(data: dict) -> None:
    path = read_config.config_path()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _clean(folder: str) -> str:
    return "/".join(p for p in str(folder).replace("\\", "/").split("/")
                    if p and p != ".")


def attached(data: dict | None = None) -> list[str]:
    """The attached folders, as written, in the order they were attached."""
    data = _load() if data is None else data
    folders = (data.get("markdown_notebook") or {}).get("folders") or []
    return [_clean(f) for f in folders if isinstance(f, str) and _clean(f)]


def root() -> Path | None:
    return data_paths.notebook_root()


def normalised(entry, folders: list[str]) -> dict:
    """An agent's access in the current shape, ignoring choices for folders
    that are not attached. A legacy entry reads as per_folder with nothing
    chosen; `migrate` is what carries its zones across."""
    entry = entry if isinstance(entry, dict) else {}
    mode = entry.get("mode") if entry.get("mode") in MODES else DEFAULT_MODE
    chosen = entry.get("folders") if isinstance(entry.get("folders"), dict) else {}
    kept = {f: chosen[f] for f in folders if chosen.get(f) in ACCESS}
    return {"mode": mode, "folders": kept}


def effective(entry, folders: list[str]) -> dict[str, str]:
    """What the agent may do in each attached folder."""
    access = normalised(entry, folders)
    if access["mode"] == "read_all":
        return {f: "read" for f in folders}
    if access["mode"] == "write_all":
        return {f: "write" for f in folders}
    return {f: access["folders"].get(f, "hide") for f in folders}


def may(entry, folders: list[str], relative: str) -> str:
    """read, write or hide for one path inside the notebook, written from the
    notebook down: the deepest attached folder holding it decides."""
    access = normalised(entry, folders)
    if access["mode"] == "read_all":
        return "read"
    if access["mode"] == "write_all":
        return "write"
    rel = _clean(relative)
    holders = [f for f in folders if rel == f or rel.startswith(f + "/")]
    if not holders:
        return "hide"
    return access["folders"].get(max(holders, key=len), "hide")


# ── writing ──────────────────────────────────────────────────────────────────

def _inside(path: Path, base: Path) -> str | None:
    """`path` written from `base` down, or None where it is not inside it."""
    try:
        rel = path.resolve().relative_to(base.resolve())
    except ValueError:
        return None
    return _clean(rel.as_posix())


def attach(folder: str, data: dict | None = None) -> str:
    """Attach a folder inside the notebook. Takes it written from the notebook
    down or as an absolute path; refuses one outside the notebook."""
    data = _load() if data is None else data
    base = root()
    if base is None:
        raise SystemExit("notebook: no notebook folder is set")
    given = Path(os.path.expanduser(folder))
    rel = _inside(given, base) if given.is_absolute() else _clean(folder)
    if not rel:
        raise SystemExit(f"notebook: {folder} is not a folder inside the notebook")
    nb = data.setdefault("markdown_notebook", {})
    folders = attached(data)
    if rel not in folders:
        folders.append(rel)
    nb["folders"] = folders
    return rel


def detach(folder: str, data: dict | None = None) -> bool:
    """Detach a folder, and drop it from every agent's choices."""
    data = _load() if data is None else data
    rel = _clean(folder)
    folders = attached(data)
    if rel not in folders:
        return False
    folders.remove(rel)
    data.setdefault("markdown_notebook", {})["folders"] = folders
    for slug, agent in (data.get("agents") or {}).items():
        if isinstance(agent, dict) and isinstance(agent.get("notebook_access"), dict):
            chosen = agent["notebook_access"].get("folders")
            if isinstance(chosen, dict):
                chosen.pop(rel, None)
    return True


def repoint(path: str, data: dict | None = None) -> None:
    """Point Bristol at another notebook. The attached list and every agent's
    per-folder choices are cleared; each agent keeps its mode."""
    data = _load() if data is None else data
    nb = data.setdefault("markdown_notebook", {})
    nb["notes_dir"] = path
    nb["folders"] = []
    for agent in (data.get("agents") or {}).values():
        if isinstance(agent, dict) and isinstance(agent.get("notebook_access"), dict):
            agent["notebook_access"]["folders"] = {}


def set_access(slug: str, mode: str, folders: dict[str, str] | None,
               data: dict | None = None) -> dict:
    """Set an agent's mode, and its per-folder choices where given. Choices not
    given are kept, so switching mode never loses them."""
    data = _load() if data is None else data
    agent = (data.get("agents") or {}).get(slug)
    if not isinstance(agent, dict):
        raise SystemExit(f"notebook: no agent {slug}")
    if mode not in MODES:
        raise SystemExit(f"notebook: mode is one of {', '.join(MODES)}")
    current = agent.get("notebook_access")
    kept = dict(current.get("folders") or {}) if isinstance(current, dict) \
        and "mode" in current else {}
    for folder, access in (folders or {}).items():
        if access not in ACCESS:
            raise SystemExit(f"notebook: access is one of {', '.join(ACCESS)}")
        kept[_clean(folder)] = access
    agent["notebook_access"] = {"mode": mode, "folders": kept}
    return agent["notebook_access"]


def migrate(data: dict | None = None) -> list[str]:
    """Carry a configuration from zones to folders. Returns what it changed.

    Attaches every top-level folder the notebook holds where none is attached
    yet, so agents keep what they reached. Each agent's zones become per-folder
    choices: a writable zone or the archive it may move into is write, any other
    folder is read where it read the notebook and hidden where it did not. A
    folder grant in key_data_paths naming an attached folder, or the notebook
    itself, becomes that folder's choice (or the mode) and leaves
    key_data_paths, so one fact has one home.
    """
    data = _load() if data is None else data
    said: list[str] = []
    nb = data.get("markdown_notebook")
    base = root()
    if not isinstance(nb, dict) or base is None:
        return said
    if "folders" not in nb:
        nb["folders"] = sorted(p.name for p in base.iterdir()
                               if p.is_dir() and not p.name.startswith(".")) \
            if base.is_dir() else []
        said.append(f"attached {len(nb['folders'])} folders")
    folders = attached(data)

    def rel_of(key: str) -> str | None:
        declared = nb.get(key)
        if not isinstance(declared, str) or not declared.strip():
            return None
        return _inside(data_paths.resolve(declared), base)

    zones = {"workspace": rel_of("workspace_dir"), "inbox": rel_of("inbox_dir")}
    archive = rel_of("archive_dir")
    for slug, agent in (data.get("agents") or {}).items():
        if not isinstance(agent, dict):
            continue
        old = agent.get("notebook_access")
        if isinstance(old, dict) and "mode" in old:
            continue
        old = old if isinstance(old, dict) else {}
        reads = bool(old.get("read"))
        writes = {zones[z] for z in old.get("write_zones") or [] if zones.get(z)}
        if old.get("archive_moves") and archive:
            writes.add(archive)
        mode, chosen = "per_folder", {}
        for f in folders:
            top = f.split("/")[0]
            if f in writes or top in writes:
                chosen[f] = "write"
            else:
                chosen[f] = "read" if reads else "hide"
        kept_grants = []
        for grant in agent.get("key_data_paths") or []:
            declared = grant.get("path") if isinstance(grant, dict) else grant
            access = grant.get("access", "write") if isinstance(grant, dict) else "write"
            rel = _inside(data_paths.resolve(declared), base) \
                if isinstance(declared, str) else None
            if rel == "":
                mode = "write_all" if access == "write" else "read_all"
            elif rel in folders:
                chosen[rel] = "write" if access == "write" else "read"
            else:
                kept_grants.append(grant)
        if "key_data_paths" in agent:
            agent["key_data_paths"] = kept_grants
        agent["notebook_access"] = {"mode": mode, "folders": chosen}
        said.append(f"{slug}: {mode}")
    return said


# ── CLI ──────────────────────────────────────────────────────────────────────

def _show(data: dict) -> dict:
    base = root()
    return {
        "root": (data.get("markdown_notebook") or {}).get("notes_dir", ""),
        "root_path": str(base) if base else "",
        "root_exists": bool(base and base.is_dir()),
        "folders": [{"folder": f,
                     "exists": bool(base and (base / f).is_dir())}
                    for f in attached(data)],
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("--json", action="store_true")
    a = sub.add_parser("access"); a.add_argument("agent")
    a.add_argument("--json", action="store_true")
    sub.add_parser("attach").add_argument("folder")
    sub.add_parser("detach").add_argument("folder")
    sub.add_parser("repoint").add_argument("path")
    sa = sub.add_parser("set-access"); sa.add_argument("agent")
    sa.add_argument("--mode", required=True, choices=MODES)
    sa.add_argument("--folder", action="append", default=[],
                    help="FOLDER=read|write|hide; repeatable")
    sub.add_parser("migrate")
    args = p.parse_args(argv)

    data = _load()
    if args.cmd == "show":
        shown = _show(data)
        if args.json:
            print(json.dumps(shown))
        else:
            print(f"notebook  {shown['root'] or '(none)'}"
                  + ("" if shown["root_exists"] else "  (missing)"))
            for f in shown["folders"]:
                print(f"  {f['folder']}" + ("" if f["exists"] else "  (missing)"))
        return 0
    if args.cmd == "access":
        agent = (data.get("agents") or {}).get(args.agent)
        if not isinstance(agent, dict):
            print(f"no agent {args.agent}", file=sys.stderr)
            return 1
        folders = attached(data)
        entry = agent.get("notebook_access")
        out = {**normalised(entry, folders), "effective": effective(entry, folders)}
        if args.json:
            print(json.dumps(out))
        else:
            base = root()
            print(f"{args.agent}  mode={out['mode']}  notebook={base}")
            for f, access in out["effective"].items():
                print(f"  {access:<6} {f}")
            rest = {"read_all": "read", "write_all": "write"}.get(out["mode"], "hide")
            print(f"  {rest:<6} everything not listed")
        return 0
    if args.cmd == "attach":
        print(f"attached {attach(args.folder, data)}")
    elif args.cmd == "detach":
        print(f"detached {args.folder}" if detach(args.folder, data)
              else f"{args.folder} was not attached")
    elif args.cmd == "repoint":
        repoint(args.path, data)
        print(f"notebook is {args.path}; no folder attached")
    elif args.cmd == "set-access":
        chosen = {}
        for item in args.folder:
            folder, _, access = item.rpartition("=")
            chosen[folder] = access
        print(json.dumps(set_access(args.agent, args.mode, chosen, data)))
    elif args.cmd == "migrate":
        said = migrate(data)
        print("\n".join(said) if said else "nothing to migrate")
    _save(data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
