#!/usr/bin/env python3
"""skills.py — install, list and load Agent Skills.

A skill is a directory holding a SKILL.md whose YAML frontmatter carries `name`
and `description`, per the Agent Skills specification
(github.com/agentskills/agentskills). Two roots hold them:

    native      src/skills/ in this repository — Bristol's own converted
                playbooks and protocols, published with the code.
    installed   the path declared at `skills.install_dir` in config, resolved
                through config_tools/data_paths.py. Git-ignored; third-party.

Progressive disclosure is the contract, not a suggestion. `list` reads each
SKILL.md only as far as the frontmatter terminator and never touches the body;
`view` is the only command that loads a body.

A third-party skill lands in `<install_dir>/.quarantine/<name>/` and is invisible
to `list` and `view` until `trust` promotes it. `audit` prints every script it
carries. Nothing here executes a skill's code.

CLI
---
    python3 skills.py list
    python3 skills.py view <name>
    python3 skills.py install <repo-url> <path-in-repo> [--name NAME]
    python3 skills.py convert <file.md> [--name NAME] [--description TEXT]
    python3 skills.py audit <name>
    python3 skills.py trust <name>
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402

QUARANTINE = ".quarantine"
SCRIPT_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".ts", ".rb", ".pl", ".ps1"}

# The only top-level frontmatter keys a conversion carries across. The
# specification defines a small set (src/playbooks/skill_conversion.md
# §Frontmatter); a foreign definition's other keys — `tools`, `model`, `color`,
# `allowed-tools`, a client's own extensions — exist so a dispatcher can route a
# card to a configured worker, and a Bristol session's model and tool surface
# belong to the host it runs in. They have no reader here and are dropped rather
# than carried as decoration.
CONVERT_KEEPS = ("name", "description", "license")

# The specification's own naming rule for a skill, which is also its directory
# name: lowercase letters, digits and single interior hyphens, 1-64 characters.
NAME_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-")

# A consuming client's always-loaded index truncates a description past this,
# and what is lost is the routing signal rather than the detail.
DESCRIPTION_ROUTING_LIMIT = 60


# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------

def native_root() -> Path:
    return data_paths.project_root() / "src" / "skills"


def installed_root() -> Path | None:
    """The declared install directory, or None when config declares none."""
    declared = read_config.get("skills.install_dir", None)
    if not declared:
        return None
    return data_paths.resolve(declared)


def quarantine_root() -> Path | None:
    root = installed_root()
    return None if root is None else root / QUARANTINE


def _skill_dirs(root: Path | None) -> list[Path]:
    if root is None or not root.is_dir():
        return []
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and not d.name.startswith(".") and (d / "SKILL.md").is_file()
    )


def find_skill(name: str, *, include_quarantine: bool = False) -> tuple[Path, str] | None:
    """Return (directory, origin) for a skill by directory name."""
    roots = [(native_root(), "native"), (installed_root(), "installed")]
    if include_quarantine:
        roots.append((quarantine_root(), "quarantined"))
    for root, origin in roots:
        for d in _skill_dirs(root):
            if d.name == name:
                return d, origin
    return None


# ---------------------------------------------------------------------------
# Frontmatter — read without loading the body
# ---------------------------------------------------------------------------

def read_frontmatter(skill_md: Path) -> dict[str, str]:
    """Parse the top-level scalar fields of a SKILL.md, reading no further than
    the frontmatter's closing delimiter. Nested blocks are skipped rather than
    parsed: `list` needs `name` and `description` and nothing else.
    """
    fields: dict[str, str] = {}
    with skill_md.open(encoding="utf-8") as fh:
        first = fh.readline()
        if first.lstrip("﻿").rstrip() != "---":
            return fields
        for line in fh:
            if line.rstrip() == "---":
                break
            if line[:1] in {" ", "\t", "#", "\n"} or ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _inventory(skill_dir: Path) -> list[tuple[Path, int, str]]:
    rows = []
    for p in sorted(skill_dir.rglob("*")):
        if p.is_file():
            rows.append((p.relative_to(skill_dir), p.stat().st_size, _sha256(p)))
    return rows


def _is_script(rel: Path) -> bool:
    return rel.suffix.lower() in SCRIPT_SUFFIXES


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(_args) -> int:
    rows = []
    for root, origin in ((native_root(), "native"), (installed_root(), "installed")):
        for d in _skill_dirs(root):
            fm = read_frontmatter(d / "SKILL.md")
            rows.append((fm.get("name", d.name), origin, fm.get("description", "")))
    if not rows:
        print("No skills. Native root: src/skills/. Installed root: skills.install_dir in config.")
        return 0
    width = max(len(r[0]) for r in rows)
    for name, origin, desc in rows:
        print(f"{name:<{width}}  {origin:<9}  {desc}")
    pending = _skill_dirs(quarantine_root())
    if pending:
        names = ", ".join(d.name for d in pending)
        print(f"\nQuarantined, not loadable until trusted: {names}")
    return 0


def cmd_view(args) -> int:
    found = find_skill(args.name)
    if found is None:
        print(f"No skill named '{args.name}'. A quarantined skill must be trusted first.",
              file=sys.stderr)
        return 1
    skill_dir, _ = found
    print((skill_dir / "SKILL.md").read_text(encoding="utf-8"), end="")
    return 0


def cmd_install(args) -> int:
    root = quarantine_root()
    if root is None:
        print("config declares no skills.install_dir; nowhere to install to.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "repo"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", args.repo, str(clone)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(result.stderr.strip() or "clone failed", file=sys.stderr)
            return 1
        source = clone / args.path
        if not (source / "SKILL.md").is_file():
            print(f"{args.path} holds no SKILL.md in {args.repo}.", file=sys.stderr)
            return 1
        name = args.name or read_frontmatter(source / "SKILL.md").get("name") or source.name
        if find_skill(name, include_quarantine=True) is not None:
            print(f"A skill named '{name}' is already present.", file=sys.stderr)
            return 1
        target = data_paths.ensure_dir(root) / name
        shutil.copytree(source, target)

    rows = _inventory(target)
    total = sum(r[1] for r in rows)
    print(f"Quarantined at {target}")
    print(f"{len(rows)} files, {total} bytes. Not listed and not loadable until trusted.\n")
    width = max(len(str(r[0])) for r in rows)
    for rel, size, digest in rows:
        mark = "*" if _is_script(rel) else " "
        print(f"{mark} {str(rel):<{width}}  {size:>9}  {digest[:16]}")
    print("\n* is executable code. Read it before trusting the skill:")
    print(f"    python3 skills.py audit {name}")
    return 0


def split_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """(top-level scalar fields, body) for a markdown file with YAML frontmatter.

    A file with no frontmatter yields an empty mapping and its whole text as the
    body. Nested blocks are not parsed — their key is reported as present so a
    conversion can say it dropped them, and their content is not carried.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].lstrip("\ufeff").rstrip() != "---":
        return {}, text
    fields: dict[str, str] = {}
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            return fields, "".join(lines[index + 1:])
        line = lines[index]
        if line[:1] in {" ", "\t", "#", "\n"} or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, ""


