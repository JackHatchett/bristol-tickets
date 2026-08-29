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

An installed skill carries a `.origin.json` beside its SKILL.md holding the
repository, the path inside it, the resolved commit and the licence found, so
`list` can name where a skill came from and `audit` can answer both questions
without a second lookup. A source stating no licence records that as absent.

`audit` opens with a scan of the skill's code by `bandit`, run as a module of
this interpreter and never installed from here. What it reads and what it does
not is README.md §The scanner. A report is evidence: `trust` consults no scanner
and stays a command a person runs.

CLI
---
    python3 skills.py list [--agent SLUG]
    python3 skills.py view <name>
    python3 skills.py install <address> [--name NAME]
    python3 skills.py install <repo-url> <path-in-repo> [--name NAME]
    python3 skills.py convert <file.md> [--name NAME] [--description TEXT]
    python3 skills.py audit <name>
    python3 skills.py trust <name>
    python3 skills.py attach <name> --agent SLUG
    python3 skills.py detach <name> --agent SLUG
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402
import write_config  # noqa: E402

QUARANTINE = ".quarantine"

# What an installed skill carries about where it came from, written beside its
# SKILL.md so the record moves with the directory through quarantine and trust
# and can never orphan. Dotted, so a client reading the skill by the
# specification never sees it.
ORIGIN_FILE = ".origin.json"

# Where a repository states its licence. Read in this order, and the first that
# exists is the one recorded.
LICENCE_FILENAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE",
                     "LICENCE.md", "LICENCE.txt", "COPYING", "COPYING.md")

# What a record says instead of leaving a licence field blank. A skill whose
# source states no licence has been read and found to state none, which is a
# different fact from one nobody looked for.
ABSENT = "absent"

SCRIPT_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".ts", ".rb", ".pl", ".ps1"}

# The scanner `audit` runs over a skill's code, invoked as a module so it is
# found wherever this interpreter's packages are rather than on PATH. Bristol
# never installs it: an absent scanner is a report that says so, not a failure.
# What it reads and what it does not is `src/tools/skill_tools/README.md`
# §The scanner.
SCANNER = "bandit"
SCANNER_READS = ".py"

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

# The frontmatter keys under which a foreign definition names the skills it
# needs. A definition that states a dependency only in its prose declares
# nothing, and convert says so rather than guessing at the body.
DEPENDENCY_KEYS = ("skills", "required_skills", "dependencies", "requires")

# Frontmatter keys that name something a Bristol session does not have. Each is
# valid in the format it comes from and inert here, which is exactly why it has
# to be said out loud: a reader that does not know a key ignores it, and the
# skill then installs cleanly and quietly does nothing. Two keys name the same
# fact, so they are grouped by consequence rather than by key.
FOREIGN_GATES = {
    "required_environment_variables": "credentials",
    "env_vars": "credentials",
    "requires_toolsets": "toolsets",
    "fallback_for_toolsets": "fallback",
}

GATE_CONSEQUENCE = {
    "credentials":
        "This skill expects credentials from a mechanism Bristol does not "
        "have, so whatever needs them will not run here",
    "toolsets":
        "This skill is gated on Hermes toolsets, which a Bristol session has "
        "none of, so the gate has no reader here",
    "fallback":
        "This skill offers itself as the fallback for Hermes toolsets, which "
        "a Bristol session has none of, so it is never chosen that way",
}


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


def read_origin(skill_dir: Path) -> dict:
    """The provenance record beside a skill's SKILL.md, or {} where there is
    none — a native skill has no repository, and a skill installed before the
    record existed carries no file."""
    path = skill_dir / ORIGIN_FILE
    if not path.is_file():
        return {}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return record if isinstance(record, dict) else {}


def find_licence(clone: Path, source: Path) -> tuple[str, str]:
    """(what the licence says, where it was read from) for a skill in a clone.

    Three places, most specific first: the skill's own frontmatter, a licence
    file beside the skill, and one at the repository root. A licence file is
    recorded by its own first line — the name it gives itself — rather than by
    a licence detected from its text, since a detection is a guess and this
    records what was found. Both values are ABSENT when a repository states no
    licence anywhere."""
    declared = read_frontmatter(source / "SKILL.md").get("license", "").strip()
    if declared:
        return declared, "SKILL.md"
    for directory in (source, clone):
        for filename in LICENCE_FILENAMES:
            candidate = directory / filename
            if not candidate.is_file():
                continue
            for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip():
                    rel = candidate.relative_to(clone)
                    return line.strip(), str(rel)
            return ABSENT, str(candidate.relative_to(clone))
    return ABSENT, ABSENT


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

