#!/usr/bin/env python3
"""
analyze_folder.py — read-only inventory + health report for any folder tree.

Built for the document-audit and reorganization phases. It touches NOTHING; it
only reads metadata and (optionally) hashes files to find duplicates. Run it on
a cloud-sync folder, local ~/Documents, or an external drive to answer "what's
actually here and what's wrong with it" before proposing any moves.

WHAT IT REPORTS:
  • Total files / total size / breakdown by extension
  • Empty folders (and near-empty: only .DS_Store / Icon\r)
  • Duplicate files (byte-identical, grouped by MD5)  [--hash]
  • Badly-named files worth renaming (IMG_####, DSC_####, "Untitled", "document(1)",
    screenshots, scanner output, generic "New …", all-caps junk, etc.)
  • Largest files (top 25)

USAGE:
  python3 analyze_folder.py ~/Documents/Records
  python3 analyze_folder.py <path> --hash          # also do duplicate detection
  python3 analyze_folder.py <path> --json out.json # machine-readable report too

Nothing is moved, renamed, or deleted. Safe to run anywhere, anytime.
"""

import os
import sys
import json
import hashlib
import argparse
import re
from collections import defaultdict
from pathlib import Path

IGNORE_NAMES = {'.DS_Store', 'Icon\r', 'Thumbs.db', '.localized'}

# Heuristics for "this filename carries no human meaning"
BAD_NAME_PATTERNS = [
    re.compile(r'^IMG[_-]?\d+', re.I),
    re.compile(r'^DSC[_-]?\d+', re.I),
    re.compile(r'^DCIM', re.I),
    re.compile(r'^(Photo|Video|Image|Screenshot|Screen Shot)', re.I),
    re.compile(r'^(Untitled|Document|New |Scan|scanned|Copy of|copy)', re.I),
    re.compile(r'.*\(\d+\)\.', re.I),          # "report (1).pdf"
    re.compile(r'^[0-9a-f]{16,}', re.I),       # hex blobs
    re.compile(r'^\d{8,}$'),                   # bare long number stems
]


def human(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def is_bad_name(name: str) -> bool:
    stem = Path(name).stem
    return any(p.match(stem) or p.match(name) for p in BAD_NAME_PATTERNS)


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def analyze(root: Path, do_hash: bool):
    files = []
    empty_dirs, near_empty_dirs = [], []
    by_ext = defaultdict(lambda: {'count': 0, 'size': 0})
    bad_names = []
    skipped = []

    def onerror(err):
        skipped.append(str(err.filename))

    for dirpath, dirnames, filenames in os.walk(root, onerror=onerror):
        dp = Path(dirpath)
        real = [f for f in filenames if f not in IGNORE_NAMES]
        if not real and not dirnames:
            empty_dirs.append(dp)
        elif not real and dirnames:
            pass  # container folder, fine
        elif not real:
            near_empty_dirs.append(dp)

        for fname in real:
            p = dp / fname
            try:
                size = p.stat().st_size
            except OSError:
                continue
            files.append((p, size))
            ext = p.suffix.lower() or '(none)'
            by_ext[ext]['count'] += 1
            by_ext[ext]['size'] += size
            if is_bad_name(fname):
                bad_names.append(p)

    dupes = {}
    if do_hash:
        by_size = defaultdict(list)
        for p, size in files:
            if size > 0:
                by_size[size].append(p)
        for size, group in by_size.items():
            if len(group) < 2:
                continue
            by_hash = defaultdict(list)
            for p in group:
                try:
                    by_hash[md5(p)].append(p)
                except OSError:
                    pass
            for h, plist in by_hash.items():
                if len(plist) > 1:
                    dupes[h] = plist

    return {
        'files': files, 'by_ext': by_ext, 'empty_dirs': empty_dirs,
        'near_empty_dirs': near_empty_dirs, 'bad_names': bad_names,
        'dupes': dupes, 'skipped': skipped,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--hash', action='store_true', help='detect byte-identical duplicates')
    ap.add_argument('--json', metavar='FILE', help='also write a JSON report')
    args = ap.parse_args()

    root = Path(args.root).expanduser()
    if not root.exists():
        print(f"ERROR: {root} does not exist (is the drive mounted?)")
        sys.exit(1)

    r = analyze(root, args.hash)
    total_size = sum(s for _, s in r['files'])

    print(f"\n=== Inventory: {root} ===")
    print(f"Files: {len(r['files'])}   Total size: {human(total_size)}")

    print("\n-- By extension (top 15 by size) --")
    for ext, d in sorted(r['by_ext'].items(), key=lambda kv: -kv[1]['size'])[:15]:
        print(f"  {ext:8s} {d['count']:6d} files   {human(d['size'])}")

    print(f"\n-- Empty folders: {len(r['empty_dirs'])} --")
    for d in r['empty_dirs'][:40]:
        print(f"  {d}")
    if len(r['empty_dirs']) > 40:
        print(f"  …and {len(r['empty_dirs']) - 40} more")

    print(f"\n-- Folders with only junk files (.DS_Store etc.): {len(r['near_empty_dirs'])} --")
    for d in r['near_empty_dirs'][:20]:
        print(f"  {d}")

    print(f"\n-- Badly-named files worth renaming: {len(r['bad_names'])} --")
    for p in r['bad_names'][:30]:
        print(f"  {p.relative_to(root)}")
    if len(r['bad_names']) > 30:
        print(f"  …and {len(r['bad_names']) - 30} more")

    if args.hash:
        dupe_files = sum(len(v) - 1 for v in r['dupes'].values())
        wasted = sum(p.stat().st_size * (len(v) - 1) for v in r['dupes'].values() for p in [v[0]])
        print(f"\n-- Duplicate groups: {len(r['dupes'])}  ({dupe_files} redundant copies, ~{human(wasted)}) --")
        for h, plist in list(r['dupes'].items())[:15]:
            print(f"  [{h[:8]}] x{len(plist)}:")
            for p in plist:
                print(f"      {p.relative_to(root)}")

    print("\n-- Largest files --")
    for p, s in sorted(r['files'], key=lambda x: -x[1])[:25]:
        print(f"  {human(s):>9s}  {p.relative_to(root)}")

    if r['skipped']:
        print(f"\n(permission-denied on {len(r['skipped'])} paths)")

    if args.json:
        out = {
            'root': str(root), 'total_files': len(r['files']), 'total_size': total_size,
            'by_ext': {k: v for k, v in r['by_ext'].items()},
            'empty_dirs': [str(d) for d in r['empty_dirs']],
            'near_empty_dirs': [str(d) for d in r['near_empty_dirs']],
            'bad_names': [str(p) for p in r['bad_names']],
            'dupes': {h: [str(p) for p in v] for h, v in r['dupes'].items()},
        }
        Path(args.json).write_text(json.dumps(out, indent=2))
        print(f"\nJSON report → {args.json}")


if __name__ == '__main__':
    main()
