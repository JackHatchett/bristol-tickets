# File Management

Inspection and movement of files on disk. Every root comes from
`config/config.local.json` or an argument; none is built by hand.

## Tools

### analyze_folder.py

`python3 analyze_folder.py <root> [--hash] [--json FILE]` — read-only inventory
of a folder tree: file count and total size, breakdown by extension, empty and
near-empty directories, filenames carrying no human meaning, and the 25 largest
files. `--hash` adds byte-identical duplicate detection; `--json` also writes the
report as JSON. Moves, renames and deletes nothing.

### keyword_scan.py

`python3 keyword_scan.py` — walks `src/` for the keywords in the `keyword_scan`
block of config and writes every match to
`data/<instance>/system/logs/keyword_scan_results/keyword_scan_results.csv` as
`file_path`, `line_number`, `matched_text`. Takes no arguments. The block holds
`keywords`, `exclude_suffixes` and `exclude_prefixes`.

### dedupe_photos.py

`python3 dedupe_photos.py [--execute] [--source PATH]` — removes byte-identical
duplicates under the photo tree, resolved from `drives.external1` plus `Photos`.
Groups by file size, MD5s only the files sharing one, and deletes only on an
identical hash. Dry-run by default, writing
`data/<instance>/system/photo_tools/_dedupe_photos_manifest.csv`; `--execute`
deletes. The surviving copy of a group is the one without a macOS duplicate
suffix, then by extension priority `.heic` > `.jpg` > `.jpeg` > `.png`, then
shortest name.

### rename_photos.py

`python3 rename_photos.py [--execute] [--resume] [--source PATH]` — renames
photos in place to `YYYY-MM-DD_Place_ORIGINALSTEM.ext`, date from EXIF and place
from an offline reverse-geocode of the GPS tag. Without EXIF the date comes from
the enclosing `YYYY/MM-Month/` folder and carries no day; without GPS the place
is omitted. A same-stem `.MOV` or `.AAE` takes the same new stem, so a Live Photo
never splits. An already-dated filename is skipped, making the run idempotent.
Dry-run by default, writing `_rename_photos_manifest.csv` beside the dedupe
manifest; `--resume` reads `_rename_photos_progress.json`. Needs `pillow`,
`pillow-heif` and `reverse_geocoder`, and `dedupe_photos.py` run first.

### safe_move.py

`python3 safe_move.py <manifest.csv> [--execute] [--resume] [--copy-only]
[--sample] [--progress FILE]` — copy, MD5-verify, then delete the source, row by
row. The manifest needs `source` and `destination` columns; extra columns are
ignored, so an `analyze_folder.py` report or a hand-built CSV both work. Dry-run
by default. A failed verification leaves the source untouched and reports the
row. An existing destination is never overwritten — `_1`, `_2` are appended.
`--copy-only` keeps the source, for building a copy elsewhere. `--sample`
verifies large files by size plus head and tail instead of a full MD5.

## Conventions

- **Every destructive tool is dry-run by default**, writing a manifest to review
  before `--execute`.
- **A tool resolves its roots through config**, never a literal path.
- **A tool here inspects or moves; it never edits a file's contents.** Changing
  what is inside a file is `document_tools/`.
