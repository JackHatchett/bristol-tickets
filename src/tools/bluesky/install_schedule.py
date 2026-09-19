#!/usr/bin/env python3
"""Put the Bluesky sync on a daily schedule the machine runs by itself.

The schedule itself is `src/tools/_shared/install_schedule.py`, which every
daily job uses; this file is that installer called with the sync's own label,
command and log.

    python3 src/tools/bluesky/install_schedule.py            # show what it would do
    python3 src/tools/bluesky/install_schedule.py --install  # do it
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
SYNC = HERE.parent / "sync.py"
LABEL = "com.bristol.bluesky-sync"

DEFAULT_HOUR = 4
DEFAULT_MINUTE = 20
DEFAULT_WINDOW_DAYS = 7

sys.path.insert(0, str(ROOT / "src" / "tools" / "_shared"))
import install_schedule as scheduler  # noqa: E402


def log_path():
    """Where a run's own output goes, inside the git-ignored data tree."""
    sys.path.insert(0, str(ROOT / "src" / "tools"))
    from config_tools import data_paths  # noqa: E402

    reader = ROOT / "src" / "tools" / "config_tools" / "read_config.py"
    result = subprocess.run([sys.executable, str(reader), "important_paths.tickets_db"],
                            capture_output=True, text=True)
    declared = result.stdout.strip()
    instance = Path(declared).parts[1] if declared.startswith("data/") else "instance"
    folder = data_paths.ensure_dir(f"data/{instance}/bluesky")
    return folder / "sync.log"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true",
                        help="write and load the schedule rather than printing it")
    parser.add_argument("--hour", type=int, default=DEFAULT_HOUR)
    parser.add_argument("--minute", type=int, default=DEFAULT_MINUTE)
    parser.add_argument("--days", type=int, default=DEFAULT_WINDOW_DAYS,
                        help="how many days back each run covers, so a day "
                             "missed by an earlier failure is picked up")
    args = parser.parse_args()

    scheduler.schedule(
        label=LABEL,
        program=[sys.executable, str(SYNC), "--days", str(args.days)],
        log=log_path(),
        hour=args.hour,
        minute=args.minute,
        working_dir=ROOT,
        install=args.install,
        installer=HERE,
    )


if __name__ == "__main__":
    main()
