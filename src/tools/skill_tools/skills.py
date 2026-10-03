#!/usr/bin/env python3
"""skills.py — install, list and load Agent Skills.

A skill is a directory holding a SKILL.md whose YAML frontmatter carries `name`
and `description`, per the Agent Skills specification
(github.com/agentskills/agentskills). Two roots hold them:

    native      src/skills/ in this repository — Bristol's own converted
                procedures, published with the code.
    installed   the path declared at `skills.install_dir` in config, resolved
                through config_tools/data_paths.py. Git-ignored; third-party.

Progressive disclosure is the contract, not a suggestion. `list` reads each
SKILL.md only as far as the frontmatter terminator and never touches the body;
`view` is the only command that loads a body.

An imported skill lands in `<install_dir>/<name>/` and is listed and loadable at
once. `audit` prints every script it carries. Nothing here executes a skill's
code.

An installed skill carries a `.origin.json` beside its SKILL.md holding the
repository, the path inside it, the resolved commit and the licence found, so
`list` can name where a skill came from and `audit` can answer both questions
without a second lookup. A source stating no licence records that as absent.

`install` scans the skill's code before anything is added: `bandit` for Python
and `semgrep` for every language. The import stops on a medium or high finding,
on a scanner that could not run, and on a code file no scanner read; a clean
skill lands with the result recorded beside its provenance. `audit` runs the
same scan again. What each reads is README.md §The scanner.

CLI
---
    python3 skills.py list [--agent SLUG]
    python3 skills.py view <name>
    python3 skills.py install <address> [--name NAME]
    python3 skills.py install <repo-url> <path-in-repo> [--name NAME]
    python3 skills.py convert <file.md> [--name NAME] [--description TEXT]
    python3 skills.py audit <name>
    python3 skills.py attach <name> --agent SLUG
    python3 skills.py detach <name> --agent SLUG
    python3 skills.py package <name> [--out DIR]
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
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402
import write_config  # noqa: E402

# What an installed skill carries about where it came from, written beside its
# SKILL.md so the record moves with the directory and can never orphan. Dotted, so a client reading the skill by the
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

# The scanner `install` and `audit` run over a skill's code, invoked as a module
# so it is found wherever this interpreter's packages are rather than on PATH.
# requirements.txt lists it; an import whose Python it cannot scan stops.
# What it reads and what it does not is `src/tools/skill_tools/README.md`
# §The scanner.
SCANNER = "bandit"
SCANNER_READS = ".py"

# The second scanner, for every other language a skill's code is written in.
# Its rules come from the semgrep registry at scan time: the default security
# set, and the registry's bash rules, which the default set leaves out.
POLYGLOT = "semgrep"
POLYGLOT_CONFIGS = ("p/default", "r/bash")

# The code files semgrep's rules parse. Semgrep lists every file it opened, and
# a generic rule opens files in languages it has no parser for, so a file
# counts as read only where its language is one of these.
POLYGLOT_READS = {".sh", ".bash", ".js", ".mjs", ".ts", ".rb", ".py"}

# Semgrep's severities, put on bandit's scale so one rule decides both.
POLYGLOT_SEVERITY = {"ERROR": "HIGH", "WARNING": "MEDIUM", "INFO": "LOW"}

# The severities that stop an import. A LOW finding includes the notice that a
# file imports subprocess or pickle at all, which most tools with code do; it is
# recorded and shown on the skill.
BLOCKING_SEVERITIES = {"MEDIUM", "HIGH"}

# The only top-level frontmatter keys a conversion carries across. The
# specification defines a small set (src/skills/skill-conversion/SKILL.md
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

# What covers a Hermes toolset's ground here, where anything does. The table
# names only toolsets whose ground something here actually covers; a toolset
# absent from it is reported as uncovered, which is a statement about this table
# rather than a guess about the skill.
TOOLSET_GROUND = {
    "kanban": "the board — ticket_tools/ticket_write.py writes it and "
              "ticket_tools/status_common.py reads it",
    "tasks": "the board — ticket_tools/ticket_write.py writes it and "
             "ticket_tools/status_common.py reads it",
    "skills": "the loader — skill_tools/skills.py, which lists, installs, "
              "audits and attaches",
    "memory": "nothing, deliberately: a session's memory is the board — "
              "src/app.md §The board is the only channel",
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


def _skill_dirs(root: Path | None) -> list[Path]:
    if root is None or not root.is_dir():
        return []
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and not d.name.startswith(".") and (d / "SKILL.md").is_file()
    )


def find_skill(name: str) -> tuple[Path, str] | None:
    """Return (directory, origin) for a skill by directory name."""
    for root, origin in ((native_root(), "native"), (installed_root(), "installed")):
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
    parsed, except a Bristol key under `metadata` (`  bristol.subtitle: …`),
    which is kept under its dotted name.
    """
    fields: dict[str, str] = {}
    with skill_md.open(encoding="utf-8") as fh:
        first = fh.readline()
        if first.lstrip("﻿").rstrip() != "---":
            return fields
        for line in fh:
            if line.rstrip() == "---":
                break
            if line[:1] in {" ", "\t"} and line.strip().startswith("bristol.") \
                    and ":" in line:
                key, _, value = line.strip().partition(":")
                fields[key.strip()] = value.strip().strip('"').strip("'")
                continue
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


