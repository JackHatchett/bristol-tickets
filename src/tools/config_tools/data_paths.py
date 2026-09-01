#!/usr/bin/env python3
"""data_paths.py — resolve a declared data location, and create it on write.

A fresh clone ships `/src` and `/config` and no `/data`. Every location an
agent needs — its `key_data_paths`, the folder its snapshots land in, the
database it keeps its own records in — is therefore *declared* long before it
exists. This module is the one place that turns a declaration into a real
path, and the one place that decides whether the absence of that path is an
error (it is not) or a thing to create (it is, at the moment of a write).

The contract, in one line each:

    resolve(declared)   an absolute path; touches nothing on disk
    ensure_dir(declared)  the same path, created if absent — call before a write
    read_dir(declared)  what is in it, or an empty list if it does not exist
    ensure_db(path, schema)  a database with its schema applied, created if absent

Creating a container is not the same as inventing content. `ensure_dir` makes
a directory and stops: no placeholder file, no sample record, no README
explaining the folder. `ensure_db` applies a schema and stops: no seed rows.

Path resolution
---------------
A declared path is one of three things:

    absolute, or starting with ~   used as written, with ~ expanded
    starting with the notebook's   resolved inside the Markdown notebook's
      own folder name              container (`markdown_notebook.notes_dir`)
    anything else                  relative to the project root

The third case is why `data/<instance>/career` in config resolves correctly
whatever the user named the folder they cloned into: the root is found by
walking up to the `src/app.md` marker, never by folder name.

The first case has a second step, for the same reason. A host may reach the
user's folders somewhere other than where config names them — a sandbox with the
chosen folders mounted into it reaches every one of them under a mount root, and
`~` there is the sandbox's own home rather than the user's. So an absolute
declared path that is not on disk is looked for once more *beside the project*,
which is where a host that relocates those folders puts them, and where they
already are on a machine running the system directly. Nothing here asks which
host it is: the project's own parent answers, whichever host that is.

CLI
---
    python3 data_paths.py --agent career_coach
    python3 data_paths.py --agent career_coach --ensure
    python3 data_paths.py --key important_paths.personal_db
    python3 data_paths.py --path data/<instance>/system/logs --ensure
    python3 data_paths.py --data-root
    python3 data_paths.py --instance

Import
------
    from data_paths import ensure_dir, read_dir, ensure_db
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instance_pointer  # noqa: E402  (runs as a script as well as a module)
import read_config  # noqa: E402

DEFAULT_INSTANCE = "default"


def project_root() -> Path:
    """The project root: the nearest ancestor holding src/app.md.

    Located by marker rather than by folder name, so the install works whatever
    the user named the folder they cloned into.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / "app.md").is_file():
            return parent
    raise SystemExit(
        "no project root above this file (no ancestor holds src/app.md)"
    )


def data_root() -> Path:
    """The tree all instance data lives under.

    Canonical resolution order (instance_pointer.py): the DATA_ROOT env
    override, then the per-machine instance pointer, then <project root>/data.
    """
    override = os.environ.get("DATA_ROOT")
    if override:
        return Path(os.path.expanduser(override))
    pointed = instance_pointer.get_path("data_root")
    if pointed:
        return pointed
    return project_root() / "data"


def instance_slug() -> str:
    """This installation's instance name — the `*` in data/*/tickets/.

    INSTANCE_SLUG env override, then the instance pointer, then the sole
    existing child of the data root, then DEFAULT_INSTANCE. The last step is
    what lets a clone with no data at all resolve a path instead of failing;
    the first-run setup writes a real slug into the pointer.
    """
    override = os.environ.get("INSTANCE_SLUG")
    if override and override.strip():
        return override.strip()
    pointed = instance_pointer.read().get("instance_slug")
    if isinstance(pointed, str) and pointed.strip():
        return pointed.strip()
    root = data_root()
    if root.is_dir():
        children = sorted(d for d in root.iterdir()
                          if d.is_dir() and not d.name.startswith("."))
        if len(children) == 1:
            return children[0].name
    return DEFAULT_INSTANCE


def notebook_root() -> Path | None:
    """The Markdown notebook's own folder, or None when config declares none."""
    declared = read_config.get("markdown_notebook.notes_dir", None)
    if not isinstance(declared, str) or not declared.strip():
        return None
    return Path(os.path.expanduser(declared.strip()))


