#!/usr/bin/env python3
"""install_schedule.py — put one daily program on the schedule the machine runs
by itself.

A job installed here is a program moving files: nothing starts a model and
nothing costs anything per run. The schedule is the operating system's own — a
launch agent on macOS, a cron line elsewhere — and this module holds the shape
of both so that two daily jobs are two sets of arguments rather than two scripts
that drift apart.

A caller supplies four things: the label the operating system knows the job by,
the program arguments to run, the file a run's own output goes to, and the time
of day. `describe` prints what would happen and writes nothing; `install` writes
it and loads it.
"""

from __future__ import annotations

import getpass
import os
import platform
import plistlib
import subprocess
from pathlib import Path


def agent_plist(label: str, program: list[str], log: Path, hour: int,
                minute: int, working_dir: Path) -> dict:
    """The launch agent, as macOS wants it.

    StartCalendarInterval runs the job at the next opportunity when the machine
    was asleep at the appointed time, which is what makes a missed day catch up
    without anyone asking.
    """
    return {
        "Label": label,
        "ProgramArguments": [str(part) for part in program],
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "WorkingDirectory": str(working_dir),
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
        "RunAtLoad": False,
    }


def cron_line(program: list[str], log: Path, hour: int, minute: int,
              working_dir: Path) -> str:
    joined = " ".join(str(part) for part in program)
    return f"{minute} {hour} * * * cd {working_dir} && {joined} >> {log} 2>&1"


def plist_target(label: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def install_macos(label: str, plist: dict, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        plistlib.dump(plist, handle)
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{label}"],
                   capture_output=True)
    result = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(target)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"launchctl refused the agent: {result.stderr.strip()}")
    print(f"installed {target}")
    print(f"run it now with: launchctl kickstart -p gui/{uid}/{label}")


def schedule(label: str, program: list[str], log: Path, hour: int, minute: int,
             working_dir: Path, install: bool = False,
             installer: Path | None = None) -> None:
    """Install the job, or print what installing it would do.

    `installer` is the script a reader would run to do it for real, named in the
    printed output so the line to type is in front of whoever read the preview.
    """
    log.parent.mkdir(parents=True, exist_ok=True)
    if platform.system() == "Darwin":
        target = plist_target(label)
        plist = agent_plist(label, program, log, hour, minute, working_dir)
        if install:
            install_macos(label, plist, target)
        else:
            print(f"would write {target}:\n")
            print(plistlib.dumps(plist).decode("utf-8"))
            if installer is not None:
                print(f"run this to install it:\n  python3 {installer} --install\n")
    else:
        print("add this line to your crontab (crontab -e):\n")
        print("  " + cron_line(program, log, hour, minute, working_dir) + "\n")
    print(f"each run writes what it did to {log}")
    print(f"the user running the schedule is {getpass.getuser()}")