def _files_and_scripts(skill_dir: Path) -> tuple[list[str], list[str]]:
    """(every file in a skill, and which of them are code), both relative to the
    skill's own directory.

    `_inventory` answers the same question and hashes every file to do it, which
    is what an install's one-time inventory wants and what a listing of every
    skill on the machine cannot afford.
    """
    everything: list[str] = []
    scripts: list[str] = []
    for f in sorted(skill_dir.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(skill_dir))
        everything.append(rel)
        if _is_script(Path(rel)):
            scripts.append(rel)
    return everything, scripts


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
    if getattr(args, "json", False):
        print(json.dumps(_listing(), indent=2))
        return 0
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
    return 0


# ---------------------------------------------------------------------------
# How a skill reads to a person
# ---------------------------------------------------------------------------
#
# One skill, three facts a reader has to be told rather than left to infer:
# where it came from, what is inside it, and which agents hold it. Every surface
# that shows a skill says them in these words, so the app, a detail view and an
# import report never teach the same fact twice.

_NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten", "eleven", "twelve")


def _spell(count: int) -> str:
    """A small number as the word a person would say, so the number and the
    noun beside it agree."""
    return _NUMBER_WORDS[count] if 0 <= count < len(_NUMBER_WORDS) else str(count)


def source_url(origin: dict) -> str:
    """The web address of the exact source a skill was taken from, built from
    its provenance record: the repository, the commit, and the path inside it.
    Empty for a skill with no record, which is every native one."""
    repo = (origin.get("repo") or "").rstrip("/").removesuffix(".git")
    commit = origin.get("commit", "")
    if not repo or not commit or commit == ABSENT:
        return ""
    if repo.startswith("git@"):
        host, _, rest = repo.partition(":")
        repo = f"https://{host.removeprefix('git@')}/{rest}"
    inside = (origin.get("path") or "").strip("/")
    return f"{repo}/tree/{commit}" + (f"/{inside}" if inside else "")


def origin_phrase(record: dict) -> str:
    """Where a skill came from. A reader is told outright rather than being
    expected to know that a root name is an answer."""
    if record.get("root") == "native":
        return "Came with Bristol"
    if not record.get("repo"):
        return "Downloaded, source not recorded"
    return f"Downloaded from {record.get('origin', '')}"


def contents_phrase(record: dict) -> str:
    """What is inside a skill. A skill carrying code and one carrying none are
    not the same risk, so they are not the same sentence."""
    files = int(record.get("files", 0))
    scripts = len(record.get("scripts", []))
    total = f"{_spell(files)} file" + ("" if files == 1 else "s")
    if not scripts:
        return f"{total}, no code"
    if files == 1:
        return f"{total}, and it is code"
    if scripts == files:
        return f"{total}, all of them code"
    return f"{total}, {_spell(scripts)} of them code"


