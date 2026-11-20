"""smoke_targets/check_published_files.py — the `published_files` smoke target, run by smoke.py."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from qt_headless import PROJECT_ROOT
from smoke_targets.failure import SmokeFailure


def _tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split("\n")
    return [root / n for n in out if n.strip()]


# The one tracked file whose whole job is to name a person.
ATTRIBUTION_FILE = "LICENSE"


def check_published_files() -> list[str]:
    ok: list[str] = []
    root = PROJECT_ROOT

    def git_cfg(key: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), "config", key], capture_output=True, text=True
        ).stdout.strip()

    reader = root / "src" / "tools" / "config_tools" / "read_config.py"
    declared = subprocess.run(
        [sys.executable, str(reader), "--expanduser", "drives.local_home.path"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    home = Path(declared or "~").expanduser()
    needles = {
        s for s in (git_cfg("user.name"), git_cfg("user.email"), str(home), home.name) if len(s) > 2
    }
    # A name this installation's own content is built from — a world's proper
    # nouns, a client, a course — is as private as the user's own name, and the
    # published tree describes the shape of the work rather than the work.
    # config names them because only this installation knows them.
    private = subprocess.run(
        [sys.executable, str(reader), "published_tree.private_names"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if private.startswith("["):
        needles |= {str(name) for name in json.loads(private) if len(str(name)) > 2}
    # A repository's own address is a published fact, and it names the account
    # that hosts it. Clone lines are masked before the scan for that reason, and
    # so is the address of any other repository on that same account — an
    # add-on the app links to is published the same way.
    origin = git_cfg("remote.origin.url")
    published = {u for u in (origin, origin.removesuffix(".git")) if len(u) > 2}
    # Written with its scheme or without it, as a link's text usually is.
    account = origin.removesuffix(".git").rsplit("/", 1)[0] + "/"
    bare = re.sub(r"^[a-z]+://", "", account)
    sibling = (
        re.compile(r"(?:[a-z]+://)?" + re.escape(bare) + r"[A-Za-z0-9._-]+")
        if account.count("/") >= 3
        else None
    )

    hits: list[str] = []
    for path in _tracked_files(root):
        if path.name == ATTRIBUTION_FILE or not path.exists():
            continue
        try:
            text = path.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for url in published:
            text = text.replace(url, "")
        if sibling is not None:
            text = sibling.sub("", text)
        rel = path.relative_to(root)
        for needle in needles:
            if needle.lower() in text.lower():
                hits.append(f"{rel}: {needle}")
        for m in re.finditer(r"/Users/[A-Za-z0-9._-]+", text):
            hits.append(f"{rel}: {m.group(0)}")

    if hits:
        raise SmokeFailure(
            "tracked files carry this installation's identity, which belongs in "
            "the git-ignored /config:\n  " + "\n  ".join(sorted(set(hits))[:20])
        )
    ok.append(
        f"{len(needles)} identity strings and every absolute home path are absent "
        f"from tracked files outside {ATTRIBUTION_FILE} and the repository's own "
        f"clone address"
    )
    return ok
