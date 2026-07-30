#!/usr/bin/env python3
"""
rename_photos.py — Phase G, layer 1, step 2: descriptive, factual filenames.

Turns  2023/01-January/IMG_1229.HEIC
into   2023/01-January/2023-01-14_Brooklyn-NY_IMG_1229.heic

DESIGN (decisions locked with the user):
  • FACTS ONLY in the filename — date from EXIF, place from GPS. No AI scene
    guesses (those go in METADATA later via digiKam, layer 2, never the name).
  • Date-first (YYYY-MM-DD) so files sort chronologically inside each folder.
  • The ORIGINAL stem is kept (…_IMG_1229) for three reasons: traceability back
    to the source, a natural collision-breaker, and trivial reversibility.
  • Place only when the photo actually has GPS (~38% of the library); otherwise
    date + original stem. Offline reverse-geocode — no network, nothing leaves
    the Mac.
  • Live Photo siblings travel: a same-stem .MOV (motion) and .AAE (edit sidecar)
    are renamed to the SAME new stem so the pair never splits.
  • REVERSIBLE: the manifest is a source,destination map. To undo, feed it to
    safe_move.py with the columns swapped, or re-run logic in reverse.
  • IDEMPOTENT: files already matching the YYYY-MM date pattern are skipped, so
    the script is safe to re-run / --resume after an interruption.

DATE SOURCE (in priority order; recorded per-row in the manifest):
  exif  → EXIF DateTimeOriginal / DateTimeDigitized / DateTime  (full Y-M-D)
  folder→ the .../YYYY/MM-Month/ path when no EXIF date exists   (Y-M only, no day)

PREREQUISITES (run once on your Mac):
  pip3 install pillow pillow-heif reverse_geocoder

RUN ORDER:
  1) python3 agent_system/src/tools/file_management/rename_photos.py            # dry run
  2) open  agent_system/data/*/system/photo_tools/_rename_photos_manifest.csv # review
  3) python3 agent_system/src/tools/file_management/rename_photos.py --execute  # rename
  (Interrupted? add --resume.)   Run dedupe_photos.py FIRST.

SOURCE: resolved from config.local.json's `drives.external1` root + "Photos"
  (renames happen in place, same folder) — never hardcoded, matches the
  tools/maintenance/*.py convention.
"""

import os
import re
import sys
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime


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
MANIFEST_FILE = _resolve_data_path("system/photo_tools/_rename_photos_manifest.csv")
PROGRESS_FILE = _resolve_data_path("system/photo_tools/_rename_photos_progress.json")

PRIMARY_EXTS = {'.heic', '.heif', '.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.webp'}
SIBLING_EXTS = {'.mov', '.aae', '.mp4', '.m4v'}
ALREADY_RE   = re.compile(r'^\d{4}-\d{2}')          # already date-prefixed → skip

US_STATE_ABBR = {
    'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA',
    'Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA',
    'Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS',
    'Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA',
    'Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT',
    'Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM',
    'New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK',
    'Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC',
    'South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT',
    'Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY',
}

# Lazy imports so a missing optional dep degrades gracefully to date-only.
try:
    from PIL import Image
    import pillow_heif
    pillow_heif.register_heif_opener()
    _PIL = True
except Exception:
    _PIL = False

try:
    import reverse_geocoder as _rg
    _GEO = True
except Exception:
    _GEO = False


def slug(s: str) -> str:
    s = re.sub(r'[^\w\-]+', '-', s.strip())
    return re.sub(r'-{2,}', '-', s).strip('-')


def exif_date(img) -> str | None:
    """Return YYYY-MM-DD from EXIF, or None."""
    try:
        ex = img.getexif()
    except Exception:
        return None
    for tag in (36867, 36868, 306):          # Orig, Digitized, DateTime
        v = ex.get(tag)
        if v and isinstance(v, str) and len(v) >= 10:
            try:
                return datetime.strptime(v[:10], '%Y:%m:%d').strftime('%Y-%m-%d')
            except ValueError:
                continue
    return None


def gps_place(img) -> str | None:
    """City-ST (US) or City-CC from GPS, or None."""
    if not _GEO:
        return None
    try:
        ex = img.getexif()
        g = ex.get_ifd(0x8825)
        if not g:
            return None

        def dms(t):
            return float(t[0]) + float(t[1])/60 + float(t[2])/3600
        lat = dms(g[2]); lon = dms(g[4])
        if g.get(1) == 'S': lat = -lat
        if g.get(3) == 'W': lon = -lon
        if lat == 0 and lon == 0:
            return None
        r = _rg.search([(lat, lon)], mode=1)[0]
        name = slug(r['name'])
        if r['cc'] == 'US':
            st = US_STATE_ABBR.get(r['admin1'], slug(r['admin1']))
            return f"{name}-{st}"
        return f"{name}-{r['cc']}"
    except Exception:
        return None


