#!/usr/bin/env python3
"""smoke.py — runtime-error smoke checks for the fleet's PySide6 GUI tools.

What it is: a fast "does it still build and run" check. It constructs each
GUI's real widgets on Qt's offscreen platform and reports any import error,
signal/slot mismatch, or construction-time exception. What it is NOT: a visual
check — offscreen paints nothing, so how a window *looks* still needs a real
display (the packaged Mac app).

Each target is a module of its own, ``smoke_targets/check_<target>.py``, defining
``check_<target>()``; ``TARGETS`` below lists them in the order a full run
takes. Each is checked in its OWN subprocess because every GUI tool ships a
top-level package named ``ui`` (and its own ``app.py``), which cannot coexist
in one interpreter. Run everything, or one target:

    bash run_smoke.sh                 # provision env + check all targets
    bash run_smoke.sh bristol         # just one
    python3 smoke.py --target test_control   # single target, in-process

Exit code 0 = all green; non-zero = at least one target failed.
"""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
from pathlib import Path

TARGETS = [
    "bristol",
    "agent_tools",
    "payload",
    "config_resolution",
    "test_control",
    "board_flows",
    "governing_docs",
    "skill_declarations",
    "bluesky_pruning",
    "bluesky_archive",
    "bluesky_purge",
    "bluesky_images",
    "published_files",
    "ticket_tier",
    "ticket_attachment",
    "notebook_access",
    "dashboard_access",
    "public_docs",
]


def _check(name: str):
    """The check function of one target, imported from its own module."""
    module = importlib.import_module(f"smoke_targets.check_{name}")
    return getattr(module, f"check_{name}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _run_one_inprocess(name: str) -> int:
    if name not in TARGETS:
        print(f"SMOKE FAIL: unknown target '{name}'")
        return 2
    try:
        for line in _check(name)():
            print(f"ok  [{name}] {line}")
    except Exception as exc:
        import traceback

        print(f"SMOKE FAIL [{name}]: {exc.__class__.__name__}: {exc}")
        traceback.print_exc()
        return 1
    return 0


def _orchestrate(names: list[str]) -> int:
    rc = 0
    for name in names:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--target", name],
            capture_output=True,
            text=True,
        )
        sys.stdout.write(proc.stdout)
        if proc.stderr.strip():
            sys.stderr.write(proc.stderr)
        # A target that dies outright — a crash in Qt rather than a failed
        # check — prints no line of its own, so the runner says which it was.
        if proc.returncode != 0 and "SMOKE FAIL" not in proc.stdout:
            print(
                f"SMOKE FAIL [{name}]: the process exited with code "
                f"{proc.returncode} and reported no failed check"
            )
        rc = rc or proc.returncode
    print("SMOKE OK" if rc == 0 else "SMOKE FAILED")
    return rc


def main() -> None:
    ap = argparse.ArgumentParser(description="Runtime-error smoke checks for the GUI tools.")
    ap.add_argument("targets", nargs="*", help="targets to check (default: all)")
    ap.add_argument(
        "--target", help="run exactly one target IN THIS process (used by the orchestrator)"
    )
    args = ap.parse_args()

    if args.target:
        # A target runs in a child process of its own and has printed its
        # results, so the child leaves without interpreter teardown and the Qt
        # objects it built are freed with the process.
        rc = _run_one_inprocess(args.target)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(rc)

    names = args.targets or list(TARGETS)
    unknown = [n for n in names if n not in TARGETS]
    if unknown:
        sys.exit(f"smoke: unknown target(s): {', '.join(unknown)}. Known: {', '.join(TARGETS)}")
    sys.exit(_orchestrate(names))


if __name__ == "__main__":
    main()
