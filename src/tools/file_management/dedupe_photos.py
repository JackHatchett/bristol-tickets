#!/usr/bin/env python3
"""
dedupe_photos.py — Phase G, layer 1, step 1: remove byte-identical duplicates.

WHY THIS EXISTS:
  The Phase-4 photo sort produced byte-identical FORMAT duplicates — the same
  shot saved as both `IMG_7066.JPG` and `IMG_7066.jpeg`, plus macOS "copy"/" 1"
  variants. We dedupe BEFORE the descriptive rename (rename_photos.py) so we
  never bother renaming redundant copies. "Clean before pretty."

HOW IT'S SAFE:
  • Two-pass hashing: group by file SIZE first, only MD5 the files that share a
    size with another file. (Hashing all 72 GB blind would be needlessly slow.)
  • A group is only ever a duplicate set if the MD5s are *identical* — true
    byte-for-byte copies, never "looks similar".
  • Dry-run by default: writes a manifest, deletes NOTHING. You review it, then
    re-run with --execute.
  • NB: the only place .jpg vs .jpeg might be DIFFERENT images (not true dupes)
    is unrelated media libraries outside Photos/ (e.g. a scanned book/comic
    archive elsewhere). This script only ever touches Photos/, and only ever
    removes MD5-identical files, so that edge case cannot bite here.

KEEPER RULE (which copy of a dup group survives):
  1. Prefer a name WITHOUT a macOS duplicate suffix (" 1", " 2", " copy", "(1)").
  2. Prefer extension priority: .heic > .jpg > .jpeg > .png > others.
  3. Tie-break: shortest name, then lexicographically first.
  The keeper is always reported in the manifest so you can see what stayed.

PREREQUISITES: none beyond Python 3 (standard library only).

RUN ORDER:
  1) python3 src/tools/file_management/dedupe_photos.py            # dry run
  2) open  data/*/system/photo_tools/_dedupe_photos_manifest.csv # review
  3) python3 src/tools/file_management/dedupe_photos.py --execute  # delete dups

SOURCE: resolved from config.local.json's `drives.external1` root + "Photos"
  (all year subfolders; runs on your Mac) — never hardcoded.
"""

import os
import sys
import csv
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def _resolve_data_path(relative: str) -> Path:
    """Resolve a path under the instance data root without hardcoding the
    instance slug — mirrors the discovery pattern in
    tools/bristol/app.py (data/*/, first match wins, fresh-provisioning
    fallback to $AGENT_INSTANCE_SLUG)."""
    project_root = Path(__file__).resolve().parents[3]
    data_dir = project_root / "data"
    if data_dir.exists():
        matches = list(data_dir.glob("*/" + relative))
        if matches:
            return matches[0]
    instance_slug = os.environ.get("AGENT_INSTANCE_SLUG", "default_user")
    return data_dir / instance_slug / relative


def _resolve_external1_path(subfolder: str) -> Path:
    """Resolve a path under the configured primary backup drive
    (config.local.json's drives.external1) — mirrors tools/maintenance/*.py's
    config-driven resolution instead of hardcoding a real mount path."""
    project_root = Path(__file__).resolve().parents[3]
    config_path = project_root / "config" / "config.local.json"
    if not config_path.exists():
        raise SystemExit(f"ERROR: config.local.json not found at {config_path}")
    index = json.loads(config_path.read_text())
    if "external1" not in index.get("drives", {}):
        raise SystemExit(
            "ERROR: config.local.json has no 'external1' drive entry."
        )
    return Path(os.path.expanduser(index["drives"]["external1"]["path"])) / subfolder


# ── CONFIG ──────────────────────────────────────────────────────────────────
SOURCE        = _resolve_external1_path("Photos")
MANIFEST_FILE = _resolve_data_path("system/photo_tools/_dedupe_photos_manifest.csv")

# Files we consider for dedupe. (Exact dupes are exact dupes regardless of type,
# but we restrict to media so we never touch sidecars/system files by accident.)
MEDIA_EXTS = {'.heic', '.heif', '.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp',
              '.webp', '.mov', '.mp4', '.m4v'}
EXT_PRIORITY = {'.heic': 0, '.heif': 1, '.jpg': 2, '.jpeg': 3, '.png': 4}
DUP_SUFFIX_HINTS = (' copy', ' 1', ' 2', ' 3', '(1)', '(2)', '(3)')


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def keeper_score(p: Path):
    """Lower is better — the minimum in a group is kept."""
    stem = p.stem
    has_suffix = any(stem.endswith(s) or s in stem for s in DUP_SUFFIX_HINTS)
    ext_rank = EXT_PRIORITY.get(p.suffix.lower(), 9)
    return (1 if has_suffix else 0, ext_rank, len(p.name), str(p).lower())


def iter_media(root: Path):
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.startswith('.'):
                continue
            p = Path(dirpath) / name
            if p.suffix.lower() in MEDIA_EXTS:
                yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true',
                    help='actually delete the duplicate copies (default: dry-run)')
    ap.add_argument('--source', default=str(SOURCE))
    args = ap.parse_args()
    root = Path(args.source)
    dry = not args.execute

    if not root.exists():
        print(f"ERROR: source not found: {root}  (is the Seagate mounted?)")
        sys.exit(1)

    print(f"\n=== dedupe_photos ===")
    print(f"Mode:   {'DRY RUN' if dry else 'EXECUTE (delete dups)'}")
    print(f"Source: {root}\n")

    # Pass 1: bucket by size.
    by_size = defaultdict(list)
    n = 0
    for p in iter_media(root):
        try:
            by_size[p.stat().st_size].append(p)
        except OSError:
            continue
        n += 1
    print(f"Scanned {n} media files; {sum(1 for v in by_size.values() if len(v) > 1)} "
          f"size-collision groups to hash.")

    # Pass 2: hash only files that share a size; group by md5.
    groups = defaultdict(list)   # md5 -> [paths]
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        for p in paths:
            try:
                groups[(size, md5(p))].append(p)
            except OSError:
                continue

    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}

    removed = kept = 0
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_FILE, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['group', 'action', 'path', 'size_bytes', 'md5', 'timestamp'])
        for gid, ((size, digest), paths) in enumerate(sorted(dup_groups.items()), 1):
            paths_sorted = sorted(paths, key=keeper_score)
            keeper, dups = paths_sorted[0], paths_sorted[1:]
            ts = datetime.now().isoformat(timespec='seconds')
            w.writerow([gid, 'KEEP', keeper, size, digest, ts])
            kept += 1
            for d in dups:
                w.writerow([gid, 'REMOVE', d, size, digest, ts])
                removed += 1
                if not dry:
                    try:
                        d.unlink()
                    except OSError as e:
                        print(f"  ✗ could not delete {d}: {e}")

    freed = sum(size for (size, _), paths in dup_groups.items() for _ in paths[1:])
    print(f"\nDuplicate groups: {len(dup_groups)}")
    print(f"Files to {'remove' if dry else 'removed'}: {removed}  (keepers: {kept})")
    print(f"Space {'recoverable' if dry else 'freed'}: {freed/1e9:.2f} GB")
    print(f"Manifest: {MANIFEST_FILE}")
    if dry:
        print("\nDry-run only — nothing deleted. Review the manifest, then --execute.")


if __name__ == '__main__':
    main()
