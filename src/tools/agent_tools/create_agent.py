#!/usr/bin/env python3
"""create_agent.py — write a new agent's charter, config entry and board epic.

Everything a new agent is made of that can be derived is derived. What cannot
be — the mandate and the guardrails that halt it — is what the caller supplies,
because a file that could grant itself authority is the one thing this system
refuses (`src/templates/identity_template.md` §What of an agent can be
imported).

GitHub-safe: contains no personal data or absolute user paths. Every location
resolves through `/config`.

CLI
---
    python3 create_agent.py <slug> \\
        --description "the one line a picker shows" \\
        --role "what this agent is for, written for a stranger" \\
        --guardrail "Never ..." [--guardrail ...] \\
        [--charter-file <path>] [--env NAME=VALUE]... \\
        [--data-path data/<instance>/<domain>]... \\
        [--context-file <path>]... \\
        [--skill <name>]... \\
        [--notebook read|write|none] \\
        [--owns tools/<slug>/]...
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "config_tools"))
sys.path.insert(0, str(HERE.parents[0] / "skill_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402
import write_config  # noqa: E402
import skills  # noqa: E402

SLUG = re.compile(r"^[a-z][a-z0-9_]*$")
WIDTH = 79

CHARTER = """# {slug}.md — Agent Charter

**Single source of truth for identity and operating mandate.**
**Loaded at every session start via `src/app.md`.**

---

## 1. Identity & System Role

{role}

---

## 2. Operating Mandate & Execution

### 2.1 Session Start
`src/templates/identity_template.md` §Session start.

### 2.2 Bright-Line Guardrails Only
{guardrails}

---

## 3. Boundaries & Coordination

`src/templates/identity_template.md` §Boundaries and coordination, and §Data
locations.
{owns}"""


def wrap(text: str, indent: str = "") -> str:
    """One paragraph per blank line, wrapped to the governing-doc width."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "\n\n".join(
        textwrap.fill(p, width=WIDTH, initial_indent=indent,
                      subsequent_indent=indent, break_on_hyphens=False,
                      break_long_words=False)
        for p in paragraphs
    )


def charter_text(slug: str, role: str, guardrails: list[str],
                 owns: list[str]) -> str:
    bullets = "\n".join(
        textwrap.fill(f"- **{g.strip().rstrip('.')}.**", width=WIDTH,
                      subsequent_indent="  ", break_on_hyphens=False,
                      break_long_words=False)
        for g in guardrails
    )
    owned = ""
    if owns:
        named = ", ".join(f"`{o}`" for o in owns)
        owned = "\n" + textwrap.fill(f"Owns {named}.", width=WIDTH) + "\n"
    return CHARTER.format(slug=slug, role=wrap(role), guardrails=bullets,
                          owns=owned)


