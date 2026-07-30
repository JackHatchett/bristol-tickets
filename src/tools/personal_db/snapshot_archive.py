#!/usr/bin/env python3
"""
snapshot_archive.py — keep a dated series of a snapshot, under a retention policy.

WHY THIS EXISTS. `render_snapshot.py` writes one always-current view per domain
(`library.xlsx`), overwritten in place. That view answers "what does the library
look like now" and nothing else. A dated series answers a different question —
"what did it look like in March" — and the library has a decade of that history
worth keeping (the 2016 export, the migration off Google Sheets). Both are
wanted; they are not the same artefact and must not be confused:

    library.xlsx            the live view. Regenerable, disposable, never dated.
    archive/library_*.xlsx  the history. A retained series, pruned by policy.
    checkpoints/*.xlsx      pinned moments. Never pruned, never auto-created.

This is not a backup and does not compete with Time Machine. Time Machine
protects against loss; it keeps hourly copies for 24 hours, daily for a month,
weekly beyond that, then drops the oldest when the disk fills — so a snapshot
from 2019 is long gone. The archive here is a longitudinal record of the
collection itself, kept deliberately and indefinitely at decreasing resolution.

RETENTION — grandfather-father-son, the same shape restic/borg `forget` and
Time Machine both use: fine-grained recently, coarse further back.

    keep_daily    7    one per day for the last week
    keep_weekly   5    one per ISO week beyond that (~the rest of the month)
    keep_monthly 12    one per month beyond that (~the rest of the year)
    keep_yearly   0    one per year, forever (0 = unlimited)

A file satisfying any rule is kept; a file satisfying none is deleted. Buckets
are filled newest-first, so the newest snapshot in each day/week/month/year is
the one that survives.

Usage:
    python3 snapshot_archive.py --dir <snapshot dir> [--stem library]
                                [--archive <live.xlsx>] [--apply] [--json]

    Default is a dry run: it prints keep/delete and touches nothing. Pass
    --apply to delete. --archive FILE first copies FILE into archive/ under
    today's date (overwriting an earlier copy from today), then prunes.

    import snapshot_archive as sa
    sa.archive_and_prune(Path(".../library.xlsx"))
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

ARCHIVE_DIRNAME = "archive"
CHECKPOINT_DIRNAME = "checkpoints"
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


@dataclass(frozen=True)
class Retention:
    """0 means unlimited; a negative number is not meaningful."""
    daily: int = 7
    weekly: int = 5
    monthly: int = 12
    yearly: int = 0


DEFAULT_RETENTION = Retention()


def _file_date(path: Path) -> date:
    """The snapshot's own date: from its filename if it carries one, else the
    file's mtime. Filename wins — a file copied or restored keeps its meaning,
    its mtime does not."""
    m = DATE_RE.search(path.name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime).date()


def _buckets(d: date) -> dict[str, tuple]:
    iso = d.isocalendar()
    return {
        "daily": (d.year, d.month, d.day),
        "weekly": (iso[0], iso[1]),
        "monthly": (d.year, d.month),
        "yearly": (d.year,),
    }


def plan(paths: list[Path], retention: Retention = DEFAULT_RETENTION
         ) -> tuple[list[tuple[Path, str]], list[Path]]:
    """Split paths into (kept, deleted). Returns each kept file with the rule
    that saved it, so a dry run can explain itself.

    Newest first; a file is kept when it opens a bucket the policy still has
    room for. Identical to restic's `forget` semantics."""
    limits = {"daily": retention.daily, "weekly": retention.weekly,
              "monthly": retention.monthly, "yearly": retention.yearly}
    dated = sorted(((_file_date(p), p) for p in paths),
                   key=lambda t: (t[0], t[1].name), reverse=True)

    seen: dict[str, list] = {k: [] for k in limits}
    kept: list[tuple[Path, str]] = []
    dropped: list[Path] = []

    for d, path in dated:
        b = _buckets(d)
        reason = None
        for rule, limit in limits.items():
            if limit < 0:
                continue
            bucket = b[rule]
            if bucket in seen[rule]:
                continue
            if limit == 0 or len(seen[rule]) < limit:
                seen[rule].append(bucket)
                reason = reason or rule
        if reason:
            kept.append((path, reason))
        else:
            dropped.append(path)
    return kept, dropped


def archive_dir(snapshot_dir: Path) -> Path:
    return snapshot_dir / ARCHIVE_DIRNAME


def series(snapshot_dir: Path, stem: str) -> list[Path]:
    """The dated series for one stem. Only archive/ is ever considered —
    checkpoints/ and the live file are outside the policy by construction."""
    ad = archive_dir(snapshot_dir)
    if not ad.is_dir():
        return []
    return sorted(p for p in ad.glob(f"{stem}_*")
                  if p.is_file() and not p.name.startswith("."))


def archive(live: Path, on: date | None = None) -> Path:
    """Copy the live snapshot into archive/ under its date. One file per day:
    a second run the same day replaces the first, so running the renderer ten
    times in an afternoon leaves one snapshot, not ten."""
    on = on or date.today()
    dest_dir = archive_dir(live.parent)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{live.stem}_{on.isoformat()}{live.suffix}"
    shutil.copy2(str(live), str(dest))
    return dest


def archive_and_prune(live: Path, retention: Retention = DEFAULT_RETENTION,
                      apply: bool = True) -> tuple[Path, list[Path]]:
    """Add today's copy to the series, then enforce the policy. Returns the
    new archive file and the files removed."""
    dest = archive(live)
    _, dropped = plan(series(live.parent, live.stem), retention)
    if apply:
        for p in dropped:
            p.unlink()
    return dest, dropped


def main() -> None:
    args = sys.argv[1:]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    d = opt("--dir")
    live = opt("--archive")
    if not d and not live:
        sys.exit(__doc__)
    snapshot_dir = Path(d) if d else Path(live).parent
    stem = opt("--stem") or (Path(live).stem if live else None)
    if not stem:
        sys.exit("snapshot_archive: --stem is required with --dir")
    apply_now = "--apply" in args
    retention = Retention(
        daily=int(opt("--keep-daily", DEFAULT_RETENTION.daily)),
        weekly=int(opt("--keep-weekly", DEFAULT_RETENTION.weekly)),
        monthly=int(opt("--keep-monthly", DEFAULT_RETENTION.monthly)),
        yearly=int(opt("--keep-yearly", DEFAULT_RETENTION.yearly)),
    )

    if live:
        dest = archive(Path(live))
        print(f"[snapshot_archive] archived -> {dest}")

    files = series(snapshot_dir, stem)
    kept, dropped = plan(files, retention)

    if "--json" in args:
        print(json.dumps({
            "kept": [{"file": str(p), "rule": r} for p, r in kept],
            "delete": [str(p) for p in dropped],
            "applied": apply_now,
        }, indent=2))
    else:
        print(f"[snapshot_archive] {snapshot_dir}/{ARCHIVE_DIRNAME} — "
              f"{len(files)} file(s): keep {len(kept)}, delete {len(dropped)}")
        for p, r in kept:
            print(f"  keep   [{r:7s}] {p.name}")
        for p in dropped:
            print(f"  delete           {p.name}")
        if not apply_now and dropped:
            print("  (dry run — pass --apply to delete)")

    if apply_now:
        for p in dropped:
            p.unlink()


if __name__ == "__main__":
    main()