def _origin_column(skill_dir: Path, root_name: str) -> str:
    """What a skill's origin reads as in a listing. A native skill has no
    repository and says so; an installed one names the repository and the commit
    it was taken at. A skill carrying no record falls back to its root, which is
    all that is known about it."""
    record = read_origin(skill_dir)
    repo = record.get("repo")
    if not repo:
        return root_name
    # Both spellings a git remote comes in — https://host/owner/repo and
    # git@host:owner/repo — reduce to the last two segments, which is the pair
    # that identifies the repository in either.
    parts = [x for x in re.split(r"[/:]", repo.rstrip("/").removesuffix(".git")) if x]
    where = "/".join(parts[-2:]) if len(parts) >= 2 else repo
    commit = record.get("commit", "")
    return f"{where}@{commit[:7]}" if commit and commit != ABSENT else where


ATTACHMENTS = "agents.{slug}.skills"


def attached_to(slug: str) -> list[str]:
    """The skill names attached to one agent, in configured order."""
    names = read_config.get(ATTACHMENTS.format(slug=slug), [])
    return [n for n in names if isinstance(n, str)] if isinstance(names, list) else []


def _agent_slugs() -> list[str]:
    agents = read_config.get("agents", {})
    return [s for s in agents if s != "_notes"] if isinstance(agents, dict) else []


def _require_agent(slug: str) -> None:
    known = _agent_slugs()
    if slug not in known:
        raise SystemExit(
            f"no agent '{slug}' in config. Configured: {', '.join(known) or 'none'}")


def _all_skills() -> list[tuple[str, str, str]]:
    """Every loadable skill as (name, origin, description), both roots."""
    rows = []
    for root, root_name in ((native_root(), "native"), (installed_root(), "installed")):
        for d in _skill_dirs(root):
            fm = read_frontmatter(d / "SKILL.md")
            rows.append((fm.get("name", d.name), _origin_column(d, root_name),
                         fm.get("description", "")))
    return rows


def cmd_list(args) -> int:
    rows = _all_skills()
    if not rows:
        print("No skills. Native root: src/skills/. Installed root: skills.install_dir in config.")
        return 0

    slug = getattr(args, "agent", None)
    attached: list[str] = []
    if slug:
        _require_agent(slug)
        attached = attached_to(slug)
        order = {name: i for i, name in enumerate(attached)}
        rows.sort(key=lambda r: order.get(r[0], len(order)))

    mark_width = len("yours") if attached else 0
    width = max(len(r[0]) for r in rows)
    origin_width = max(len(r[1]) for r in rows)
    for name, origin, desc in rows:
        prefix = f"{'yours' if name in attached else '':<{mark_width}}  " if attached else ""
        print(f"{prefix}{name:<{width}}  {origin:<{origin_width}}  {desc}")
    if slug:
        print(f"\nWhat is marked yours is attached to {slug} and matched first; "
              f"every other skill listed is reachable the same way.")

    pending = _skill_dirs(quarantine_root())
    if pending:
        names = ", ".join(d.name for d in pending)
        print(f"\nQuarantined, not loadable until trusted: {names}")
    return 0


def _known_skill(name: str) -> bool:
    return any(r[0] == name for r in _all_skills())


def cmd_attach(args) -> int:
    _require_agent(args.agent)
    if not _known_skill(args.name):
        raise SystemExit(
            f"no loadable skill '{args.name}'. `list` names what is loadable; a "
            f"quarantined skill has to be trusted first.")
    attached = attached_to(args.agent)
    if args.name in attached:
        print(f"{args.name} is already attached to {args.agent}")
        return 0
    write_config.set_key(ATTACHMENTS.format(slug=args.agent), attached + [args.name])
    print(f"{args.name} attached to {args.agent}")
    return 0


