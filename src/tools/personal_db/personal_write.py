#!/usr/bin/env python3
"""
personal_write.py — write CLI for personal.db.

Subcommands (applications domain only — books live in Zotero, see
src/tools/zotero/ and playbooks/librarian/add_book.md):

  add-application     --company C --role R [--status ... --fit-verdict ... --gaps ...
                      --location ... --ats ... --date-evaluated ... --cover-letter ...
                      --contact ... --referral ... --jd-link ... --year YYYY --fit-notes ...]
  update-application  --id N  [any of the same fields]
  find-company        --company C     # "have I applied here?" lookup for career_coach
  render              [--domain all|applications|books]

DB is SoT; mutating subcommands re-render the affected snapshot automatically
unless --no-render is passed. Write-safety via db_common (MEMORY journal).

Run: PERSONAL_DB_DIR=... python3 src/tools/personal_db/personal_write.py <subcommand> ...
"""

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_common as dbc  # noqa: E402

APP_FIELDS = [
    "company", "role", "fit_notes", "fit_verdict", "gaps", "location",
    "ats_platform", "date_evaluated", "cover_letter", "status", "contact",
    "referral", "jd_link", "year",
]
RENDER = Path(__file__).resolve().parent / "render_snapshot.py"


def _rerender(domain: str) -> None:
    r = subprocess.run([sys.executable, str(RENDER), "--domain", domain],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())


def _now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds")


def add_application(args) -> None:
    vals = {f: getattr(args, f) for f in APP_FIELDS if getattr(args, f) is not None}
    if not vals.get("company"):
        sys.exit("add-application: --company is required")
    vals["created_at"] = vals["updated_at"] = _now()
    cols = list(vals)
    conn = dbc.connect()
    cur = conn.execute(
        f"INSERT INTO applications ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
        [vals[c] for c in cols])
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    print(f"✓ inserted application id={rid}: {vals.get('company')} — {vals.get('role','')}")
    if not args.no_render:
        _rerender("applications")


def update_application(args) -> None:
    sets = {f: getattr(args, f) for f in APP_FIELDS if getattr(args, f) is not None}
    if not sets:
        sys.exit("update-application: nothing to update")
    sets["updated_at"] = _now()
    conn = dbc.connect()
    conn.execute(
        f"UPDATE applications SET {','.join(f'{c}=?' for c in sets)} WHERE id=?",
        [*sets.values(), args.id])
    conn.commit()
    changed = conn.total_changes
    conn.close()
    print(f"✓ updated application id={args.id} ({changed} row change)" if changed
          else f"⚠ no application with id={args.id}")
    if changed and not args.no_render:
        _rerender("applications")


def find_company(args) -> None:
    conn = dbc.connect()
    rows = conn.execute(
        "SELECT id, company, role, status, fit_verdict, date_evaluated, year "
        "FROM applications WHERE LOWER(company) LIKE LOWER(?) ORDER BY year DESC",
        (f"%{args.company}%",)).fetchall()
    conn.close()
    if not rows:
        print(f"No prior application matching '{args.company}'.")
        return
    print(f"{len(rows)} prior application(s) matching '{args.company}':")
    for r in rows:
        print(f"  #{r['id']} {r['company']} — {r['role']} "
              f"[{r['status']}, {r['fit_verdict']}, {r['date_evaluated'] or r['year']}]")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="personal.db write CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_app_args(sp):
        sp.add_argument("--company"); sp.add_argument("--role")
        sp.add_argument("--fit-notes", dest="fit_notes")
        sp.add_argument("--fit-verdict", dest="fit_verdict")
        sp.add_argument("--gaps"); sp.add_argument("--location")
        sp.add_argument("--ats", dest="ats_platform")
        sp.add_argument("--date-evaluated", dest="date_evaluated")
        sp.add_argument("--cover-letter", dest="cover_letter")
        sp.add_argument("--status"); sp.add_argument("--contact")
        sp.add_argument("--referral"); sp.add_argument("--jd-link", dest="jd_link")
        sp.add_argument("--year", type=int)
        sp.add_argument("--no-render", action="store_true")

    a = sub.add_parser("add-application"); add_app_args(a); a.set_defaults(func=add_application)
    u = sub.add_parser("update-application"); u.add_argument("--id", type=int, required=True)
    add_app_args(u); u.set_defaults(func=update_application)
    f = sub.add_parser("find-company"); f.add_argument("--company", required=True)
    f.set_defaults(func=find_company)
    r = sub.add_parser("render"); r.add_argument("--domain", default="all")
    r.set_defaults(func=lambda args: _rerender(args.domain))
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
