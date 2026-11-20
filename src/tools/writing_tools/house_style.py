#!/usr/bin/env python3
"""house_style.py — which house style a copyediting pass applies, and the file
of rules it applies.

The style in force is config, the `house_style` key of the agent's entry,
`agents.<agent>.house_style`. A style is built when its rules file is in the
house-style skill's references folder, `<style>.md`; the styles built are
exactly those files. A rules file whose line `Builds on: <style>` gives a base
style is read after that base, and its rules replace the base rules they name.

CLI
---
    python3 house_style.py <agent>              the style in force, and its rules files, base first
    python3 house_style.py <agent> --style X    the same for style X
    python3 house_style.py --list               every style built

A style that is set but not built exits 2 and gives the style by name with the
styles that are built.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STYLES_DIR = ROOT / "src" / "skills" / "copyediting-to-a-house-style" / "references"

sys.path.insert(0, str(ROOT / "src" / "tools" / "config_tools"))


def built() -> list[str]:
    """Every house style with a rules file, alphabetically."""
    if not STYLES_DIR.is_dir():
        return []
    return sorted(p.stem for p in STYLES_DIR.glob("*.md"))


def in_force(agent: str) -> str | None:
    """The style `agents.<agent>.house_style` sets, or None where it is unset."""
    import read_config

    value = read_config.get(f"agents.{agent}.house_style", None)
    return value if isinstance(value, str) and value else None


def rules_file(style: str) -> Path:
    """The rules file of a built style. Raises LookupError for one not built."""
    path = STYLES_DIR / f"{style}.md"
    if not path.is_file():
        have = ", ".join(built()) or "none"
        raise LookupError(f"house style '{style}' is not built; built: {have}")
    return path


BUILDS_ON = re.compile(r"^Builds on: (\S+)\s*$", re.MULTILINE)


def chain(style: str) -> list[Path]:
    """The rules files a style is applied from, base first. Raises LookupError
    for a style, or a base, that is not built, and for a base that loops."""
    files: list[Path] = []
    seen: set[str] = set()
    current: str | None = style
    while current is not None:
        if current in seen:
            raise LookupError(f"house style '{style}' builds on itself through '{current}'")
        seen.add(current)
        path = rules_file(current)
        files.insert(0, path)
        found = BUILDS_ON.search(path.read_text(encoding="utf-8"))
        current = found.group(1) if found else None
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("agent", nargs="?", help="the agent whose house_style is read")
    parser.add_argument("--style", help="a style to resolve in place of the one in force")
    parser.add_argument("--list", action="store_true", help="list every style built")
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(built()))
        return 0
    if not args.agent and not args.style:
        parser.error("give an agent, --style, or --list")

    style = args.style or in_force(args.agent)
    if style is None:
        print(f"agents.{args.agent}.house_style is not set", file=sys.stderr)
        return 2
    try:
        files = chain(style)
    except LookupError as exc:
        print(exc, file=sys.stderr)
        return 2
    for path in files:
        print(f"{style}\t{path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