def scan_phrase(record: dict) -> str:
    """What the import's scan found, for a downloaded skill carrying code.
    Empty for a skill with no code and for a native one."""
    if record.get("root") == "native" or not record.get("scripts"):
        return ""
    scan_record = record.get("scan") or {}
    if not scan_record.get("scanners") or scan_record.get("unread") \
            or not scan_record.get("ran"):
        return "Code not fully scanned"
    found = len(scan_record.get("findings", []))
    if not found:
        return "Scanned, nothing found"
    return (f"Scanned, {_spell(found)} low-severity note"
            + ("" if found == 1 else "s"))


# Words a title leaves lowercase unless they open it: articles, conjunctions
# and short prepositions.
TITLE_SMALL = {"a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet",
               "as", "at", "by", "in", "of", "on", "to", "per", "via", "vs",
               "with", "from", "into"}
# Words a title writes in capitals, because that is how they are read.
TITLE_UPPER = {"ai", "api", "csv", "html", "jd", "pdf", "qa", "ui", "url"}


def title_phrase(name: str) -> str:
    """A skill's name as a person reads it: checking-a-wiki-for-disagreements
    is Checking a Wiki for Disagreements. The name itself stays as written,
    since the Agent Skills standard requires the hyphenated form."""
    words = [w for w in name.replace("_", "-").split("-") if w]
    out = []
    for i, word in enumerate(words):
        low = word.lower()
        if low in TITLE_UPPER:
            out.append(low.upper())
        elif i and low in TITLE_SMALL:
            out.append(low)
        else:
            out.append(low[:1].upper() + low[1:])
    return " ".join(out)


def subtitle_phrase(fields: dict) -> str:
    """What a skill does, short: its bristol.subtitle where it declares one,
    otherwise its description's first sentence."""
    if fields.get("subtitle_declared"):
        return fields["subtitle_declared"]
    text = fields.get("description", "").strip()
    for stop in (". ", " — ", " (", ": "):
        end = text.find(stop)
        if end > 0:
            text = text[:end]
    return text.rstrip(".")


def holders_phrase(holders: list[str]) -> str:
    """Which agents hold a skill, including when the answer is none."""
    return "Held by " + (", ".join(holders) if holders else "no agent")


def _skill_record(skill_dir: Path, root_name: str) -> dict:
    """One skill as data: what `list` prints, plus what a surface needs to say
    the same things a session is told."""
    fm = read_frontmatter(skill_dir / "SKILL.md")
    record = read_origin(skill_dir)
    contents, scripts = _files_and_scripts(skill_dir)
    fields = {
        "name": fm.get("name", skill_dir.name),
        "directory": skill_dir.name,
        "description": fm.get("description", ""),
        "origin": _origin_column(skill_dir, root_name),
        "root": root_name,
        "repo": record.get("repo", ""),
        "commit": record.get("commit", ""),
        "license": record.get("license", "") or fm.get("license", ""),
        "license_source": record.get("license_source", ""),
        "files": len(contents),
        "file_list": contents,
        "scripts": scripts,
        "path": str(skill_dir),
        "source_url": source_url(record),
        "scan": record.get("scan", {}),
        "subtitle_declared": fm.get("bristol.subtitle", ""),
    }
    fields["title"] = title_phrase(fields["name"])
    fields["subtitle"] = subtitle_phrase(fields)
    fields["said_origin"] = origin_phrase(fields)
    fields["said_contents"] = contents_phrase(fields)
    fields["said_scan"] = scan_phrase(fields)
    return fields


def _listing() -> dict:
    """Every skill on this machine, plus which agent
    attaches which. One read, so a surface and a session cannot disagree about a
    name, a description or an origin.

    Each skill carries its three facts already worded — `said_origin`,
    `said_contents`, `said_holders` — so every surface that shows a skill shows
    the same sentence rather than composing its own.
    """
    skills = []
    for root, root_name in ((native_root(), "native"),
                            (installed_root(), "installed")):
        for d in _skill_dirs(root):
            skills.append(_skill_record(d, root_name))
    agents = {slug: attached_to(slug) for slug in _agent_slugs()}
    for record in skills:
        holders = sorted(slug for slug, names in agents.items()
                         if record["name"] in names)
        record["holders"] = holders
        record["said_holders"] = holders_phrase(holders)
    return {
        "skills": skills,
        "agents": agents,
    }


