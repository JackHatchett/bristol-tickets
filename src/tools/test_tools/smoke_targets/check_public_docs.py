"""smoke_targets/check_public_docs.py — the `public_docs` smoke target, run by smoke.py."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path, PurePosixPath

from qt_headless import PROJECT_ROOT
from smoke_targets.failure import SmokeFailure

# The documents a stranger reads on GitHub, from the project root. Every page
# under docs/ is added to these.
PUBLIC_DOCS = ("README.md", "CONTRIBUTING.md", "src/tools/bristol/BUILD_APP.md")

# What an installation makes for itself: a path under these is the reader's own,
# and a fresh clone has none of it.
MADE_AT_INSTALL = ("data/", "config/config.local.json")

# Words a document counts the shipped agents in.
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}  # fmt: skip
_N = r"\b(" + "|".join(NUMBER_WORDS) + r"|\d+)\s+"
COUNT = re.compile(
    "|".join(
        _N + tail
        for tail in (
            r"(?:shipped|readymade|built-in)\s+agents\b",
            r"roles\b",
            r"(?:agents\s+)?ship\s+with\s+Bristol\b",
        )
    ),
    re.IGNORECASE,
)


def public_documents(root: Path) -> list[Path]:
    """Every public document there is, in a fixed order."""
    docs = [root / name for name in PUBLIC_DOCS if (root / name).is_file()]
    return docs + sorted((root / "docs").glob("*.md"))


def shipped_agents(root: Path) -> list[str]:
    """The agents Bristol ships: one per charter under src/agent_identities/."""
    return sorted(p.stem for p in (root / "src" / "agent_identities").glob("*.md"))


def _given_paths(text: str) -> list[str]:
    """The repository paths and python3 scripts a document gives."""
    found = re.findall(r"`([^`\s]+)`", text)
    found += re.findall(r"\]\(([^)\s#]+)", text)
    found += re.findall(r"python3\s+([^\s`'\"]+\.py)\b", text)
    return found


def _missing(root: Path, doc: Path, given: str) -> bool:
    """Whether a path a document gives is a repository path that is not on disk."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", given) or any(c in given for c in "<>*~${}"):
        return False
    path = given.rstrip(".,;:)").strip("/")
    if "/" not in path or path.startswith(MADE_AT_INSTALL) or path in MADE_AT_INSTALL:
        return False
    from_root = root / os.path.normpath(path)
    from_doc = root / os.path.normpath(str(PurePosixPath(doc.parent.relative_to(root)) / path))
    if from_root.exists() or from_doc.exists():
        return False
    # A path that starts at no folder of the project is the reader's own, such
    # as a folder on their machine; one that does is the repository's.
    first = path.split("/")[0]
    return (root / first).is_dir() or from_doc.parent.is_dir()


def check_public_docs() -> list[str]:
    ok: list[str] = []
    root = PROJECT_ROOT
    docs = public_documents(root)
    if not docs:
        raise SmokeFailure("no public document was found to check")

    # Every repository path and script a document gives is on disk.
    stale: list[str] = []
    for doc in docs:
        for given in _given_paths(doc.read_text(encoding="utf-8")):
            if _missing(root, doc, given):
                stale.append(f"{doc.relative_to(root)} gives {given}")
    if stale:
        raise SmokeFailure(
            "a public document gives a path or a script the repository does not have:\n    "
            + "\n    ".join(sorted(set(stale)))
        )
    ok.append(f"every path and python3 script {len(docs)} public documents give is on disk")

    # Every shipped agent is documented, offered at install, and counted right.
    agents = shipped_agents(root)
    agents_doc = (root / "docs" / "agents.md").read_text(encoding="utf-8")
    sections = set(re.findall(r"(?m)^## ([a-z_]+)\s*$", agents_doc))
    undocumented = [a for a in agents if a not in sections]
    if undocumented:
        raise SmokeFailure(f"docs/agents.md has no section for {', '.join(undocumented)}")
    example = json.loads((root / "config" / "config.example.json").read_text(encoding="utf-8"))
    offered = set(example.get("agents", {}))
    unoffered = [a for a in agents if a not in offered]
    if unoffered:
        raise SmokeFailure(
            f"config/config.example.json, which the setup wizard offers from, leaves out "
            f"{', '.join(unoffered)}"
        )
    miscounted: list[str] = []
    for doc in docs:
        for match in COUNT.finditer(doc.read_text(encoding="utf-8")):
            word = next(g for g in match.groups() if g).lower()
            number = NUMBER_WORDS.get(word) or int(word)
            if number != len(agents):
                miscounted.append(f"{doc.relative_to(root)}: {match.group(0)!r}")
    if miscounted:
        raise SmokeFailure(
            f"{len(agents)} agents ship, and a public document counts otherwise:\n    "
            + "\n    ".join(miscounted)
        )
    ok.append(
        f"the {len(agents)} shipped agents each have a section in docs/agents.md and an "
        "entry in config.example.json, and every count of them agrees"
    )
    return ok
