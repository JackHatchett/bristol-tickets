#!/usr/bin/env python3
"""Put the contacts due list on a daily schedule the machine runs by itself.

The schedule itself is `src/tools/_shared/install_schedule.py`, which every
daily job uses; this file is that installer called with the due list's own
label, command and log. A run writes the day's list into the notebook's capture
inbox and writes nothing when nothing is due.

    python3 src/tools/personal_db/install_due_schedule.py            # show what it would do
    python3 src/tools/personal_db/install_due_schedule.py --install  # do it
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
DUE = HERE.parent / "contacts_due.py"
LABEL = "com.bristol.contacts-due"

DEFAULT_HOUR = 7
DEFAULT_MINUTE = 30

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
    folder = data_paths.ensure_dir(f"data/{instance}/personal")
    return folder / "contacts_due.log"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true",
                        help="write and load the schedule rather than printing it")
    parser.add_argument("--hour", type=int, default=DEFAULT_HOUR)
    parser.add_argument("--minute", type=int, default=DEFAULT_MINUTE)
    args = parser.parse_args()

    scheduler.schedule(
        label=LABEL,
        program=[sys.executable, str(DUE), "--capture"],
        log=log_path(),
        hour=args.hour,
        minute=args.minute,
        working_dir=ROOT,
        install=args.install,
        installer=HERE,
    )


if __name__ == "__main__":
    main()
