#!/usr/bin/env python3
"""
import_agent.py — read an agent file, then adopt the agent it describes.

    python3 import_agent.py <file.agent.json>            # read it, fetch its skills
    python3 import_agent.py <file.agent.json> --accept   # write the agent

Two runs, because a file that arrives carrying a mandate is a stranger's
statement of what an agent may do. The first run fetches every skill the file
names into the skill quarantine, where nothing loads until it is trusted, and
prints the agent's mandate and its guardrails for a person to read. The second
writes the charter and the config entry, and the agent is then an agent like any
other — `src/templates/identity_template.md` §What of an agent can be imported.

The file itself is the only place a pending agent lives: nothing of it is
written anywhere until `--accept`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "config_tools"))
sys.path.insert(0, str(HERE.parents[0] / "skill_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402
import write_config  # noqa: E402
import skills  # noqa: E402

FORMAT = 1
SUPPLY = "<supply>"
INSTANCE = "<instance>"
NOTEBOOK = "<notebook>"
GUARDRAIL_WORDS = ("guardrail", "bright-line", "bright line")


# ── Reading the file ──────────────────────────────────────────────────────────

def load(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as failure:
        raise SystemExit(f"import_agent: {path} could not be read ({failure}).")
    if not isinstance(document, dict) or "bristol_agent" not in document:
        raise SystemExit(f"import_agent: {path} is not an agent file — it "
                         f"declares no bristol_agent format.")
    if document["bristol_agent"] != FORMAT:
        raise SystemExit(f"import_agent: {path} is format "
                         f"{document['bristol_agent']}; this build reads "
                         f"format {FORMAT}.")
    for key in ("slug", "charter", "entry"):
        if not document.get(key):
            raise SystemExit(f"import_agent: {path} carries no {key}.")
    return document


def sections(charter: str) -> list[tuple[str, str]]:
    """(heading, body) for every ## or ### section of a charter."""
    out: list[tuple[str, str]] = []
    heading, body = "", []
    for line in charter.splitlines():
        if line.startswith("## "):
            if heading:
                out.append((heading, "\n".join(body).strip()))
            heading, body = line.lstrip("# ").strip(), []
        elif heading:
            body.append(line)
    if heading:
        out.append((heading, "\n".join(body).strip()))
    return out


def mandate_and_guardrails(charter: str) -> str:
    """What a person has to read before granting an agent authority: what it is
    for, and what stops it. A charter shaped differently is shown whole rather
    than filtered down to nothing."""
    found = [(h, b) for h, b in sections(charter)
             if "identity" in h.lower() or "mandate" in h.lower()
             or any(word in h.lower() for word in GUARDRAIL_WORDS)]
    if not found:
        return charter.strip()
    return "\n\n".join(f"## {h}\n\n{b}" for h, b in found if b)


# ── Skills ────────────────────────────────────────────────────────────────────

def fetch_skills(named: list[dict]) -> list[str]:
    """Install every addressed skill through skill_tools' own command, so an
    imported skill and a hand-installed one arrive the same way and land in the
    same quarantine. Returns one report line per skill."""
    installer = HERE.parents[0] / "skill_tools" / "skills.py"
    lines = []
    for record in named:
        name = record.get("name", "?")
        source = record.get("source")
        if source == "native":
            state = "here" if skills._known_skill(name) else "MISSING — this build ships no such skill"
            lines.append(f"  {name}: ships with Bristol, {state}")
            continue
        if source != "address" or not record.get("address"):
            lines.append(f"  {name}: MISSING — the file records no address, so "
                         f"it cannot be fetched")
            continue
        if skills.find_skill(name, include_quarantine=True):
            lines.append(f"  {name}: already here, left as it is")
            continue
        done = subprocess.run(
            [sys.executable, str(installer), "install", record["address"]],
            capture_output=True, text=True)
        if done.returncode == 0:
            lines.append(f"  {name}: fetched into quarantine from "
                         f"{record['address']}")
        else:
            why = (done.stderr or done.stdout).strip().splitlines()
            lines.append(f"  {name}: MISSING — {why[-1] if why else 'install failed'}")
    return lines


# ── Writing the agent ─────────────────────────────────────────────────────────