def _known_skill(name: str) -> bool:
    return any(r[0] == name for r in _all_skills())


def cmd_attach(args) -> int:
    _require_agent(args.agent)
    if not _known_skill(args.name):
        raise SystemExit(
            f"no skill '{args.name}'. `list` gives every skill there is.")
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
        print(f"No skill named '{args.name}'.", file=sys.stderr)
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
        # A repository whose SKILL.md sits at its top level is the skill; the
        # install checks for that file and says so where it is missing.
        return f"{scheme}://{host}/{owner}/{repo}.git", "", None
    view = remainder[0]
    if view not in {"tree", "blob"}:
        raise AddressError(
            f"'{address}' has no /tree/ or /blob/ segment, so the ref and the "
            f"path inside {owner}/{repo} cannot be told apart. Paste the "
            f"address the repository shows while you are looking at the skill's "
            f"folder.")
    if len(remainder) < 2:
        raise AddressError(
            f"'{address}' has no ref after /{view}/ in {owner}/{repo}.")
    ref = remainder[1]
    inside = remainder[2:]
    if view == "blob":
        inside = inside[:-1]
    return f"{scheme}://{host}/{owner}/{repo}.git", "/".join(inside), ref


def cmd_install(args) -> int:
    root = installed_root()
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
            where = path or "The top level of the repository"
            print(f"{where} holds no SKILL.md in {repo}. Open the skill's own "
                  f"folder and paste that address.", file=sys.stderr)
            return 1
        name = args.name or read_frontmatter(source / "SKILL.md").get("name") or source.name
        if find_skill(name) is not None:
            print(f"A skill named '{name}' is already present.", file=sys.stderr)
            return 1
        # Scanned where it was fetched, so a skill the scan stops never
        # reaches the folder sessions load from.
        staged = Path(tmp) / "staged" / name
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns(".git"))
        checked = scan_record(staged)
        why = refusal(checked)
        if why:
            lines = "\n".join(f"  {line}" for line in
                              scan_report_lines(checked)[1:])
            print(f"Not imported: {name}, because {why}. Nothing was added.\n"
                  f"{lines}", file=sys.stderr)
            return 1
        target = data_paths.ensure_dir(root) / name
        shutil.copytree(staged, target)
        rows = _inventory(target)
        commit = subprocess.run(
            ["git", "-C", str(clone), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        ).stdout.strip() or ABSENT
        licence, licence_source = find_licence(clone, source)
        record = {"repo": repo, "path": path, "commit": commit,
                  "license": licence, "license_source": licence_source,
                  "scan": checked}
        (target / ORIGIN_FILE).write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")

    total = sum(r[1] for r in rows)
    print(f"Installed at {target}, listed and loadable now")
    print(f"From {repo} {path or '(top level)'} at {commit[:12]}")
    print(f"Licence: {licence} (from {licence_source})")
    print(f"{len(rows)} files, {total} bytes.\n")
    width = max(len(str(r[0])) for r in rows)
    for rel, size, digest in rows:
        mark = "*" if _is_script(rel) else " "
        print(f"{mark} {str(rel):<{width}}  {size:>9}  {digest[:16]}")
    if any(_is_script(rel) for rel, _size, _digest in rows):
        print("\n* is executable code.")
    print()
    for line in scan_report_lines(record["scan"]):
        print(line)
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
        # A gate with no reader here is half the answer; the other half is
        # whether the ground it names is covered by something else.
        if group in {"toolsets", "fallback"}:
            for name in values:
                ground = TOOLSET_GROUND.get(name.strip().lower())
                print(f"    {name}: {ground}." if ground
                      else f"    {name}: nothing here is declared as covering "
                           f"that ground.")
    print("  It installs either way; this is what to expect from it, "
          "not a refusal.")


def normalise_name(raw: str) -> str:
    """A skill name from arbitrary text: lowercased, non-name characters folded
    to hyphens, runs collapsed, ends trimmed. Returns '' when nothing survives."""
    lowered = "".join(c if c in NAME_CHARS else "-" for c in raw.strip().lower())
    while "--" in lowered:
        lowered = lowered.replace("--", "-")
    return lowered.strip("-")[:64]


def cmd_convert(args) -> int:
    """Write a foreign markdown definition into the install root as a skill folder.

    A subagent definition, a slash command and a prompt-pack entry are one object
    — a markdown body under frontmatter — and the half of that frontmatter which
    routes work has no reader in Bristol. This keeps the body and the two fields
    that make a skill loadable, and says what it dropped.
    """
    source = Path(args.source).expanduser()
    if not source.is_file():
        print(f"{source} is not a file.", file=sys.stderr)
        return 1
    root = installed_root()
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
    if find_skill(name) is not None:
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
    print(f"Installed at {target}, listed and loadable now")
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
              f"routing signal is what is lost. Rewrite it in {target / 'SKILL.md'}.")
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


