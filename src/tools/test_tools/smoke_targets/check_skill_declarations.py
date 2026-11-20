"""smoke_targets/check_skill_declarations.py — the `skill_declarations` smoke target, run by smoke.py."""

from __future__ import annotations

from pathlib import Path

from qt_headless import PROJECT_ROOT
from smoke_targets.failure import SmokeFailure


def declared_scripts(skill_md: Path) -> list[str]:
    """The `metadata.bristol.scripts` a skill declares, as written.

    Read line by line rather than with a YAML parser, for the same reason the
    loader reads frontmatter that way: the file is read as far as the closing
    delimiter and no further, and no dependency is added to run a smoke check.
    """
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    for line in lines[1:]:
        if line.strip() == "---":
            return []
        if line.startswith("  bristol.scripts:"):
            return line.split(":", 1)[1].split()
    return []


def check_skill_declarations() -> list[str]:
    """Every script a native skill declares is on disk.

    A skill names a command in a sentence, and prose is not checkable. The
    declaration is what makes a renamed or deleted tool a failure here rather
    than a command that does not run halfway through a task.
    """
    root = PROJECT_ROOT
    skills = sorted((root / "src" / "skills").glob("*/SKILL.md"))
    if not skills:
        raise SmokeFailure("no native skills found; the skills root moved")

    missing: dict[str, list[str]] = {}
    declared = 0
    for skill_md in skills:
        for rel in declared_scripts(skill_md):
            declared += 1
            if not (root / rel).is_file():
                missing.setdefault(rel, []).append(skill_md.parent.name)
    if missing:
        # Reported by tool rather than by skill: a renamed tool is one edit, and
        # what the person fixing it needs is every skill that names it.
        lines = [
            f"{rel} — declared by {', '.join(sorted(names))}"
            for rel, names in sorted(missing.items())
        ]
        raise SmokeFailure("a skill declares a script that is not there:\n  " + "\n  ".join(lines))

    holders = sum(1 for s in skills if declared_scripts(s))
    return [f"{declared} declared scripts across {holders} skills are all on disk"]