def cmd_detach(args) -> int:
    _require_agent(args.agent)
    attached = attached_to(args.agent)
    if args.name not in attached:
        print(f"{args.name} is not attached to {args.agent}")
        return 0
    write_config.set_key(ATTACHMENTS.format(slug=args.agent),
                         [n for n in attached if n != args.name])
    print(f"{args.name} detached from {args.agent}. It stays loadable by every agent.")
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


class AddressError(Exception):
    """An address that names no skill, saying which part could not be resolved."""


def resolve_address(address: str) -> tuple[str, str, str | None]:
    """(repository URL, path inside it, ref or None) from one browser address.

    The forms a person has in the clipboard are what a repository host shows
    while looking at a folder or a file:
    `https://host/<owner>/<repo>/tree/<ref>/<path>` and the `blob` form ending
    at a file, whose containing directory is what holds the skill.
    """
    trimmed = address.rstrip("/")
    if "://" not in trimmed:
        raise AddressError(
            f"'{address}' is not a URL. Pass a repository URL and the path "
            f"inside it as two arguments, or paste the address of the skill's "
            f"folder.")
    scheme, _, rest = trimmed.partition("://")
    host, _, tail = rest.partition("/")
    parts = [p for p in tail.split("/") if p]
    if len(parts) < 2:
        raise AddressError(f"'{address}' names no repository on {host}.")
    owner, repo = parts[0], parts[1]
    remainder = parts[2:]
    # GitLab spells the same two views /-/tree/ and /-/blob/.
    if remainder[:1] == ["-"]:
        remainder = remainder[1:]
    if not remainder:
        raise AddressError(
            f"'{address}' names the repository {owner}/{repo} and no path "
            f"inside it, so it names no skill. Open the skill's own folder and "
            f"paste that address, or pass the path as a second argument.")
    view = remainder[0]
    if view not in {"tree", "blob"}:
        raise AddressError(
            f"'{address}' has no /tree/ or /blob/ segment, so the ref and the "
            f"path inside {owner}/{repo} cannot be told apart. Paste the "
            f"address the repository shows while you are looking at the skill's "
            f"folder.")
    if len(remainder) < 3:
        raise AddressError(
            f"'{address}' names a ref in {owner}/{repo} and no path after it, "
            f"so it names no skill.")
    ref = remainder[1]
    inside = remainder[2:]
    if view == "blob":
        inside = inside[:-1]
        if not inside:
            raise AddressError(
                f"'{address}' names a file at the root of {owner}/{repo}, "
                f"which is not a skill directory.")
    return f"{scheme}://{host}/{owner}/{repo}.git", "/".join(inside), ref