def _polyglot_command() -> str | None:
    """The semgrep executable installed beside this interpreter, or on PATH."""
    beside = Path(sys.executable).parent / POLYGLOT
    if beside.is_file():
        return str(beside)
    return shutil.which(POLYGLOT)


def polyglot_scan(skill_dir: Path) -> dict | None:
    """Semgrep's report over a skill's directory, or None where it could not
    run — not installed, or its rules could not be fetched."""
    command = _polyglot_command()
    if command is None:
        return None
    args = [command, "--json", "--quiet", "--metrics=off"]
    for config in POLYGLOT_CONFIGS:
        args += ["--config", config]
    proc = subprocess.run(args + [str(skill_dir)], capture_output=True,
                          text=True)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(report, dict) or any(
            e.get("level") == "error" and "config" in e.get("message", "").lower()
            for e in report.get("errors", [])):
        return None
    return report


def _relative(name: str, skill_dir: Path) -> str:
    path = Path(name)
    try:
        return str(path.resolve().relative_to(skill_dir.resolve()))
    except ValueError:
        return path.name


def scan_record(skill_dir: Path) -> dict:
    """Every scan of a skill's code, as the record an import keeps beside the
    provenance: whether each scanner the code needed ran, each finding on one
    severity scale, and the code files no scanner read. A skill with no code
    records a scan with nothing to read."""
    scripts = [str(rel) for rel, _, _ in _inventory(skill_dir) if _is_script(rel)]
    record = {"scanners": [], "ran": True, "missing": [], "findings": [],
              "unread": []}
    if not scripts:
        return record
    read: set[str] = set()
    if any(name.endswith(SCANNER_READS) for name in scripts):
        report = scan(skill_dir)
        if report is None:
            record["ran"] = False
            record["missing"].append(SCANNER)
        else:
            record["scanners"].append(SCANNER)
            read |= {n for n in scripts if n.endswith(SCANNER_READS)}
            for issue in report.get("results", []):
                record["findings"].append({
                    "scanner": SCANNER,
                    "severity": str(issue.get("issue_severity", "?")).upper(),
                    "test": issue.get("test_id", "?"),
                    "text": issue.get("issue_text", ""),
                    "file": _relative(issue.get("filename", ""), skill_dir),
                    "line": issue.get("line_number", "?"),
                })
    report = polyglot_scan(skill_dir)
    if report is None:
        record["ran"] = False
        record["missing"].append(POLYGLOT)
    else:
        record["scanners"].append(POLYGLOT)
        read |= {_relative(n, skill_dir)
                 for n in report.get("paths", {}).get("scanned", [])
                 if Path(n).suffix.lower() in POLYGLOT_READS}
        for issue in report.get("results", []):
            extra = issue.get("extra", {})
            record["findings"].append({
                "scanner": POLYGLOT,
                "severity": POLYGLOT_SEVERITY.get(
                    str(extra.get("severity", "")).upper(), "HIGH"),
                "test": str(issue.get("check_id", "?")).rsplit(".", 1)[-1],
                "text": " ".join(str(extra.get("message", "")).split())[:200],
                "file": _relative(issue.get("path", ""), skill_dir),
                "line": issue.get("start", {}).get("line", "?"),
            })
    record["unread"] = sorted(n for n in scripts if n not in read)
    return record