def folder_ym(path: Path) -> str | None:
    """YYYY-MM from a .../YYYY/MM-Month/ path."""
    parts = path.parts
    for i, p in enumerate(parts):
        if re.fullmatch(r'\d{4}', p) and i + 1 < len(parts):
            m = re.match(r'(\d{2})', parts[i+1])
            if m:
                return f"{p}-{m.group(1)}"
    return None


def find_siblings(path: Path) -> list:
    sibs = []
    for f in path.parent.iterdir():
        if f != path and f.is_file() and f.stem == path.stem \
                and f.suffix.lower() in SIBLING_EXTS:
            sibs.append(f)
    return sibs


def unique(dest: Path, taken: set) -> Path:
    if not dest.exists() and dest not in taken:
        return dest
    i = 1
    while True:
        cand = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
        if not cand.exists() and cand not in taken:
            return cand
        i += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true', help='rename for real (default: dry-run)')
    ap.add_argument('--resume', action='store_true', help='skip files already done')
    ap.add_argument('--source', default=str(SOURCE))
    args = ap.parse_args()
    root = Path(args.source)
    dry = not args.execute

    if not root.exists():
        print(f"ERROR: source not found: {root}  (is the Seagate mounted?)")
        sys.exit(1)
    if not _PIL:
        print("WARNING: Pillow/pillow-heif not available — cannot read EXIF; "
              "would fall back to folder Y-M for everything. Install deps first.")

    done = set()
    if args.resume and PROGRESS_FILE.exists():
        done = set(json.loads(PROGRESS_FILE.read_text()).get('done', []))

    print(f"\n=== rename_photos ===")
    print(f"Mode:   {'DRY RUN' if dry else 'EXECUTE (rename in place)'}")
    print(f"Source: {root}   geocoder: {'on' if _GEO else 'OFF'}\n")

    taken: set = set()
    stats = {'renamed': 0, 'skipped_already': 0, 'no_date_exif': 0,
             'with_place': 0, 'siblings': 0, 'errors': 0}

    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    fh = open(MANIFEST_FILE, 'w', newline='')
    w = csv.writer(fh)
    w.writerow(['source', 'destination', 'date_source', 'place', 'is_sibling_of'])

    primaries = []
    for dirpath, _d, files in os.walk(root):
        for name in files:
            if name.startswith('.'):
                continue
            p = Path(dirpath) / name
            if p.suffix.lower() in PRIMARY_EXTS:
                primaries.append(p)
    primaries.sort()
    print(f"Primary images found: {len(primaries)}")

    for idx, p in enumerate(primaries, 1):
        if str(p) in done:
            continue
        if ALREADY_RE.match(p.stem):
            stats['skipped_already'] += 1
            continue

        date_str = None; place = None; date_source = 'exif'
        if _PIL:
            try:
                img = Image.open(p)
                date_str = exif_date(img)
                place = gps_place(img)
            except Exception:
                pass
        if not date_str:
            date_str = folder_ym(p)
            date_source = 'folder'
            stats['no_date_exif'] += 1
        if not date_str:
            stats['errors'] += 1
            continue

        parts = [date_str] + ([place] if place else []) + [slug(p.stem)]
        new_stem = '_'.join(parts)
        dest = unique(p.with_name(new_stem + p.suffix.lower()), taken)
        taken.add(dest)
        if place:
            stats['with_place'] += 1

        w.writerow([str(p), str(dest), date_source, place or '', ''])

        siblings = find_siblings(p)
        sib_targets = []
        for s in siblings:
            sdest = unique(s.with_name(new_stem + s.suffix.lower()), taken)
            taken.add(sdest)
            sib_targets.append((s, sdest))
            w.writerow([str(s), str(sdest), date_source, place or '', p.name])
            stats['siblings'] += 1

        if not dry:
            try:
                p.rename(dest)
                for s, sdest in sib_targets:
                    s.rename(sdest)
                done.add(str(p))
                stats['renamed'] += 1
            except OSError as e:
                print(f"  ✗ {p.name}: {e}")
                stats['errors'] += 1
        else:
            stats['renamed'] += 1

        if not dry and idx % 200 == 0:
            PROGRESS_FILE.write_text(json.dumps({'done': list(done)}))
            print(f"  …{idx}/{len(primaries)}")

    fh.close()
    if not dry:
        PROGRESS_FILE.write_text(json.dumps({'done': list(done)}))

    print(f"\n{'Would rename' if dry else 'Renamed'}: {stats['renamed']} primaries "
          f"(+{stats['siblings']} siblings)")
    print(f"  with a place tag:        {stats['with_place']}")
    print(f"  date from folder (no EXIF): {stats['no_date_exif']}")
    print(f"  already-named, skipped:  {stats['skipped_already']}")
    print(f"  errors:                  {stats['errors']}")
    print(f"Manifest: {MANIFEST_FILE}")
    if dry:
        print("\nDry-run only — nothing renamed. Review the manifest, then --execute.")


if __name__ == '__main__':
    main()
