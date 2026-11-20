#!/usr/bin/env python3
"""privacy_scan.py — refuse a history that contains a private name.

Reads the whole git history of the commits given, messages included, for every
name `published_tree.private_names` in the git-ignored config lists, and
reports each with the commit and the line. `smoke.py published_files` reads the
current tree alone; this reads every commit GitHub would receive.

    python3 privacy_scan.py [--rev REV ...]     # default HEAD

Exit 0 when nothing is found, 1 when something is, 2 when no name is configured.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "config_tools"))

import data_paths  # noqa: E402
import read_config  # noqa: E402


def names() -> list[str]:
    try:
        configured = read_config.get("published_tree.private_names")
    except Exception:
        configured = []
    return [str(n) for n in configured or [] if len(str(n)) > 2]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--rev", action="append")
    revs = parser.parse_args(argv).rev or ["HEAD"]
    needles = names()
    if not needles:
        print("privacy_scan: published_tree.private_names is empty", file=sys.stderr)
        return 2
    patterns = [
        (n, re.compile(r"(?<![a-z0-9])" + re.escape(n.lower()) + r"(?![a-z0-9])")) for n in needles
    ]
    log = subprocess.run(
        [
            "git",
            "-C",
            str(data_paths.project_root()),
            "log",
            *revs,
            "-p",
            "--format=@@COMMIT %h%n%an%n%B",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
    ).stdout
    hits: dict[str, str] = {}
    count: dict[str, int] = {}
    commit = "?"
    for line in log.splitlines():
        if line.startswith("@@COMMIT "):
            commit = line[9:]
            continue
        low = line.lower()
        for n, pat in patterns:
            if pat.search(low):
                count[n] = count.get(n, 0) + 1
                hits.setdefault(n, f"{commit}  {line.strip()[:140]}")
    if not hits:
        print(f"PRIVACY OK: no private name in {' '.join(revs)}")
        return 0
    print(f"PRIVACY FAIL: {len(hits)} private names in {' '.join(revs)}")
    for n in sorted(hits, key=lambda k: -count[k]):
        print(f"  {n}  ({count[n]} lines)  first: {hits[n]}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
