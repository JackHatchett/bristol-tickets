#!/usr/bin/env python3
"""
import_applications.py — load applications.csv into personal.db `applications`.

One-time, re-runnable (default: refuses to run if the table already has rows,
unless --replace). Prints a row-count parity report (CSV rows vs inserted).

Source CSV path resolution order:
  1. --csv <path>
  2. $APPLICATIONS_CSV
  3. $CAREER_COACH_DIR/applications.csv
  4. canonical: data/*/career/applications.csv (first match)

Run: PERSONAL_DB_DIR=... python3 src/tools/personal_db/import_applications.py [--replace] [--csv PATH]
"""

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_common as dbc  # noqa: E402

# CSV header -> applications column
COLMAP = {
    "Company": "company",
    "Role": "role",
    "Fit Notes": "fit_notes",
    "Fit Verdict": "fit_verdict",
    "Gaps": "gaps",
    "Location": "location",
    "ATS Platform": "ats_platform",
    "Date Evaluated": "date_evaluated",
    "Cover Letter": "cover_letter",
    "Status": "status",
    "Contact": "contact",
    "Referral": "referral",
    "JD Link": "jd_link",
    "Year": "year",
}


def resolve_csv() -> Path:
    for i, a in enumerate(sys.argv):
        if a == "--csv" and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])
    if os.environ.get("APPLICATIONS_CSV"):
        return Path(os.environ["APPLICATIONS_CSV"])
    if os.environ.get("CAREER_COACH_DIR"):
        return Path(os.environ["CAREER_COACH_DIR"]) / "applications.csv"
    matches = sorted(dbc._project_root().glob("data/*/career/applications.csv"))
    if matches:
        return matches[0]
    sys.exit("import_applications: ERROR — could not locate applications.csv")


def main() -> None:
    replace = "--replace" in sys.argv
    csv_path = resolve_csv()
    if not csv_path.exists():
        sys.exit(f"import_applications: ERROR — CSV not found at {csv_path}")

    with with_conn() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        if existing and not replace:
            sys.exit(f"applications already has {existing} rows. Re-run with --replace to rebuild.")
        if replace:
            conn.execute("DELETE FROM applications")

        rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
        inserted = 0
        for r in rows:
            vals = {}
            for header, col in COLMAP.items():
                v = (r.get(header) or "").strip()
                if col == "year":
                    vals[col] = int(v) if v.isdigit() else None
                else:
                    vals[col] = v if v != "" else None
            cols = list(vals.keys())
            conn.execute(
                f"INSERT INTO applications ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                [vals[c] for c in cols],
            )
            inserted += 1
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]

    print(f"[import_applications] source: {csv_path}")
    print(f"  CSV data rows : {len(rows)}")
    print(f"  inserted      : {inserted}")
    print(f"  table total   : {total}")
    print("  PARITY OK" if len(rows) == inserted == total else "  ⚠ PARITY MISMATCH")


# Small shim so we can swap in with_writeback if a mounted write ever fails.
def with_conn():
    class _Ctx:
        def __enter__(self):
            self.c = dbc.connect()
            return self.c
        def __exit__(self, *a):
            self.c.close()
            return False
    return _Ctx()


if __name__ == "__main__":
    main()
