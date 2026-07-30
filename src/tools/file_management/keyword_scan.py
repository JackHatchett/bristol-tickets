#!/usr/bin/env python3

import os
import csv
import json
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = RUNTIME_ROOT.parent / "config"

INDEX_PATH = CONFIG_DIR / "config.local.json"

if not INDEX_PATH.exists():
    raise SystemExit("ERROR: config.local.json not found")

INDEX = json.loads(INDEX_PATH.read_text())
# keyword-scan tuning is a sub-key of the single config file.
CONFIG = INDEX.get("keyword_scan", {})

SCAN_ROOT = Path(INDEX["agent_system_runtime"]["root"])
OUTPUT_DIR = Path(INDEX["agent_system_data"]["folders"]["keyword_scan_results"])

KEYWORDS = CONFIG.get("keywords", [])
EXCLUDE_SUFFIXES = CONFIG.get("exclude_suffixes", [])
EXCLUDE_PREFIXES = CONFIG.get("exclude_prefixes", [])

if not SCAN_ROOT.exists():
    raise SystemExit("ERROR: scan_root does not exist")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "keyword_scan_results.csv"

def excluded(rel):
    for suf in EXCLUDE_SUFFIXES:
        if rel.endswith(suf):
            return True
    for pre in EXCLUDE_PREFIXES:
        if rel.startswith(pre):
            return True
    return False

def scan_file(path):
    hits = []
    try:
        with open(path, "r", errors="ignore") as f:
            for lineno, line in enumerate(f, start=1):
                for kw in KEYWORDS:
                    if kw in line:
                        hits.append((lineno, line.strip()))
    except Exception:
        pass
    return hits

def main():
    rows = []
    for base, dirs, files in os.walk(SCAN_ROOT):
        for file in files:
            full = os.path.join(base, file)
            rel = os.path.relpath(full, SCAN_ROOT)
            if excluded(rel):
                continue
            results = scan_file(full)
            for lineno, text in results:
                rows.append([full, lineno, text])

    with open(OUTPUT_FILE, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["file_path", "line_number", "matched_text"])
        writer.writerows(rows)

    print("Done. Manifest written to " + str(OUTPUT_FILE))

if __name__ == "__main__":
    main()
