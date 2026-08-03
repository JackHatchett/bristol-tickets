#!/usr/bin/env python3
"""
safe_move.py — the project's reusable copy→verify→delete mover.

This is the move engine the whole project trusts, factored out so any future
session can drive a batch of moves from a manifest without re-implementing the
safety logic. It is the same discipline used in Phases 2/3:

  for each file:  copy to destination  →  MD5-verify both sides match  →
                  only THEN delete the source.

If verification fails, the source is left untouched and the row is reported as
an error. Interrupted runs are resumable (a progress file records completed
sources). Honours the charter's BATCH+VERIFY and DRY-RUN-FIRST gates.

INPUT: a CSV manifest with at least two columns: source,destination
  (extra columns are ignored — so analyze_folder.py / hand-built manifests work).

USAGE:
  python3 safe_move.py moves.csv                 # DRY RUN: validate only, move nothing
  python3 safe_move.py moves.csv --execute       # copy→verify→delete for real
  python3 safe_move.py moves.csv --execute --resume
  python3 safe_move.py moves.csv --execute --copy-only   # copy+verify, keep source

NOTES:
  • Never overwrites: if a destination exists, it appends _1, _2, …
  • --copy-only is for building backups (e.g. pushing photos to a cloud folder) where
    the source must stay put.
  • Large files are verified by full MD5 by default; pass --sample for a
    size + head/tail check instead (faster for multi-GB media you re-download).
"""

import os
import sys
import csv
import json
import hashlib
import argparse
import shutil
from pathlib import Path


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


PROGRESS_DEFAULT = _resolve_data_path("system/photo_tools/_safe_move_progress.json")


def md5(path: Path, sample: bool = False) -> str:
    h = hashlib.md5()
    size = path.stat().st_size
    with open(path, 'rb') as f:
        if sample and size > (8 << 20):           # >8MB: hash head+tail+size
            h.update(f.read(1 << 20))
            f.seek(-(1 << 20), os.SEEK_END)
            h.update(f.read(1 << 20))
            h.update(str(size).encode())
        else:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
    return h.hexdigest()


def unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, ext, parent = dest.stem, dest.suffix, dest.parent
    i = 1
    while True:
        cand = parent / f"{stem}_{i}{ext}"
        if not cand.exists():
            return cand
        i += 1


def load_rows(manifest: Path):
    rows = []
    with open(manifest, newline='') as f:
        reader = csv.DictReader(f)
        cols = {c.lower(): c for c in (reader.fieldnames or [])}
        src_col = cols.get('source') or cols.get('src') or cols.get('from')
        dst_col = (cols.get('destination') or cols.get('dest')
                   or cols.get('proposed_destination') or cols.get('to'))
        if not src_col or not dst_col:
            print(f"ERROR: manifest needs source & destination columns. Found: {reader.fieldnames}")
            sys.exit(1)
        for row in reader:
            s, d = row.get(src_col, '').strip(), row.get(dst_col, '').strip()
            if s and d and s != d:
                rows.append((Path(s), Path(d)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest')
    ap.add_argument('--execute', action='store_true', help='actually move (default: dry-run)')
    ap.add_argument('--resume', action='store_true', help='skip already-completed sources')
    ap.add_argument('--copy-only', action='store_true', help='copy+verify but keep source')
    ap.add_argument('--sample', action='store_true', help='sample-verify big files (size+head+tail)')
    ap.add_argument('--progress', default=str(PROGRESS_DEFAULT))
    args = ap.parse_args()

    dry = not args.execute
    prog_path = Path(args.progress).expanduser()
    done = set()
    if args.resume and prog_path.exists():
        done = set(json.loads(prog_path.read_text()).get('done', []))

    rows = load_rows(Path(args.manifest).expanduser())
    pending = [(s, d) for s, d in rows if str(s) not in done]

    print(f"\n=== safe_move ===")
    print(f"Mode:    {'DRY RUN' if dry else ('COPY-ONLY' if args.copy_only else 'MOVE (copy→verify→delete)')}")
    print(f"Rows:    {len(rows)}   pending: {len(pending)}\n")

    ok = err = skipped = 0
    for i, (src, dst) in enumerate(pending, 1):
        if not src.exists():
            print(f"[{i}] MISSING SOURCE: {src}")
            err += 1
            continue
        dst = unique_dest(dst)
        print(f"[{i}/{len(pending)}] {src.name}  →  {dst}")

        if dry:
            ok += 1
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            if md5(src, args.sample) != md5(dst, args.sample):
                print(f"     ✗ VERIFY FAILED — leaving source in place")
                dst.unlink(missing_ok=True)
                err += 1
                continue
            if not args.copy_only:
                src.unlink()
            ok += 1
            done.add(str(src))
        except Exception as e:
            print(f"     ✗ ERROR: {e}")
            err += 1
            continue

        if i % 25 == 0:
            prog_path.write_text(json.dumps({'done': list(done)}))

    prog_path.write_text(json.dumps({'done': list(done)}))
    print(f"\nDone. ok={ok} err={err} skipped={skipped}")
    if dry:
        print("Dry-run only — nothing moved. Re-run with --execute when the plan looks right.")


if __name__ == '__main__':
    main()
