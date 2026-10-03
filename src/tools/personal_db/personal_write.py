#!/usr/bin/env python3
"""
personal_write.py — write CLI for personal.db.

Subcommands for the applications and contacts domains — books live in Zotero,
see src/tools/zotero/ and src/skills/add-book/SKILL.md:

  add-application     --company C --role R [--status ... --fit-verdict ... --gaps ...
                      --location ... --ats ... --date-evaluated ... --cover-letter ...
                      --contact ... --referral ... --jd-link ... --year YYYY --fit-notes ...]
  update-application  --id N  [any of the same fields]
  find-company        --company C     # "have I applied here?" lookup for career_coach
  render              [--domain all|applications|contacts|books]

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


# ---------------------------------------------------------------------------
# contacts — the person, what is outstanding with them, and what they are
# attached to. Every write goes through db_common.connect(), as the
# applications writes above do.
# ---------------------------------------------------------------------------

CONTACT_FIELDS = ["name", "aliases", "how_known", "company", "title",
                  "cadence_days", "last_contact_on", "notes"]
ASK_KINDS = ("reconnect", "referral", "application-submit", "recommendation",
             "intro", "favour-owed", "other")
ASK_STATUSES = ("open", "done", "dropped")
DIRECTIONS = ("us", "them")


def _contact_matches(conn, needle: str):
    """Every contact whose name or aliases hold this text.

    Aliases are matched as well as the name because the same person arrives
    spelled differently — a nickname, a maiden name, a middle initial — and a
    second row for one person is the failure this domain exists to avoid.
    """
    like = f"%{needle.lower()}%"
    return conn.execute(
        "SELECT id, name, aliases, company, title, cadence_days, last_contact_on "
        "FROM contact "
        "WHERE LOWER(name) LIKE ? OR LOWER(COALESCE(aliases,'')) LIKE ? "
        "ORDER BY LOWER(name)", (like, like)).fetchall()


def add_contact(args) -> None:
    vals = {f: getattr(args, f) for f in CONTACT_FIELDS
            if getattr(args, f, None) is not None}
    if not vals.get("name"):
        sys.exit("add-contact: --name is required")
    existing = _contact_matches(dbc.connect(), vals["name"])
    if existing and not args.anyway:
        print(f"⚠ {len(existing)} contact(s) already match '{vals['name']}':")
        for r in existing:
            print(f"  #{r['id']} {r['name']}"
                  f"{' (' + r['aliases'] + ')' if r['aliases'] else ''}")
        sys.exit("Pass --anyway if this is a different person.")
    vals["created_at"] = vals["updated_at"] = _now()
    cols = list(vals)
    conn = dbc.connect()
    cur = conn.execute(
        f"INSERT INTO contact ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
        [vals[c] for c in cols])
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    print(f"✓ inserted contact id={rid}: {vals['name']}")
    if not args.no_render:
        _rerender("contacts")


def update_contact(args) -> None:
    sets = {f: getattr(args, f) for f in CONTACT_FIELDS
            if getattr(args, f, None) is not None}
    if not sets:
        sys.exit("update-contact: nothing to update")
    sets["updated_at"] = _now()
    conn = dbc.connect()
    conn.execute(f"UPDATE contact SET {','.join(f'{c}=?' for c in sets)} WHERE id=?",
                 [*sets.values(), args.id])
    conn.commit()
    changed = conn.total_changes
    conn.close()
    print(f"✓ updated contact id={args.id} ({changed} row change)" if changed
          else f"⚠ no contact with id={args.id}")
    if changed and not args.no_render:
        _rerender("contacts")


def add_ask(args) -> None:
    conn = dbc.connect()
    if conn.execute("SELECT 1 FROM contact WHERE id=?", (args.contact,)).fetchone() is None:
        conn.close()
        sys.exit(f"add-ask: no contact with id={args.contact}")
    cur = conn.execute(
        "INSERT INTO contact_ask (contact_id, kind, direction, subject, "
        "opened_on, due_on, status, last_touch) "
        "VALUES (?,?,?,?,COALESCE(?, date('now')),?, 'open', COALESCE(?, date('now')))",
        (args.contact, args.kind, args.direction, args.subject,
         args.opened_on, args.due_on, args.opened_on))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    print(f"✓ opened ask id={rid} on contact #{args.contact}: "
          f"{args.kind} — {args.subject or ''}")
    if not args.no_render:
        _rerender("contacts")


def close_ask(args) -> None:
    """Close an ask, and record the exchange on the contact it belongs to.

    Closing one is the commonest moment the two were last in touch, so the
    contact's last_contact_on follows it unless the caller says otherwise; a
    cadence measured from a date nobody updates would come due for ever.
    """
    conn = dbc.connect()
    row = conn.execute("SELECT contact_id FROM contact_ask WHERE id=?",
                       (args.id,)).fetchone()
    if row is None:
        conn.close()
        sys.exit(f"close-ask: no ask with id={args.id}")
    when = args.on or datetime.date.today().isoformat()
    conn.execute("UPDATE contact_ask SET status=?, last_touch=? WHERE id=?",
                 (args.status, when, args.id))
    if not args.keep_last_contact:
        conn.execute(
            "UPDATE contact SET last_contact_on=?, updated_at=? WHERE id=?",
            (when, _now(), row["contact_id"]))
    conn.commit()
    conn.close()
    print(f"✓ ask id={args.id} is {args.status} as of {when}")
    if not args.no_render:
        _rerender("contacts")


def add_link(args) -> None:
    conn = dbc.connect()
    if conn.execute("SELECT 1 FROM contact WHERE id=?", (args.contact,)).fetchone() is None:
        conn.close()
        sys.exit(f"add-link: no contact with id={args.contact}")
    if args.target_id is None and not args.target_path:
        conn.close()
        sys.exit("add-link: pass --target-id or --target-path")
    cur = conn.execute(
        "INSERT INTO contact_link (contact_id, target_kind, target_id, "
        "target_path, label) VALUES (?,?,?,?,?)",
        (args.contact, args.kind, args.target_id, args.target_path, args.label))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    print(f"✓ linked contact #{args.contact} to {args.kind} "
          f"{args.target_id if args.target_id is not None else args.target_path} "
          f"(link id={rid})")


def find_contact(args) -> None:
    conn = dbc.connect()
    rows = _contact_matches(conn, args.name)
    if not rows:
        print(f"No contact matching '{args.name}'.")
        conn.close()
        return
    print(f"{len(rows)} contact(s) matching '{args.name}':")
    for r in rows:
        asks = conn.execute(
            "SELECT id, kind, direction, subject, due_on FROM contact_ask "
            "WHERE contact_id=? AND status='open' ORDER BY COALESCE(due_on,'9999')",
            (r["id"],)).fetchall()
        alias = f" (also {r['aliases']})" if r["aliases"] else ""
        seen = r["last_contact_on"] or "never"
        print(f"  #{r['id']} {r['name']}{alias} — "
              f"{r['company'] or 'no company recorded'}, last contact {seen}")
        for a in asks:
            waits = "waiting on them" if a["direction"] == "them" else "ours to move"
            due = f", due {a['due_on']}" if a["due_on"] else ""
            print(f"      ask #{a['id']} {a['kind']}: {a['subject'] or ''} "
                  f"[{waits}{due}]")
    conn.close()


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

    def add_contact_args(sp):
        sp.add_argument("--name"); sp.add_argument("--aliases",
                        help="other names this person answers to, comma separated")
        sp.add_argument("--how-known", dest="how_known")
        sp.add_argument("--company"); sp.add_argument("--title")
        sp.add_argument("--cadence-days", dest="cadence_days", type=int,
                        help="how often to be in touch; leave unset for no cadence")
        sp.add_argument("--last-contact-on", dest="last_contact_on",
                        help="YYYY-MM-DD of the last exchange either way")
        sp.add_argument("--notes")
        sp.add_argument("--no-render", action="store_true")

    ac = sub.add_parser("add-contact")
    add_contact_args(ac)
    ac.add_argument("--anyway", action="store_true",
                    help="add the row even though a contact of this name is "
                         "already recorded")
    ac.set_defaults(func=add_contact)

    uc = sub.add_parser("update-contact"); uc.add_argument("--id", type=int, required=True)
    add_contact_args(uc); uc.set_defaults(func=update_contact)

    aa = sub.add_parser("add-ask")
    aa.add_argument("--contact", type=int, required=True)
    aa.add_argument("--kind", required=True, choices=ASK_KINDS)
    aa.add_argument("--direction", default="them", choices=DIRECTIONS,
                    help="who the next move waits on")
    aa.add_argument("--subject", help="what the ask is about, in one line")
    aa.add_argument("--opened-on", dest="opened_on", help="YYYY-MM-DD; default today")
    aa.add_argument("--due-on", dest="due_on",
                    help="YYYY-MM-DD this becomes late; optional")
    aa.add_argument("--no-render", action="store_true")
    aa.set_defaults(func=add_ask)

    ca = sub.add_parser("close-ask"); ca.add_argument("--id", type=int, required=True)
    ca.add_argument("--status", default="done", choices=("done", "dropped"))
    ca.add_argument("--on", help="YYYY-MM-DD it closed; default today")
    ca.add_argument("--keep-last-contact", dest="keep_last_contact",
                    action="store_true",
                    help="leave the contact's last_contact_on where it is")
    ca.add_argument("--no-render", action="store_true")
    ca.set_defaults(func=close_ask)

    al = sub.add_parser("add-link"); al.add_argument("--contact", type=int, required=True)
    al.add_argument("--kind", required=True,
                    help="application | document | client | course | other")
    al.add_argument("--target-id", dest="target_id", type=int,
                    help="a row id in this database")
    al.add_argument("--target-path", dest="target_path",
                    help="a declared path, where the target is a file")
    al.add_argument("--label", help="what this link is, for a reader")
    al.set_defaults(func=add_link)

    fc = sub.add_parser("find-contact"); fc.add_argument("--name", required=True)
    fc.set_defaults(func=find_contact)

    r = sub.add_parser("render"); r.add_argument("--domain", default="all")
    r.set_defaults(func=lambda args: _rerender(args.domain))
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
