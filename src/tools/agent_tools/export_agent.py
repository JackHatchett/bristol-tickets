#!/usr/bin/env python3
"""
export_agent.py — write one agent to a single portable file.

    python3 export_agent.py <slug> [--out PATH]

The file carries the three parts of an agent that can travel: its charter, its
config entry, and the address of every skill it names. It carries no value that
belongs to the person exporting it — every absolute path and every environment
variable's value is replaced by a placeholder the importer fills, and the
instance slug and the notebook's folder name become tokens the importer resolves
to their own. What may cross and what may not is
`src/templates/identity_template.md` §What of an agent can be imported.

Import is `import_agent.py`; the file format is
`src/tools/agent_tools/README.md` §The agent file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "config_tools"))
sys.path.insert(0, str(HERE.parents[0] / "skill_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402
import skills  # noqa: E402

FORMAT = 1
SUPPLY = "<supply>"
INSTANCE = "<instance>"
NOTEBOOK = "<notebook>"
# Keys the importer regenerates rather than copies: a charter's path follows
# from the slug, and skills are named in their own section with addresses.
REGENERATED = {"identity", "skills"}


def notebook_name() -> str | None:
    root = data_paths.notebook_root()
    return root.name if root is not None else None


def generalise(value, instance: str, notebook: str | None):
    """A config value with everything local to this installation taken out."""
    if isinstance(value, dict):
        return {k: generalise(v, instance, notebook) for k, v in value.items()}
    if isinstance(value, list):
        return [generalise(v, instance, notebook) for v in value]
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.startswith("/") or text.startswith("~"):
        return SUPPLY
    if text.startswith(f"data/{instance}/") or text == f"data/{instance}":
        return text.replace(f"data/{instance}", f"data/{INSTANCE}", 1)
    if notebook and (text.startswith(f"{notebook}/") or text == notebook):
        return text.replace(notebook, NOTEBOOK, 1)
    return text


def skill_addresses(names: list[str]) -> list[dict]:
    """One record per attached skill: its name, and where it came from."""
    out = []
    for name in names:
        found = skills.find_skill(name, include_quarantine=True)
        if found is None:
            out.append({"name": name, "source": "unknown"})
            continue
        skill_dir, root_name = found
        if root_name == "native":
            out.append({"name": name, "source": "native"})
            continue
        origin = skills.read_origin(skill_dir)
        address = skills.source_url(origin)
        if not address:
            # Installed before the provenance record existed: the skill is here
            # and its address is not, so it cannot be fetched by name alone.
            out.append({"name": name, "source": "unrecorded"})
            continue
        record = {"name": name, "source": "address", "address": address}
        for key in ("repository", "path", "commit", "licence"):
            if origin.get(key):
                record[key] = origin[key]
        out.append(record)
    return out


def build(slug: str) -> dict:
    entry = read_config.get(f"agents.{slug}")
    instance = data_paths.instance_slug()
    notebook = notebook_name()

    charter_path = data_paths.project_root() / entry["identity"]
    if not charter_path.is_file():
        raise SystemExit(f"export_agent: {entry['identity']} is not on disk.")

    config_entry = {
        key: generalise(value, instance, notebook)
        for key, value in entry.items() if key not in REGENERATED
    }
    if isinstance(config_entry.get("env"), dict):
        config_entry["env"] = {k: SUPPLY for k in config_entry["env"]}

    return {
        "bristol_agent": FORMAT,
        "slug": slug,
        "charter": charter_path.read_text(encoding="utf-8"),
        "entry": config_entry,
        "skills": skill_addresses(entry.get("skills", []) or []),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("slug", help="the agent to export")
    ap.add_argument("--out", type=Path, help="where to write it "
                                             "(default: <slug>.agent.json here)")
    args = ap.parse_args(argv)

    if args.slug not in read_config.get("agents", {}):
        print(f"'{args.slug}' is not an agent. `read_config.py --keys agents` "
              f"names the ones that are.", file=sys.stderr)
        return 1

    document = build(args.slug)
    out = args.out or Path.cwd() / f"{args.slug}.agent.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")

    supplied = [k for k, v in document["entry"].items()
                if json.dumps(v).find(SUPPLY) != -1]
    print(f"Wrote {out}")
    print(f"  charter   {len(document['charter'].splitlines())} lines")
    print(f"  entry     {', '.join(document['entry']) or 'no keys'}")
    named = document["skills"]
    print(f"  skills    {len(named)} named"
          + (f" — {', '.join(s['name'] for s in named)}" if named else ""))
    unaddressed = [s["name"] for s in named
                   if s["source"] in {"unknown", "unrecorded"}]
    if unaddressed:
        print(f"            carries no address, so an importer cannot fetch it: "
              f"{', '.join(unaddressed)}")
    if supplied:
        print(f"  placeholders in {', '.join(supplied)} — the importer's values, "
              f"not yours")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
