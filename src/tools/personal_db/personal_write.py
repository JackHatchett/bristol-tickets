#!/usr/bin/env python3
"""
personal_write.py — write CLI for personal.db.

Subcommands for the applications and learning domains — books live in Zotero,
see src/tools/zotero/ and src/skills/add-book/SKILL.md:

  add-application     --company C --role R [--status ... --fit-verdict ... --gaps ...
                      --location ... --ats ... --date-evaluated ... --cover-letter ...
                      --contact ... --referral ... --jd-link ... --year YYYY --fit-notes ...]
  update-application  --id N  [any of the same fields]
  find-company        --company C     # "have I applied here?" lookup for career_coach
  record-progress     --course C --lesson N --kind opened|reading|quiz|exercise
                      [--item X --score S]
  clear-progress      --course C --lesson N --kind ... [--item X]
  find-place          [--course C]    # where to reopen a course, or every course
  render              [--domain all|applications|learning|books]

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


KINDS = ("opened", "reading", "quiz", "exercise")


def record(course: str, lesson: int, kind: str,
           item: str = "", score: str | None = None) -> None:
    """One thing the learner did. Doing it again updates that row."""
    if kind not in KINDS:
        raise ValueError("kind must be one of %s" % ", ".join(KINDS))
    conn = dbc.connect()
    conn.execute("""
        INSERT INTO learning_progress(course,lesson,kind,item,score,recorded_at)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(course,lesson,kind,item) DO UPDATE SET
          score=excluded.score,
          recorded_at=excluded.recorded_at
    """, (course, lesson, kind, item or "", score, _now()))
    conn.commit()
    conn.close()


def clear(course: str, lesson: int, kind: str, item: str = "") -> int:
    """Undo one recorded thing. Returns how many rows went."""
    conn = dbc.connect()
    cur = conn.execute(
        "DELETE FROM learning_progress WHERE course=? AND lesson=? AND kind=? AND item=?",
        (course, lesson, kind, item or ""))
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n


def marks(course: str, lesson: int) -> list[dict]:
    """Every row recorded against one lesson: kind, item and score."""
    conn = dbc.connect()
    rows = conn.execute(
        "SELECT kind, item, score, recorded_at FROM learning_progress "
        "WHERE course=? AND lesson=? ORDER BY kind, item", (course, lesson)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def place(course: str | None = None) -> list[dict]:
    """The lesson each course was last opened at, newest first."""
    conn = dbc.connect()
    if course:
        rows = conn.execute(
            "SELECT course, lesson, recorded_at FROM v_learning_place WHERE course=?",
            (course,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT course, lesson, recorded_at FROM v_learning_place "
            "ORDER BY recorded_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_progress(args) -> None:
    try:
        record(args.course, args.lesson, args.kind, args.item, args.score)
    except ValueError as exc:
        sys.exit("record-progress: %s" % exc)
    what = "%s lesson %s %s" % (args.course, args.lesson, args.kind)
    print("\u2713 recorded %s%s" % (what, (" (%s)" % args.item) if args.item else ""))
    if not args.no_render:
        _rerender("learning")


def clear_progress(args) -> None:
    n = clear(args.course, args.lesson, args.kind, args.item)
    what = "%s lesson %s %s" % (args.course, args.lesson, args.kind)
    print("\u2713 cleared %s%s" % (what, (" (%s)" % args.item) if args.item else "")
          if n else "nothing recorded for %s" % what)
    if n and not args.no_render:
        _rerender("learning")


def find_place(args) -> None:
    rows = place(args.course)
    if not rows:
        print("No course has been opened yet." if not args.course
              else "%s has not been opened yet." % args.course)
        return
    for r in rows:
        print("  %s \u2014 lesson %s (opened %s)" % (r["course"], r["lesson"], r["recorded_at"]))


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

    g = sub.add_parser("record-progress")
    g.add_argument("--course", required=True)
    g.add_argument("--lesson", type=int, required=True)
    g.add_argument("--kind", required=True, choices=KINDS)
    g.add_argument("--item", default="")
    g.add_argument("--score")
    g.add_argument("--no-render", action="store_true")
    g.set_defaults(func=record_progress)

    c = sub.add_parser("clear-progress")
    c.add_argument("--course", required=True)
    c.add_argument("--lesson", type=int, required=True)
    c.add_argument("--kind", required=True, choices=KINDS)
    c.add_argument("--item", default="")
    c.add_argument("--no-render", action="store_true")
    c.set_defaults(func=clear_progress)

    w = sub.add_parser("find-place"); w.add_argument("--course")
    w.set_defaults(func=find_place)

    r = sub.add_parser("render"); r.add_argument("--domain", default="all")
    r.set_defaults(func=lambda args: _rerender(args.domain))
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
