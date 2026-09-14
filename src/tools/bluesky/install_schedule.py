#!/usr/bin/env python3
"""Put the Bluesky sync on a daily schedule the machine runs by itself.

The job is a program moving files, so nothing here starts a model and nothing
here costs anything per run. The schedule is the operating system's own: a
launch agent on macOS, a cron line elsewhere.

    python3 src/tools/bluesky/install_schedule.py            # show what it would do
    python3 src/tools/bluesky/install_schedule.py --install  # do it
"""

from __future__ import annotations

import argparse
import getpass
import platform
import plistlib
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


def agent_plist(hour, minute, window_days, log):
    """The launch agent, as macOS wants it.

    StartCalendarInterval runs the job at the next opportunity when the machine
    was asleep at the appointed time, which is what makes a missed day catch up
    without anyone asking.
    """
    return {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(SYNC), "--days", str(window_days)],
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "WorkingDirectory": str(ROOT),
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
        "RunAtLoad": False,
    }


def cron_line(hour, minute, window_days, log):
    return (f"{minute} {hour} * * * cd {ROOT} && {sys.executable} {SYNC} "
            f"--days {window_days} >> {log} 2>&1")


def install_macos(plist, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        plistlib.dump(plist, handle)
    subprocess.run(["launchctl", "bootout", f"gui/{os_uid()}/{LABEL}"],
                   capture_output=True)
    result = subprocess.run(["launchctl", "bootstrap", f"gui/{os_uid()}", str(target)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"launchctl refused the agent: {result.stderr.strip()}")
    print(f"installed {target}")
    print(f"run it now with: launchctl kickstart -p gui/{os_uid()}/{LABEL}")


def os_uid():
    import os
    return os.getuid()


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

    log = log_path()
    if platform.system() == "Darwin":
        target = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        plist = agent_plist(args.hour, args.minute, args.days, log)
        if args.install:
            install_macos(plist, target)
        else:
            print(f"would write {target}:\n")
            print(plistlib.dumps(plist).decode("utf-8"))
            print(f"run this to install it:\n  "
                  f"python3 {HERE} --install\n")
    else:
        line = cron_line(args.hour, args.minute, args.days, log)
        print("add this line to your crontab (crontab -e):\n")
        print("  " + line + "\n")
    print(f"each run writes what it did to {log}")
    print(f"the user running the schedule is {getpass.getuser()}")


if __name__ == "__main__":
    main()
