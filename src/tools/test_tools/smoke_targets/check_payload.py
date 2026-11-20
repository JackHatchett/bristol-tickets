"""smoke_targets/check_payload.py — the `payload` smoke target, run by smoke.py."""

from __future__ import annotations

import tempfile
from pathlib import Path

from qt_headless import TOOLS, tool_on_path
from smoke_targets.failure import SmokeFailure


def check_payload() -> list[str]:
    """The tree a built .app carries: what it installs, what an update replaces,
    and what an abandoned setup takes back.

    No Qt and no bundle: `payload` is plain file copying, so the check builds a
    source tree, installs it, uses it, updates it and undoes it in a temp
    folder.
    """

    ok: list[str] = []
    tool_on_path("bristol")
    import payload

    if (
        any(name in payload.PUBLISHED_FILES for name in ("config/config.local.json", "data"))
        or "data" in payload.PUBLISHED_DIRS
    ):
        raise SmokeFailure(
            "a published name covers an installation's own files — a release "
            "would ship one user's board and an update would overwrite the next "
            "one's"
        )
    ok.append("no published name reaches config.local.json or data/")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "carried"
        (source / "src").mkdir(parents=True)
        (source / "config").mkdir()
        (source / "docs").mkdir()
        (source / "src" / "app.md").write_text("# app.md\n")
        (source / "src" / "VERSION").write_text("1.0.0\n")
        (source / "AGENTS.md").write_text("read src/app.md\n")
        (source / "config" / "config.example.json").write_text("{}\n")
        (source / "src" / "__pycache__").mkdir()
        (source / "src" / "__pycache__" / "x.pyc").write_bytes(b"junk")

        target = root / "Bristol"
        payload.stage(source, target)
        if not payload.installed_at(target) or payload.version(target) != "1.0.0":
            raise SmokeFailure("a staged tree is not a readable installation")
        if (target / "src" / "__pycache__").exists():
            raise SmokeFailure("staging carried a cache folder into the install")
        ok.append("install writes the published tree and no build leavings")

        (target / "data" / "someone" / "tickets").mkdir(parents=True)
        (target / "data" / "someone" / "tickets" / "tickets.db").write_bytes(b"BOARD")
        (target / "config" / "config.local.json").write_text('{"active_agent":"x"}')

        (source / "src" / "VERSION").write_text("1.1.0\n")
        (source / "src" / "app.md").write_text("# app.md — newer\n")
        payload.stage(source, target)
        if payload.version(target) != "1.1.0":
            raise SmokeFailure("an update did not raise the installed version")
        if "newer" not in (target / "src" / "app.md").read_text():
            raise SmokeFailure("an update did not replace the machinery")
        if (target / "data" / "someone" / "tickets" / "tickets.db").read_bytes() != b"BOARD":
            raise SmokeFailure("an update destroyed the board")
        if (target / "config" / "config.local.json").read_text() != '{"active_agent":"x"}':
            raise SmokeFailure("an update destroyed the configuration")
        ok.append("update replaces the machinery and leaves the board and config")

        fresh = root / "Fresh"
        payload.stage(source, fresh)
        payload.unstage(fresh)
        if fresh.exists():
            raise SmokeFailure("an abandoned setup left a folder behind")

        used = root / "Used"
        used.mkdir()
        (used / "theirs.txt").write_text("mine")
        payload.stage(source, used)
        payload.unstage(used)
        if not (used / "theirs.txt").exists() or (used / "src").exists():
            raise SmokeFailure(
                "undoing a placement either took the user's own file or left the tree"
            )
        ok.append("an abandoned setup undoes itself without touching what was there")

    # The folders and the board a run creates are undone on the same rule the
    # tree placement follows: only what this run put there, and never a folder
    # something else has written into.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        kept = root / "data" / "theirs"
        kept.mkdir(parents=True)
        (kept / "notes.txt").write_text("mine")
        created: list[Path] = []
        placed: list[Path] = []
        payload.make_dirs([root / "data" / "mine" / "tickets", kept], created)
        board = root / "data" / "mine" / "tickets" / "tickets.db"
        board.write_text("")
        placed.append(board)
        if kept in created:
            raise SmokeFailure("a folder that already existed was recorded as created")
        payload.unmake(created, placed)
        if (root / "data" / "mine").exists():
            raise SmokeFailure("undoing a run left the folders it created")
        if not (kept / "notes.txt").exists():
            raise SmokeFailure("undoing a run took a folder it did not create")
        ok.append("an abandoned run undoes the folders and board it created")

    # schema.sql ships beside the code in a source tree and one folder above
    # it in a build, and a board cannot be provisioned without it.
    with tempfile.TemporaryDirectory() as tmp:
        # Resolved, because schema_path resolves what it is given and the
        # comparison below is against a path this test built.
        root = Path(tmp).resolve()
        source_ui = root / "bristol" / "ui"
        source_ui.mkdir(parents=True)
        (root / "bristol" / "schema.sql").write_text("-- schema\n")
        found = payload.schema_path(source_ui / "setup_wizard.py")
        if found != root / "bristol" / "schema.sql":
            raise SmokeFailure("schema.sql is not found from a source tree")

        resources = root / "App.app" / "Contents" / "Resources"
        (resources / "lib" / "python3.13" / "ui").mkdir(parents=True)
        (resources / "schema.sql").write_text("-- schema\n")
        found = payload.schema_path(resources / "lib" / "python3.13" / "ui" / "setup_wizard.py")
        if found != resources / "schema.sql":
            raise SmokeFailure("schema.sql is not found inside a built bundle")

        bare = root / "bare" / "ui"
        bare.mkdir(parents=True)
        if payload.schema_path(bare / "setup_wizard.py") is not None:
            raise SmokeFailure("a missing schema.sql was reported as found")
    ok.append("schema.sql resolves from a source tree and from inside a bundle")

    # A bundle keeps only the Qt modules slim.py names, so a module imported
    # anywhere in the app and absent from that list ships an app that starts
    # and then cannot import it.
    import re as _re

    import slim

    imported = set()
    for source_file in (TOOLS / "bristol").rglob("*.py"):
        if any(part in ("dist", "build", ".eggs", "__pycache__") for part in source_file.parts):
            continue
        for match in _re.finditer(
            r"PySide6\.(Qt[A-Za-z]+)", source_file.read_text(encoding="utf-8")
        ):
            imported.add(match.group(1))
    missing = sorted(imported - set(slim.MODULES))
    if missing:
        raise SmokeFailure(
            f"the app imports {', '.join(missing)}, which a slimmed bundle "
            "does not carry — add them to slim.MODULES"
        )
    ok.append(f"a slimmed bundle carries every Qt module the app imports ({len(imported)})")

    return ok