def localise(value, instance: str, notebook: str | None):
    """The exporter's tokens resolved to this installation's own names."""
    if isinstance(value, dict):
        return {k: localise(v, instance, notebook) for k, v in value.items()}
    if isinstance(value, list):
        return [localise(v, instance, notebook) for v in value]
    if not isinstance(value, str):
        return value
    text = value.replace(INSTANCE, instance)
    if notebook:
        text = text.replace(NOTEBOOK, notebook)
    return text


def placeholders(entry: dict, prefix: str = "") -> list[str]:
    """Every dotted key still holding a value the importer has to supply."""
    out: list[str] = []
    if isinstance(entry, dict):
        for key, value in entry.items():
            out += placeholders(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(entry, list):
        for i, value in enumerate(entry):
            out += placeholders(value, f"{prefix}.{i}")
    elif entry == SUPPLY:
        out.append(prefix)
    return out


def accept(document: dict) -> int:
    slug = document["slug"]
    root = data_paths.project_root()
    charter_path = root / "src" / "agent_identities" / f"{slug}.md"

    if slug in read_config.get("agents", {}):
        print(f"'{slug}' is already an agent here. Rename the one in the file, "
              f"or extend the one you have.", file=sys.stderr)
        return 1
    if charter_path.exists():
        print(f"{charter_path.relative_to(root)} already exists.", file=sys.stderr)
        return 1

    notebook = data_paths.notebook_root()
    entry = localise(document["entry"], data_paths.instance_slug(),
                     notebook.name if notebook else None)
    entry = {"identity": f"src/agent_identities/{slug}.md", **entry}

    charter_path.parent.mkdir(parents=True, exist_ok=True)
    charter_path.write_text(document["charter"], encoding="utf-8")
    write_config.set_key(f"agents.{slug}", entry)

    # Through skill_tools' own command, which refuses a name that is not
    # loadable — so a quarantined skill stays unattached until it is trusted.
    attached, held = [], []
    for record in document.get("skills", []):
        name = record.get("name", "")
        if skills._known_skill(name):
            skills.cmd_attach(argparse.Namespace(name=name, agent=slug))
            attached.append(name)
        else:
            held.append(name)

    writer = HERE.parents[0] / "ticket_tools" / "ticket_write.py"
    made = subprocess.run(
        [sys.executable, str(writer), "add-epic",
         "--name", f"{slug} — initial setup", "--owner", slug],
        capture_output=True, text=True)
    epic = (made.stdout or made.stderr).strip().splitlines()

    print(f"Charter   src/agent_identities/{slug}.md")
    print(f"Config    agents.{slug}")
    print(f"Skills    attached: {', '.join(attached) or 'none'}")
    if held:
        print(f"          not attached, because they are not loadable yet: "
              f"{', '.join(held)}")
        print(f"          `skills.py trust <name>` after reading it, then "
              f"`skills.py attach <name> --agent {slug}`")
    print(f"Epic      {epic[-1] if epic else 'add-epic produced no output'}")

    outstanding = placeholders(entry)
    if outstanding:
        print("\nValues that are yours to supply — the exporter's never crossed:")
        for dotted in outstanding:
            print(f"  python3 src/tools/config_tools/write_config.py "
                  f"agents.{slug}.{dotted} '<your value>'")
    print(f"\n{slug} is selectable as the active agent.")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("file", type=Path, help="the .agent.json file")
    ap.add_argument("--accept", action="store_true",
                    help="write the charter and the config entry")
    args = ap.parse_args(argv)

    document = load(args.file)
    slug = document["slug"]
    entry = document["entry"]

    print(f"AGENT     {slug}")
    print(f"          {entry.get('description', '(no description)')}")
    print()
    print(mandate_and_guardrails(document["charter"]))
    print()

    if args.accept:
        return accept(document)

    print("SKILLS IT NAMES")
    for line in fetch_skills(document.get("skills", [])):
        print(line)
    print("\nNothing was trusted. A fetched skill is in quarantine until you "
          "have read it — src/skills/importing-a-skill/SKILL.md.")
    print(f"\nRead the mandate and the guardrails above. To adopt {slug}:")
    print(f"  python3 src/tools/agent_tools/import_agent.py {args.file} --accept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