def blocking(record: dict) -> list[dict]:
    """The findings in a scan record that stop an import."""
    return [f for f in record.get("findings", [])
            if str(f.get("severity", "")).upper() in BLOCKING_SEVERITIES]


def scan_report_lines(record: dict) -> list[str]:
    """A scan record as lines a reader can act on, each finding sent to a file
    and a line."""
    out = [f"=== scan ({', '.join(record.get('scanners', [])) or 'none'}) ==="]
    for name in record.get("missing", []):
        out.append(f"Not scanned: {name} is not installed for this interpreter, "
                   f"or its rules could not be fetched.")
        out.append(f"    {Path(sys.executable).name} -m pip install {name}")
    for f in record.get("findings", []):
        out.append(f"{f['severity']:<8} {f['test']} {f['text']} "
                   f"— {f['file']}:{f['line']}")
    if record.get("unread"):
        out.append("No scanner reads these: " + ", ".join(record["unread"]))
    if len(out) == 1:
        out.append("Nothing found." if record.get("scanners")
                   else "No code to scan.")
    return out


def refusal(record: dict) -> str:
    """Why an import stops, or '' where it goes ahead. Every code file has to
    have been read by a scanner that ran, and nothing it found may be medium or
    high."""
    if not record.get("ran"):
        return "a scanner it needs could not run"
    if blocking(record):
        return "the scan found a risk"
    if record.get("unread"):
        return "some of its code is in a language no scanner here reads"
    return ""


def cmd_audit(args) -> int:
    found = find_skill(args.name)
    if found is None:
        print(f"No skill named '{args.name}'.", file=sys.stderr)
        return 1
    skill_dir = found[0]

    record = read_origin(skill_dir)
    if record:
        print("=== origin ===")
        for key in ("repo", "path", "commit", "license", "license_source"):
            print(f"{key}: {record.get(key, ABSENT)}")
        print()
    for line in scan_report_lines(scan_record(skill_dir)):
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


def cmd_package(args) -> int:
    """Write a loadable skill out as a zip another host can take.

    The archive's root is the skill's own directory, which is the shape every
    reader of the specification expects. Nothing about how a skill arrives
    changes here: this is a second door, facing out.
    """
    found = find_skill(args.name)
    if found is None:
        print(f"No skill named '{args.name}'.", file=sys.stderr)
        return 1
    skill_dir, origin = found

    if args.out:
        out_dir = Path(args.out).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        declared = read_config.get("bristol_data.folders.staging", None)
        if not declared:
            print("No output directory: pass --out, or declare "
                  "bristol_data.folders.staging in config.", file=sys.stderr)
            return 1
        out_dir = data_paths.ensure_dir(declared)

    archive = out_dir / f"{args.name}.zip"
    inventory = [entry for entry in _inventory(skill_dir)
                 if str(entry[0]) != ORIGIN_FILE]
    record = read_origin(skill_dir)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, _, _ in inventory:
            zf.write(skill_dir / rel, str(Path(args.name) / rel))
        if record:
            zf.write(skill_dir / ORIGIN_FILE, str(Path(args.name) / ORIGIN_FILE))

    fields = read_frontmatter(skill_dir / "SKILL.md")
    print(f"Packaged at {archive}")
    print(f"Root of the archive: {args.name}/, holding {_spell(len(inventory))} "
          f"file{'' if len(inventory) == 1 else 's'}.")
    if record:
        print(f"Written by {record.get('repo', ABSENT)} at "
              f"{record.get('path', ABSENT)}, commit "
              f"{record.get('commit', ABSENT)[:12]}. Bristol installed it and "
              f"is not its source.")
        print(f"Licence: {record.get('license', ABSENT)} "
              f"(from {record.get('license_source', ABSENT)}). It travels under "
              f"that source's own terms.")
    elif origin == "native":
        print("Written for Bristol and published with it.")
        print(f"Licence: {fields.get('license', ABSENT)}, from the skill's own "
              f"frontmatter.")
    else:
        print("Installed before origins were recorded, so where it came from is "
              "not known here. Say so to whoever receives it.")
        print(f"Licence: {fields.get('license', ABSENT)}, from the skill's own "
              f"frontmatter.")
    print("A person loads this in the receiving host themselves. Nothing here "
          "reaches that host, and nothing here can tell you it arrived.")
    return 0