def notebook_access(choice: str) -> dict:
    """The zones a new agent reaches — config's markdown_notebook §ZONES.

    `write` grants both writable zones and the move into the archive, which is
    the whole of what an agent may write; `read` grants the notebook without
    them; `none` grants nothing.
    """
    writes = choice == "write"
    return {
        "read": choice in {"read", "write"},
        "write_zones": ["workspace", "inbox"] if writes else [],
        "archive_moves": writes,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slug", help="the agent's name, in snake_case")
    parser.add_argument("--description", required=True,
                        help="the one line the agent picker and docs show")
    parser.add_argument("--role",
                        help="what this agent is for, written for a stranger")
    parser.add_argument("--guardrail", action="append", default=[],
                        help="one rule that halts execution; repeatable")
    parser.add_argument("--charter-file",
                        help="a file holding the whole charter document, "
                             "instead of --role and --guardrail")
    parser.add_argument("--env", action="append", default=[],
                        metavar="NAME=VALUE",
                        help="an environment variable this agent runs with; "
                             "repeatable")
    parser.add_argument("--data-path", action="append", default=[],
                        help="a data folder this agent owns; repeatable")
    parser.add_argument("--context-file", action="append", default=[],
                        help="a file this agent reads on sight; repeatable")
    parser.add_argument("--skill", action="append", default=[],
                        help="a skill to attach; repeatable")
    parser.add_argument("--owns", action="append", default=[],
                        help="a folder this agent maintains; repeatable")
    parser.add_argument("--notebook", choices=("read", "write", "none"),
                        default="none",
                        help="notebook access as a whole; default none")
    parser.add_argument("--notebook-read", choices=("yes", "no"),
                        help="read the notebook; overrides --notebook")
    parser.add_argument("--write-zone", action="append", default=[],
                        help="a notebook zone this agent writes; repeatable")
    parser.add_argument("--archive-moves", choices=("yes", "no"),
                        help="may move a file into the notebook archive")
    parser.add_argument("--no-epic", action="store_true",
                        help="skip the board epic, where one already exists")
    args = parser.parse_args(argv)

    slug = args.slug
    if not args.charter_file and not (args.role and args.guardrail):
        print("supply the charter: --charter-file, or --role with at least one "
              "--guardrail.", file=sys.stderr)
        return 1
    if not SLUG.match(slug):
        print(f"'{slug}' is not a slug: lower case, digits and underscores, "
              f"starting with a letter.", file=sys.stderr)
        return 1

    configured = read_config.get("agents", {})
    if slug in configured:
        print(f"'{slug}' is already an agent. Extend its charter and config "
              f"entry rather than creating a second one.", file=sys.stderr)
        return 1

    root = data_paths.project_root()
    charter = root / "src" / "agent_identities" / f"{slug}.md"
    if charter.exists():
        print(f"{charter.relative_to(root)} already exists.", file=sys.stderr)
        return 1

    # Every named skill is checked before anything is written, so a typo does
    # not leave an agent half-created.
    unknown = [s for s in args.skill if not skills._known_skill(s)]
    if unknown:
        print(f"not loadable: {', '.join(unknown)}. `skills.py list` names what "
              f"is, and a quarantined skill has to be trusted first.",
              file=sys.stderr)
        return 1

    if args.charter_file:
        # A charter supplied whole is written verbatim: it is a document
        # somebody wrote, and this tool has no business reformatting it.
        try:
            body = Path(args.charter_file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"could not read the charter: {exc}", file=sys.stderr)
            return 1
        if not body.strip():
            print("an agent with no charter is not an agent.", file=sys.stderr)
            return 1
    else:
        body = charter_text(slug, args.role, args.guardrail, args.owns)

    env = {}
    for item in args.env:
        name, sep, value = item.partition("=")
        if not sep or not name.strip():
            print(f"an environment entry is NAME=value: '{item}' is not.",
                  file=sys.stderr)
            return 1
        env[name.strip()] = value

    charter.parent.mkdir(parents=True, exist_ok=True)
    charter.write_text(body, encoding="utf-8")

    entry = {
        "identity": f"src/agent_identities/{slug}.md",
        "description": args.description.strip(),
        "key_context_files": args.context_file,
        "key_data_paths": args.data_path,
        "notebook_access": notebook_access(args.notebook),
    }
    # The three parts stated one at a time win over the shorthand, so the form
    # and the command line express the same access.
    if args.notebook_read is not None:
        entry["notebook_access"]["read"] = args.notebook_read == "yes"
    if args.write_zone:
        entry["notebook_access"]["write_zones"] = args.write_zone
    elif args.notebook_read is not None or args.archive_moves is not None:
        entry["notebook_access"].setdefault("write_zones", [])
        if not args.write_zone and args.notebook == "none":
            entry["notebook_access"]["write_zones"] = []
    if args.archive_moves is not None:
        entry["notebook_access"]["archive_moves"] = args.archive_moves == "yes"
    if env:
        entry["env"] = env
    write_config.set_key(f"agents.{slug}", entry)

    # Attached through skill_tools' own command rather than by writing the key
    # here, so a skill attached at creation and one attached a year later go the
    # same way and stay the same shape.
    for name in args.skill:
        skills.cmd_attach(argparse.Namespace(name=name, agent=slug))

    print(f"Charter   src/agent_identities/{slug}.md")
    print(f"Config    agents.{slug}")
    for declared in args.data_path:
        where = data_paths.resolve(declared)
        state = "exists" if Path(where).is_dir() else "not there yet, which is normal"
        print(f"Data      {declared} — {state}")

    if not args.no_epic:
        # Through the board's own CLI rather than a second insert, so an agent
        # created here and an agent created by hand reach the board identically.
        writer = HERE.parents[0] / "ticket_tools" / "ticket_write.py"
        made = subprocess.run(
            [sys.executable, str(writer), "add-epic",
             "--name", f"{slug} — initial setup", "--owner", slug],
            capture_output=True, text=True,
        )
        line = (made.stdout or made.stderr).strip().splitlines()
        print(f"Epic      {line[-1] if line else 'add-epic produced no output'}")

    print(f"\n{slug} is selectable as the active agent. Nothing else needs "
          f"editing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