def beside_the_project(expanded: Path) -> Path | None:
    """The same location, found beside the project, or None.

    A host may reach the user's folders somewhere other than where config names
    them. The folders the project sits among are those folders, because the
    project is one of them, so a declared path that is not on disk is rebuilt
    from the deepest of its own ancestors that names a folder there. The deepest
    match wins: it is the most specific of the user's folders the path names.
    """
    try:
        neighbourhood = project_root().parent
    except SystemExit:
        return None
    parts = expanded.parts
    for i in range(len(parts) - 1, 0, -1):
        candidate = neighbourhood / parts[i]
        if candidate.is_dir():
            found = candidate.joinpath(*parts[i + 1:])
            return found if found != expanded else None
    return None


def resolve(declared: str | Path) -> Path:
    """The absolute path a declaration refers to.

    Reads config. Touches the disk only for an absolute declared path that is
    not there, which is the one case a host can have relocated — see the module
    docstring's Path resolution.
    """
    text = str(declared).strip()
    if not text:
        raise ValueError("data_paths.resolve: empty path")
    expanded = Path(os.path.expanduser(text))
    if expanded.is_absolute():
        if expanded.exists():
            return expanded
        relocated = beside_the_project(expanded)
        return relocated if relocated is not None else expanded
    notebook = notebook_root()
    if notebook is not None:
        head, _, tail = text.partition("/")
        if head == notebook.name and tail:
            return notebook / tail
    return project_root() / text


def ensure_dir(declared: str | Path) -> Path:
    """The resolved directory, created with its parents if absent.

    Call this immediately before a write, never speculatively. It creates the
    directory and nothing else — an empty folder is the correct first state.
    """
    path = resolve(declared)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parent(declared: str | Path) -> Path:
    """The resolved path for a *file*, with its containing directory created."""
    path = resolve(declared)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_dir(declared: str | Path, pattern: str = "*") -> list[Path]:
    """Sorted matches inside a declared directory, or [] when it does not exist.

    The empty list is the honest answer for a first read: the agent has written
    nothing there yet. Reading creates nothing.
    """
    path = resolve(declared)
    if not path.is_dir():
        return []
    return sorted(path.glob(pattern))


def agent_data_paths(slug: str) -> list[Path]:
    """The resolved `key_data_paths` an agent declares in config."""
    declared = read_config.get(f"agents.{slug}.key_data_paths", [])
    if not isinstance(declared, list):
        return []
    return [resolve(p) for p in declared if isinstance(p, str) and p.strip()]


def ensure_agent_data_paths(slug: str) -> list[Path]:
    """Create every directory an agent declares, and return them."""
    declared = read_config.get(f"agents.{slug}.key_data_paths", [])
    if not isinstance(declared, list):
        return []
    return [ensure_dir(p) for p in declared if isinstance(p, str) and p.strip()]


def ensure_db(path: str | Path, schema: str | Path) -> Path:
    """A database at `path` with `schema` applied, created if either is absent.

    `schema` is SQL text, or a path to a .sql file. Every statement in a schema
    this repo ships is `IF NOT EXISTS`, so applying it to a database that
    already exists patches what is missing and leaves the rest untouched. No
    rows are written: provisioning gives an agent an empty store, not a
    pretend one.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    sql = schema
    if isinstance(schema, Path) or (isinstance(schema, str) and schema.endswith(".sql")):
        sql = Path(schema).read_text(encoding="utf-8")
    conn = sqlite3.connect(str(target), timeout=10)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        # // A mounted-folder bridge has wedged a database whose rollback
        # // journal was written to disk; MEMORY keeps the journal out of the
        # // mount. Same reasoning as personal_db.db_common.connect.
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
    return target


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    ensure = "--ensure" in argv

    def flag(name: str) -> str | None:
        if name not in argv:
            return None
        try:
            return argv[argv.index(name) + 1]
        except IndexError:
            raise SystemExit(f"data_paths: {name} needs a value")

    if "--data-root" in argv:
        print(data_root())
        return 0
    if "--instance" in argv:
        print(instance_slug())
        return 0

    slug = flag("--agent")
    if slug:
        paths = ensure_agent_data_paths(slug) if ensure else agent_data_paths(slug)
        for p in paths:
            print(p)
        return 0

    dotted = flag("--key")
    if dotted:
        try:
            declared = read_config.get(dotted)
        except KeyError:
            sys.stderr.write(f"data_paths: no such key path: {dotted}\n")
            return 1
        print(ensure_parent(declared) if ensure else resolve(declared))
        return 0

    declared = flag("--path")
    if declared:
        print(ensure_dir(declared) if ensure else resolve(declared))
        return 0

    sys.stderr.write(__doc__.split("CLI\n---\n", 1)[1].split("\nImport")[0])
    return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