def cmd_remove(args) -> int:
    """Delete an installed skill, and detach it everywhere.

    A native skill is source under version control; removing one is an edit to
    the repository and is refused here, so this command can never be the route
    by which published code disappears.
    """
    found = find_skill(args.name)
    if found is None:
        print(f"No skill named '{args.name}'.", file=sys.stderr)
        return 1
    skill_dir, origin = found
    if origin == "native":
        print(f"'{args.name}' is a native skill under src/skills/. Remove it by "
              f"editing the repository, not from here.", file=sys.stderr)
        return 1
    # The directory goes first: a detachment recorded against a skill still on
    # disk is a skill nobody holds, which is recoverable, and the reverse is an
    # attachment naming nothing.
    try:
        shutil.rmtree(skill_dir)
    except OSError as exc:
        print(f"Could not remove {skill_dir}: {exc.strerror or exc}. Nothing was "
              f"detached.", file=sys.stderr)
        return 1
    holders = [slug for slug in _agent_slugs() if args.name in attached_to(slug)]
    for slug in holders:
        write_config.set_key(ATTACHMENTS.format(slug=slug),
                             [n for n in attached_to(slug) if n != args.name])
    held = f" It was attached to {', '.join(holders)}." if holders else ""
    print(f"Removed {args.name} from the install root.{held}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser(
        "list", help="every loadable skill: name and description only")
    p_list.add_argument("--agent", help="put this agent's attached skills first")
    p_list.add_argument(
        "--json", action="store_true",
        help="every skill, with its scan, and each agent's attachments, as data")

    p_view = sub.add_parser("view", help="load one skill's body")
    p_view.add_argument("name")

    p_install = sub.add_parser("install", help="fetch a skill, scan it and make it loadable")
    p_install.add_argument(
        "repo", metavar="address",
        help="the address of the skill's folder, or the repository's git URL")
    p_install.add_argument(
        "path", nargs="?",
        help="the skill's directory inside that repository, where the first "
             "argument is a bare repository URL")
    p_install.add_argument("--name", help="override the installed directory name")

    p_convert = sub.add_parser(
        "convert", help="write a foreign markdown definition in as a skill")
    p_convert.add_argument("source", help="the markdown file to convert")
    p_convert.add_argument("--name", help="override the skill and directory name")
    p_convert.add_argument("--description",
                           help="the trigger, where the source states none")

    p_audit = sub.add_parser("audit", help="print a skill's SKILL.md and every script it carries")
    p_audit.add_argument("name")

    p_attach = sub.add_parser("attach", help="attach a skill to an agent")
    p_attach.add_argument("name")
    p_attach.add_argument("--agent", required=True)

    p_detach = sub.add_parser("detach", help="remove a skill from an agent")
    p_detach.add_argument("name")
    p_detach.add_argument("--agent", required=True)

    p_remove = sub.add_parser(
        "remove", help="delete an installed skill and detach it")
    p_remove.add_argument("name")

    p_package = sub.add_parser(
        "package", help="write a loadable skill out as a zip another host can take")
    p_package.add_argument("name")
    p_package.add_argument(
        "--out", help="where to write the archive (default: the declared "
                      "staging location)")

    args = parser.parse_args(argv)
    return {
        "list": cmd_list, "view": cmd_view, "install": cmd_install,
        "convert": cmd_convert, "audit": cmd_audit,
        "attach": cmd_attach, "detach": cmd_detach, "remove": cmd_remove,
        "package": cmd_package,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