def cmd_install(args) -> int:
    root = quarantine_root()
    if root is None:
        print("config declares no skills.install_dir; nowhere to install to.", file=sys.stderr)
        return 1

    ref = None
    if args.path is None:
        try:
            repo, path, ref = resolve_address(args.repo)
        except AddressError as failure:
            print(failure, file=sys.stderr)
            return 1
    else:
        repo, path = args.repo, args.path

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "repo"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo, str(clone)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(result.stderr.strip() or "clone failed", file=sys.stderr)
            return 1
        if ref is not None:
            # One fetch covers a branch, a tag and a commit alike; a default
            # branch that already is the ref makes it a no-op.
            fetched = subprocess.run(
                ["git", "-C", str(clone), "fetch", "--depth", "1", "origin", ref],
                capture_output=True, text=True,
            )
            if fetched.returncode == 0:
                subprocess.run(
                    ["git", "-C", str(clone), "checkout", "--detach", "FETCH_HEAD"],
                    capture_output=True, text=True,
                )
            else:
                print(f"'{ref}' could not be fetched; reading the default branch.",
                      file=sys.stderr)
        source = clone / path
        if not (source / "SKILL.md").is_file():
            print(f"{path} holds no SKILL.md in {repo}.", file=sys.stderr)
            return 1
        name = args.name or read_frontmatter(source / "SKILL.md").get("name") or source.name
        if find_skill(name, include_quarantine=True) is not None:
            print(f"A skill named '{name}' is already present.", file=sys.stderr)
            return 1
        target = data_paths.ensure_dir(root) / name
        shutil.copytree(source, target)
        rows = _inventory(target)
        commit = subprocess.run(
            ["git", "-C", str(clone), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        ).stdout.strip() or ABSENT
        licence, licence_source = find_licence(clone, source)
        record = {"repo": repo, "path": path, "commit": commit,
                  "license": licence, "license_source": licence_source}
        (target / ORIGIN_FILE).write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")

    total = sum(r[1] for r in rows)
    print(f"Quarantined at {target}")
    print(f"From {repo} {path} at {commit[:12]}")
    print(f"Licence: {licence} (from {licence_source})")
    print(f"{len(rows)} files, {total} bytes. Not listed and not loadable until trusted.\n")
    width = max(len(str(r[0])) for r in rows)
    for rel, size, digest in rows:
        mark = "*" if _is_script(rel) else " "
        print(f"{mark} {str(rel):<{width}}  {size:>9}  {digest[:16]}")
    print("\n* is executable code. Read it before trusting the skill:")
    print(f"    python3 skills.py audit {name}")
    print_compatibility(target)
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


def declared_dependencies(path: Path) -> list[str]:
    """The skills a definition's frontmatter names, in the order it names them.

    Reads the block itself rather than the parsed fields, because a dependency
    is usually a YAML list and `split_frontmatter` carries scalars only. An
    inline value may be bracketed or comma-separated; an indented `- item` run
    under the key is read the same way.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].lstrip("\ufeff").rstrip() != "---":
        return []
    found: list[str] = []
    collecting = False
    for line in lines[1:]:
        if line.rstrip() == "---":
            break
        stripped = line.strip()
        if collecting:
            if stripped.startswith("- "):
                found.append(stripped[2:].strip().strip('"').strip("\''"))
                continue
            collecting = False
        if line[:1] in {" ", "\t", "#"} or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if key.strip().lower() not in DEPENDENCY_KEYS:
            continue
        inline = value.strip().strip("[]")
        if inline:
            found.extend(part.strip().strip('"').strip("\''")
                         for part in inline.split(",") if part.strip())
        else:
            collecting = True
    seen: set[str] = set()
    return [d for d in found if d and not (d in seen or seen.add(d))]


def foreign_gates(path: Path) -> list[tuple[str, list[str]]]:
    """(consequence, names) for every FOREIGN_GATES key a SKILL.md declares.

    Reads the frontmatter block itself rather than the parsed fields: these keys
    carry lists, two of them are nested under `metadata.hermes`, and one is a
    list of mappings whose `name` is the variable. A key's own name is the
    match, at whatever indentation it sits, and indentation is what ends its
    block, so a mapping item's other fields are skipped rather than read as
    values.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].lstrip("\ufeff").rstrip() != "---":
        return []

    def clean(raw: str) -> str:
        return raw.strip().strip('"').strip("'")

    found: dict[str, list[str]] = {}
    group: str | None = None
    key_indent = 0
    for line in lines[1:]:
        if line.rstrip() == "---":
            break
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if group is not None:
            if not stripped:
                continue
            if indent > key_indent:
                if stripped.startswith("- "):
                    item = stripped[2:].strip()
                    name, sep, value = item.partition(":")
                    found[group].append(clean(value) if sep and name.strip() == "name"
                                        else clean(item))
                continue
            group = None
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        if key not in FOREIGN_GATES:
            continue
        group = FOREIGN_GATES[key]
        key_indent = indent
        found.setdefault(group, [])
        inline = value.strip().strip("[]")
        if inline:
            found[group].extend(clean(part) for part in inline.split(",") if part.strip())
            group = None
    out = []
    for g in GATE_CONSEQUENCE:
        if g not in found:
            continue
        seen: set[str] = set()
        names = [n for n in found[g] if n and not (n in seen or seen.add(n))]
        # A key naming nothing is not a gate. `requires_toolsets: []` is a
        # skill saying it needs none, and reporting it would be a false alarm.
        if names:
            out.append((g, names))
    return out