def normalise_name(raw: str) -> str:
    """A skill name from arbitrary text: lowercased, non-name characters folded
    to hyphens, runs collapsed, ends trimmed. Returns '' when nothing survives."""
    lowered = "".join(c if c in NAME_CHARS else "-" for c in raw.strip().lower())
    while "--" in lowered:
        lowered = lowered.replace("--", "-")
    return lowered.strip("-")[:64]


def cmd_convert(args) -> int:
    """Write a foreign markdown definition into quarantine as a skill folder.

    A subagent definition, a slash command and a prompt-pack entry are one object
    — a markdown body under frontmatter — and the half of that frontmatter which
    routes work has no reader in Bristol. This keeps the body and the two fields
    that make a skill loadable, and says what it dropped.
    """
    source = Path(args.source).expanduser()
    if not source.is_file():
        print(f"{source} is not a file.", file=sys.stderr)
        return 1
    root = quarantine_root()
    if root is None:
        print("config declares no skills.install_dir; nowhere to convert into.",
              file=sys.stderr)
        return 1

    fields, body = split_frontmatter(source)
    description = args.description or fields.get("description", "")
    if not description:
        print(f"{source} carries no description, and a skill without one states "
              f"no trigger and never routes.\n"
              f"Supply it: python3 skills.py convert {source} --description \"...\"",
              file=sys.stderr)
        return 1

    name = normalise_name(args.name or fields.get("name", "") or source.stem)
    if not name:
        print("No usable skill name; pass --name.", file=sys.stderr)
        return 1
    if find_skill(name, include_quarantine=True) is not None:
        print(f"A skill named '{name}' is already present.", file=sys.stderr)
        return 1

    target = data_paths.ensure_dir(root) / name
    target.mkdir()
    kept = {"name": name, "description": description}
    if fields.get("license"):
        kept["license"] = fields["license"]
    header = "".join(f"{k}: {v}\n" for k, v in kept.items())
    (target / "SKILL.md").write_text(
        f"---\n{header}---\n{body.lstrip(chr(10))}", encoding="utf-8")

    dropped = [k for k in fields if k not in CONVERT_KEEPS]
    print(f"Quarantined at {target}")
    if dropped:
        print(f"Dropped, no reader in Bristol: {', '.join(sorted(dropped))}")
    if len(description) > DESCRIPTION_ROUTING_LIMIT:
        print(f"description is {len(description)} characters; past "
              f"{DESCRIPTION_ROUTING_LIMIT} a client's index truncates it and the "
              f"routing signal is what is lost. Rewrite it before trusting.")
    print(f"Not listed and not loadable until trusted:\n"
          f"    python3 skills.py audit {name}\n"
          f"    python3 skills.py trust {name}")
    return 0


