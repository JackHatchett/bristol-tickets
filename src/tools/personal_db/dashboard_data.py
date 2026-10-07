#!/usr/bin/env python3
"""
dashboard_data.py — the career dashboard's data, read from personal.db.

Writes one JSON document holding what the dashboard draws from the database:
each friend with their open asks and the introductions running through them,
and the applications at interview stage. It reads and never writes the
database; the JSON is a generated view, like the xlsx snapshots.

An item past its silence window is left out, so the dashboard shows only what
can still be acted on. Leaving an item out changes nothing in the database.

    python3 dashboard_data.py --out <path>      # or CAREER_DASHBOARD_JSON
    python3 dashboard_data.py --print           # to stdout
"""

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))
import db_common as dbc  # noqa: E402

WINDOW_DAYS = {"intro": 30, "interview": 21}
RECENT_CONTACT_DAYS = 90
CLOSED = re.compile(r"^(rejected|withdrawn|abandoned|no response|offer declined|closed)",
                    re.I)
INTERVIEW = re.compile(r"interview|screen|recruiter call|assignment|in progress", re.I)
LINK_ROLES = {"introducer", "referrer"}


def _cols(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _date(value):
    if not value:
        return None
    m = re.match(r"(\d{4})-(\d{2})(?:-(\d{2}))?", str(value))
    if not m:
        return None
    return dt.date(int(m[1]), int(m[2]), int(m[3] or 1))


def _days(since, today):
    return (today - since).days if since else None


def _person(row, cols):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"] if "email" in cols else None,
        "linkedin": row["linkedin_url"] if "linkedin_url" in cols else None,
    }


def build(today=None):
    today = today or dt.date.today()
    conn = sqlite3.connect(f"file:{dbc.db_path()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        ccols = _cols(conn, "contact")
        contacts = {r["id"]: r for r in conn.execute("SELECT * FROM contact")}
        asks = [dict(r) for r in conn.execute(
            "SELECT * FROM contact_ask WHERE status = 'open'")]
        links = [dict(r) for r in conn.execute(
            "SELECT * FROM contact_link WHERE target_kind = 'application'")]
        app_ids = {l["target_id"] for l in links if l["target_id"]}
        apps = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM applications")}
    finally:
        conn.close()

    targets = {}
    for l in links:
        if (l["label"] or "") == "intro target":
            targets.setdefault(l["target_id"], []).append(l["contact_id"])

    has_flag = "is_friend" in ccols
    if has_flag:
        friend_ids = [i for i, r in contacts.items() if r["is_friend"]]
    else:
        # Until contacts carry a friend marker, a friend is anyone who is not
        # only somebody's intro target; the rows with nothing live are dropped
        # after they are built.
        only_target = {l["contact_id"] for l in links if l["label"] == "intro target"}
        friend_ids = [i for i in contacts if i not in only_target
                      or any(l["contact_id"] == i and l["label"] != "intro target"
                             for l in links)]

    friends = []
    for fid in sorted(friend_ids, key=lambda i: contacts[i]["name"]):
        c = contacts[fid]
        f_asks = [a for a in asks if a["contact_id"] == fid]
        used_asks = set()
        intros = []
        for l in links:
            if l["contact_id"] != fid or (l["label"] or "") not in LINK_ROLES:
                continue
            app = apps.get(l["target_id"])
            if not app or CLOSED.match(app["status"] or ""):
                continue
            match = [a for a in f_asks
                     if f"app {app['id']}" in (a["subject"] or "")
                     or str(app["id"]) in re.findall(r"\d+", a["subject"] or "")
                     or (app["company"] or "~").lower() in (a["subject"] or "").lower()]
            used_asks.update(a["id"] for a in match)
            touches = [_date(app["date_evaluated"])]
            touches += [_date(a["last_touch"]) or _date(a["opened_on"]) for a in match]
            last = max([t for t in touches if t], default=None)
            silent = _days(last, today)
            if silent is not None and silent > WINDOW_DAYS["intro"]:
                continue
            move = match[0]["direction"] if match else "them"
            tids = targets.get(app["id"]) or [fid]
            for tid in tids:
                t = contacts.get(tid)
                intros.append({
                    "app_id": app["id"],
                    "target": _person(t, ccols),
                    "target_is_friend": tid == fid,
                    "company": app["company"],
                    "role": app["role"],
                    "jd_link": app["jd_link"],
                    "status": app["status"],
                    "move": move,
                    "days_silent": silent,
                })
        loose = [{"subject": a["subject"], "kind": a["kind"], "move": a["direction"],
                  "opened_on": a["opened_on"]}
                 for a in f_asks if a["id"] not in used_asks]
        last = _date(c["last_contact_on"])
        friends.append({
            **_person(c, ccols),
            "how_known": c["how_known"],
            "company": c["company"],
            "last_contact_on": c["last_contact_on"],
            "days_since_contact": _days(last, today),
            "reference_status": c["reference_status"] if "reference_status" in ccols else None,
            "asks": loose,
            "intros": intros,
        })

    if not has_flag:
        friends = [f for f in friends if f["intros"] or f["asks"]
                   or (f["days_since_contact"] is not None
                       and f["days_since_contact"] <= RECENT_CONTACT_DAYS)]

    interviews = []
    for app in apps.values():
        st = app["status"] or ""
        if CLOSED.match(st) or not INTERVIEW.search(st):
            continue
        silent = _days(_date(app["date_evaluated"]), today)
        if silent is not None and silent > WINDOW_DAYS["interview"]:
            continue
        interviews.append({"app_id": app["id"], "company": app["company"],
                           "role": app["role"], "status": st,
                           "jd_link": app["jd_link"], "days_silent": silent})

    return {"generated_at": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
            "windows_days": WINDOW_DAYS, "friends": friends, "interviews": interviews}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.environ.get("CAREER_DASHBOARD_JSON"))
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--tz", default=os.environ.get("DASHBOARD_TZ"),
                    help="IANA zone that decides what today is; default the machine's")
    args = ap.parse_args(argv)
    today = None
    if args.tz:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo(args.tz)).date()
    doc = json.dumps(build(today), indent=2)
    if args.print or not args.out:
        print(doc)
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc)  # in place: a synced folder keeps the file's identity
    print(f"[dashboard_data] {len(json.loads(doc)['friends'])} friends -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
