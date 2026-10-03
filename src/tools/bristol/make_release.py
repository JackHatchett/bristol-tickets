#!/usr/bin/env python3
"""make_release.py — build the downloadable Bristol Tickets, in one command.

    python3 src/tools/bristol/make_release.py

Runs the publication checks, builds the bundle with the project tree staged
inside it, and writes a zip beside it with its checksum. The last thing it
prints is the command that puts that zip on a GitHub release.

The zip is made with `ditto`, which preserves the bundle's symlinks and
resource forks. A plain `zip` produces an app macOS refuses to open.

The release is unsigned. `BUILD_APP.md` §Signing states what that costs a
downloader and what would change if it were signed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import payload  # noqa: E402  (bristol-local; owns what a release carries)

APP_NAME = "BristolTickets.app"
CHECK_TARGETS = ("published_files", "bristol")


def project_root() -> Path:
    for parent in HERE.parents:
        if (parent / "src" / "app.md").is_file():
            return parent
    raise SystemExit("make_release: no project root above this file")


def run(command: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(command)}")
    result = subprocess.run(command, cwd=str(cwd))
    if result.returncode != 0:
        raise SystemExit(f"make_release: {command[0]} failed")


def checks(root: Path) -> None:
    """The publication checks, which a release must not skip quietly.

    published_files is the one that matters here: it reads every tracked file
    for personal data, and a payload ships those files inside the bundle.
    """
    run(["bash", str(root / "src" / "tools" / "test_tools" / "run_smoke.sh"),
         *CHECK_TARGETS], root)


def build(root: Path) -> Path:
    for leaving in (HERE / "build", HERE / "dist"):
        if leaving.exists():
            shutil.rmtree(leaving)
    run([sys.executable, "setup.py", "py2app"], HERE)
    app = HERE / "dist" / APP_NAME
    if not app.is_dir():
        raise SystemExit(f"make_release: py2app wrote no {APP_NAME}")
    if not (app / "Contents" / "Resources" / payload.PAYLOAD_DIR_NAME
            / "src" / "app.md").is_file():
        raise SystemExit(
            "make_release: the bundle carries no payload, so a download would "
            "install nothing. Check payload.stage against setup.py."
        )
    verify_seal(app)
    return app


def verify_seal(app: Path) -> None:
    seal = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(app)],
        capture_output=True, text=True)
    if seal.returncode != 0:
        raise SystemExit(
            "make_release: the bundle's signature does not match its contents "
            f"({seal.stderr.strip()}). macOS reads that as damaged and moves "
            "the download to the trash rather than offering to open it. "
            "Anything that changes the bundle after py2app writes it has to "
            "sign it again — slim.reseal is what does that."
        )


# Run by the app's own interpreter, from the skills.py the app installs: what
# an import in the downloaded app does, minus the window.
SCAN_PROBE = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import skills
out = {}
for folder in sys.argv[2:]:
    record = skills.scan_record(Path(folder))
    out[Path(folder).name] = {"refusal": skills.refusal(record),
                              "scanners": record["scanners"],
                              "missing": record["missing"],
                              "unread": record["unread"]}
print(json.dumps(out))
"""

# Two skills the check imports: one whose code is ordinary, and one that hands
# its input to a shell, which both scanners report as high severity.
PROBE_SKILLS = {
    "clean": {"scripts/tally.py": "import json\nprint(json.dumps({'n': 1}))\n",
              "scripts/hello.sh": "#!/bin/sh\necho hello\n"},
    "risky": {"scripts/run.py": "import subprocess\nimport sys\n"
                                "subprocess.call(sys.argv[1], shell=True)\n"},
}


def check_scanners(app: Path) -> None:
    """Scan two skills with the bundle's own interpreter, in the environment
    the app gives a tool it starts. The clean one has to pass with both
    scanners run, and the risky one has to be refused: a bundle failing either
    would turn away every skill carrying code, or let a risky one in."""
    contents = app / "Contents"
    tools = (contents / "Resources" / payload.PAYLOAD_DIR_NAME / "src" / "tools"
             / "skill_tools")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    # The app's launcher sets PYTHONHOME for everything it starts, and keeps
    # bytecode out of the bundle, whose signature a written file would break.
    env.update(PYTHONHOME=str(contents / "Resources"),
               PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory() as tmp:
        folders = []
        for name, files in PROBE_SKILLS.items():
            for rel, text in files.items():
                path = Path(tmp) / name / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            (Path(tmp) / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: A probe.\n---\n",
                encoding="utf-8")
            folders.append(str(Path(tmp) / name))
        print("$ scan two probe skills with the bundle's interpreter")
        done = subprocess.run(
            [str(contents / "MacOS" / "python"), "-c", SCAN_PROBE, str(tools),
             *folders], capture_output=True, text=True, env=env, cwd=tmp)
    try:
        seen = json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        raise SystemExit(
            "make_release: the bundle's interpreter could not run the scan.\n"
            f"stdout:\n{done.stdout}\nstderr:\n{done.stderr}")
    clean, risky = seen["clean"], seen["risky"]
    problems = []
    if clean["refusal"] or clean["missing"] or clean["unread"]:
        problems.append(f"a clean skill was refused: {clean}")
    if sorted(clean["scanners"]) != ["bandit", "semgrep"]:
        problems.append(f"not both scanners ran: {clean}")
    if risky["refusal"] != "the scan found a risk":
        problems.append(f"a risky skill was not refused for its risk: {risky}")
    if problems:
        raise SystemExit("make_release: the bundle's scan is wrong.\n  "
                         + "\n  ".join(problems)
                         + f"\nstderr:\n{done.stderr}")
    print("  a clean skill imports, scanned by bandit and semgrep; "
          "a risky one is refused")


def package(app: Path, version: str) -> tuple[Path, str]:
    archive = app.parent / f"BristolTickets-{version}.zip"
    if archive.exists():
        archive.unlink()
    run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
         str(app), str(archive)], app.parent)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (archive.parent / f"{archive.name}.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )
    return archive, digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-checks", action="store_true",
                        help="build without running the publication checks")
    args = parser.parse_args()

    if sys.platform != "darwin":
        raise SystemExit("make_release: a macOS .app builds only on macOS")

    root = project_root()
    version = payload.version(root)
    if version is None:
        raise SystemExit("make_release: src/VERSION names no release")

    if not args.skip_checks:
        checks(root)
    app = build(root)
    check_scanners(app)
    verify_seal(app)
    archive, digest = package(app, version)

    print(f"\nBristol Tickets {version}")
    print(f"  {app}")
    print(f"  {archive}")
    print(f"  sha256 {digest}")
    print("\nPublish it:")
    print(f'  gh release create v{version} "{archive}" '
          f'"{archive}.sha256" --title "Bristol Tickets {version}"')
    print("\nThe release notes need the first-launch step: macOS refuses an "
          "unsigned app until it is allowed once in System Settings → Privacy "
          "& Security. docs/install.md carries the wording.")


if __name__ == "__main__":
    main()