def cmd_audit(args) -> int:
    root = quarantine_root()
    candidates = [d for d in _skill_dirs(root) if d.name == args.name]
    if not candidates:
        found = find_skill(args.name)
        if found is None:
            print(f"No skill named '{args.name}'.", file=sys.stderr)
            return 1
        candidates = [found[0]]
    skill_dir = candidates[0]

    print(f"=== {skill_dir}/SKILL.md ===")
    print((skill_dir / "SKILL.md").read_text(encoding="utf-8"), end="")
    scripts = [rel for rel, _, _ in _inventory(skill_dir) if _is_script(rel)]
    if not scripts:
        print("\n=== no executable code in this skill ===")
        return 0
    for rel in scripts:
        print(f"\n=== {rel} ===")
        print((skill_dir / rel).read_text(encoding="utf-8", errors="replace"), end="")
    return 0


def cmd_trust(args) -> int:
    root = quarantine_root()
    staged = [d for d in _skill_dirs(root) if d.name == args.name]
    if not staged:
        print(f"'{args.name}' is not quarantined.", file=sys.stderr)
        return 1
    destination = data_paths.ensure_dir(installed_root()) / args.name
    if destination.exists():
        print(f"{destination} already exists.", file=sys.stderr)
        return 1
    shutil.move(str(staged[0]), str(destination))
    print(f"Trusted. {args.name} is now listed and loadable at {destination}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="every loadable skill: name and description only")

    p_view = sub.add_parser("view", help="load one skill's body")
    p_view.add_argument("name")

    p_install = sub.add_parser("install", help="fetch a skill into quarantine")
    p_install.add_argument("repo", help="git URL of the hub repository")
    p_install.add_argument("path", help="the skill's directory inside that repository")
    p_install.add_argument("--name", help="override the installed directory name")

    p_convert = sub.add_parser(
        "convert", help="write a foreign markdown definition into quarantine as a skill")
    p_convert.add_argument("source", help="the markdown file to convert")
    p_convert.add_argument("--name", help="override the skill and directory name")
    p_convert.add_argument("--description",
                           help="the trigger, where the source states none")

    p_audit = sub.add_parser("audit", help="print a skill's SKILL.md and every script it carries")
    p_audit.add_argument("name")

    p_trust = sub.add_parser("trust", help="promote a quarantined skill to loadable")
    p_trust.add_argument("name")

    args = parser.parse_args(argv)
    return {
        "list": cmd_list, "view": cmd_view, "install": cmd_install,
        "convert": cmd_convert, "audit": cmd_audit, "trust": cmd_trust,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