def print_compatibility(source: Path) -> None:
    """Say what a skill's own frontmatter declares that has no reader here.

    Nothing is printed for a skill carrying only fields the specification
    defines, and nothing here refuses an install: what a gated skill is worth is
    the person's call, and its body may be worth reading whatever the gate says.
    """
    gates = foreign_gates(source / "SKILL.md")
    if not gates:
        return
    print("\nCompatibility")
    for group, values in gates:
        named = ", ".join(values) if values else "none named"
        print(f"  {GATE_CONSEQUENCE[group]}: {named}.")
    print("  It installs and trusts either way; this is what to expect from it, "
          "not a refusal.")


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
    needs = declared_dependencies(source)
    if needs:
        print(f"Names the skills it depends on: {', '.join(needs)}\n"
              f"    install each one before this skill is of any use:\n"
              f"    python3 skills.py install <repo-url> <path-in-repo>")
    else:
        print("Declares no skills it depends on. One stated in the body alone is "
              "not read here.")
    if len(description) > DESCRIPTION_ROUTING_LIMIT:
        print(f"description is {len(description)} characters; past "
              f"{DESCRIPTION_ROUTING_LIMIT} a client's index truncates it and the "
              f"routing signal is what is lost. Rewrite it before trusting.")
    print(f"Not listed and not loadable until trusted:\n"
          f"    python3 skills.py audit {name}\n"
          f"    python3 skills.py trust {name}")
    return 0


def scan(skill_dir: Path) -> dict | None:
    """The scanner's findings over a skill's directory, or None where it could
    not run. A scanner that finds something exits non-zero, so the report is
    taken from what it printed rather than from its status."""
    proc = subprocess.run(
        [sys.executable, "-m", SCANNER, "-q", "-f", "json", "-r", str(skill_dir)],
        capture_output=True, text=True,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return report if isinstance(report, dict) else None


def scan_lines(skill_dir: Path) -> list[str]:
    """The scan section of an audit: what the scanner found, and what it did not
    read. Named per file rather than summarised, since the point of the section
    is to send a reader to a line."""
    unread = sorted(str(rel) for rel, _, _ in _inventory(skill_dir)
                    if _is_script(rel) and rel.suffix.lower() != SCANNER_READS)
    report = scan(skill_dir)
    if report is None:
        return [f"=== scan ===",
                f"No scanner. {SCANNER} is not installed for this interpreter, so "
                f"nothing has read this code but you.",
                f"    {Path(sys.executable).name} -m pip install {SCANNER}"]
    out = [f"=== scan ({SCANNER}) ==="]
    for issue in report.get("results", []):
        where = Path(issue.get("filename", "")).name
        out.append(f"{issue.get('issue_severity', '?'):<8} "
                   f"{issue.get('test_id', '?')} {issue.get('issue_text', '')} "
                   f"— {where}:{issue.get('line_number', '?')}")
    if len(out) == 1:
        out.append("Nothing found.")
    for error in report.get("errors", []):
        out.append(f"unread    {error.get('filename', '?')}: {error.get('reason', '')}")
    if unread:
        out.append(f"Not read by {SCANNER}, which reads {SCANNER_READS} only: "
                   + ", ".join(unread))
    out.append("A report is evidence. Trust is yours to give, and nothing here "
               "gives it.")
    return out


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

    record = read_origin(skill_dir)
    if record:
        print("=== origin ===")
        for key in ("repo", "path", "commit", "license", "license_source"):
            print(f"{key}: {record.get(key, ABSENT)}")
        print()
    for line in scan_lines(skill_dir):
        print(line)
    print()
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

    p_list = sub.add_parser(
        "list", help="every loadable skill: name and description only")
    p_list.add_argument("--agent", help="put this agent's attached skills first")

    p_view = sub.add_parser("view", help="load one skill's body")
    p_view.add_argument("name")

    p_install = sub.add_parser("install", help="fetch a skill into quarantine")
    p_install.add_argument(
        "repo", metavar="address",
        help="the address of the skill's folder, or the repository's git URL")
    p_install.add_argument(
        "path", nargs="?",
        help="the skill's directory inside that repository, where the first "
             "argument is a bare repository URL")
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

    p_attach = sub.add_parser("attach", help="attach a skill to an agent")
    p_attach.add_argument("name")
    p_attach.add_argument("--agent", required=True)

    p_detach = sub.add_parser("detach", help="remove a skill from an agent")
    p_detach.add_argument("name")
    p_detach.add_argument("--agent", required=True)

    args = parser.parse_args(argv)
    return {
        "list": cmd_list, "view": cmd_view, "install": cmd_install,
        "convert": cmd_convert, "audit": cmd_audit, "trust": cmd_trust,
        "attach": cmd_attach, "detach": cmd_detach,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
