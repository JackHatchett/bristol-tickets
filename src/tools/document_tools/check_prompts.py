#!/usr/bin/env python3
"""
check_prompts.py — Notebook assistant prompt-library checker
chief_of_staff tool

Reads every note in the notebook assistant's prompt folder and reports where it
departs from the contract in src/skills/notebook-prompt-library/SKILL.md. It
reports; it repairs nothing.

Both folders come from config — markdown_notebook.assistant_prompts_dir for the
library, markdown_notebook.notes_dir for the vault a wikilink has to resolve
inside — so the command takes no path argument.

Run from anywhere in the repository:
    python3 src/tools/document_tools/check_prompts.py

Exit status is 1 when any check matched, so the run composes in a shell.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402

REQUIRED_KEYS = (
    "copilot-command-context-menu-enabled",
    "copilot-command-slash-enabled",
    "copilot-command-context-menu-order",
    "copilot-command-model-key",
    "copilot-command-last-used",
)
PROMPT_TAG = "ai/prompt"
TEMPLATES_SUBDIR = "02_templates"
TEMPLATER = re.compile(r"<%.*?%>", re.DOTALL)
WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")
KEY = re.compile(r"^([A-Za-z0-9_@-]+):")
FENCE = re.compile(r"^\s*```")


# ── Reading a note ────────────────────────────────────────────────────────────

def split_frontmatter(text: str) -> tuple[list[str], str]:
    """The note's own frontmatter lines, and everything after it."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return [], text


def top_level_keys(lines: list[str]) -> list[str]:
    return [m.group(1) for line in lines if (m := KEY.match(line))]


def tag_values(lines: list[str]) -> list[str]:
    """Every tag in a frontmatter block, inline or as a list."""
    tags: list[str] = []
    collecting = False
    for line in lines:
        m = KEY.match(line)
        if m:
            collecting = m.group(1) == "tags"
            if collecting:
                inline = line.split(":", 1)[1].strip().strip("[]")
                tags += [t.strip().strip("\"'") for t in inline.split(",") if t.strip()]
            continue
        if collecting and line.strip().startswith("-"):
            tags.append(line.strip()[1:].strip().strip("\"'"))
    return [t for t in tags if t]


def emitted_blocks(body: str) -> list[list[str]]:
    """Frontmatter blocks inside the body — the shapes a prompt tells the
    assistant to write. Blocks inside a fenced code sample are examples of some
    other syntax and are skipped."""
    blocks: list[list[str]] = []
    lines = body.splitlines()
    fenced = False
    start = None
    for i, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if line.strip() != "---":
            continue
        if start is None:
            start = i
        else:
            blocks.append(lines[start + 1:i])
            start = None
    return blocks


# ── The vault a wikilink resolves in ──────────────────────────────────────────

def vault_targets(notes_dir: Path) -> set[str]:
    targets: set[str] = set()
    for path in notes_dir.rglob("*.md"):
        targets.add(path.stem.lower())
        targets.add(str(path.relative_to(notes_dir).with_suffix("")).lower())
    return targets


def link_target(raw: str) -> str:
    return raw.split("|", 1)[0].split("#", 1)[0].strip()


# ── The templates an emitted block may copy ───────────────────────────────────

def template_key_sets(notes_dir: Path) -> dict[str, set[str]]:
    sets: dict[str, set[str]] = {}
    for path in sorted((notes_dir / TEMPLATES_SUBDIR).glob("*.md")):
        front, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        keys = set(top_level_keys(front))
        if keys:
            sets[path.name] = keys
    return sets


# ── The checks ────────────────────────────────────────────────────────────────

def check_note(path: Path, targets: set[str],
               templates: dict[str, set[str]]) -> list[str]:
    findings: list[str] = []
    text = path.read_text(encoding="utf-8")
    front, body = split_frontmatter(text)

    if not front:
        return [f"{path.name}: no frontmatter block"]

    keys = top_level_keys(front)
    for required in REQUIRED_KEYS:
        if required not in keys:
            findings.append(f"{path.name}: missing key {required}")
    if PROMPT_TAG not in tag_values(front):
        findings.append(f"{path.name}: missing tag {PROMPT_TAG}")

    for raw in WIKILINK.findall(text):
        target = link_target(raw)
        if target and target.lower() not in targets:
            findings.append(f"{path.name}: wikilink [[{target}]] resolves to no note")

    for block in emitted_blocks(body):
        block_text = "\n".join(block)
        for expr in TEMPLATER.findall(block_text):
            findings.append(
                f"{path.name}: emitted frontmatter holds the Templater "
                f"expression {expr.strip()}, which the assistant cannot execute"
            )
        emitted = set(top_level_keys(block))
        if not emitted:
            continue
        if any(tkeys <= emitted for tkeys in templates.values()):
            continue
        nearest = max(templates.items(), key=lambda kv: len(kv[1] & emitted),
                      default=(None, set()))
        near = f"; nearest is {nearest[0]}" if nearest[0] else ""
        findings.append(
            f"{path.name}: emitted frontmatter ({', '.join(sorted(emitted))}) "
            f"carries no template's key set{near}"
        )
    return findings


def check_orders(notes: dict[Path, list[str]]) -> list[str]:
    """One order number per prompt, across the library."""
    seen: dict[str, list[str]] = {}
    for path, front in notes.items():
        for line in front:
            if line.startswith("copilot-command-context-menu-order:"):
                seen.setdefault(line.split(":", 1)[1].strip(), []).append(path.name)
    return [
        f"order {order} is on {len(names)} prompts: {', '.join(sorted(names))}"
        for order, names in sorted(seen.items()) if len(names) > 1
    ]


def main() -> int:
    if not read_config.get("markdown_notebook.assistant_prompts_dir", None):
        print("check_prompts: config declares no "
              "markdown_notebook.assistant_prompts_dir")
        return 1
    library = data_paths.resolve(read_config.get("markdown_notebook.assistant_prompts_dir"))
    notes_dir = data_paths.resolve(read_config.get("markdown_notebook.notes_dir"))

    if not library.is_dir():
        print(f"check_prompts: the prompt folder does not exist yet: {library}")
        return 1

    paths = sorted(library.glob("*.md"))
    if not paths:
        print(f"check_prompts: no prompt notes in {library}")
        return 1

    targets = vault_targets(notes_dir)
    templates = template_key_sets(notes_dir)

    findings: list[str] = []
    fronts: dict[Path, list[str]] = {}
    for path in paths:
        fronts[path] = split_frontmatter(path.read_text(encoding="utf-8"))[0]
        findings += check_note(path, targets, templates)
    findings += check_orders(fronts)

    print(f"{len(paths)} prompt notes in {library}")
    if not findings:
        print("Every check matched nothing.")
        return 0
    print()
    for line in findings:
        print(f"  {line}")
    print()
    print(f"{len(findings)} finding(s). "
          f"The contract is src/skills/notebook-prompt-library/SKILL.md.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
