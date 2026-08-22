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
import shutil
import subprocess
import sys
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
    return app


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
