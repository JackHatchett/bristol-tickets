#!/usr/bin/env python3
"""
dashboard_data.py — the career dashboard's data, read from personal.db.

Writes one JSON document containing what the dashboard draws from the database:
each friend with their open asks and the introductions running through them,
and the applications at interview stage. It reads and never writes the
database; the JSON is a generated view, like the xlsx snapshots.

An item past its silence window is left out, so the dashboard shows only what
can still be acted on. The windows are silence.py, which close_stale.py also
reads, so what the dashboard hides is what the daily close closes.

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
import silence  # noqa: E402
from silence import CLOSED, INTERVIEW, WINDOW_DAYS  # noqa: E402

RECENT_CONTACT_DAYS = 90
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
        asks = [dict(r) for r in conn.execute("SELECT * FROM contact_ask WHERE status = 'open'")]
        links = [
            dict(r)
            for r in conn.execute("SELECT * FROM contact_link WHERE target_kind = 'application'")
        ]
        apps = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM applications")}
        has_view = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='view' AND name='v_introduction'"
        ).fetchone()
        intro = (
            {r["app_id"]: dict(r) for r in conn.execute("SELECT * FROM v_introduction")}
            if has_view
            else {}
        )
        has_rest = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='view' AND name='v_friend_rest'"
        ).fetchone()
        rest = (
            {
                r["contact_id"]: r["next_ask_on"]
                for r in conn.execute("SELECT contact_id, next_ask_on FROM v_friend_rest")
            }
            if has_rest
            else {}
        )
    finally:
        conn.close()

    targets = {}
    for link in links:
        if (link["label"] or "") == "intro target":
            targets.setdefault(link["target_id"], []).append(link["contact_id"])

    # A row is drawn for anyone who is not only somebody's intro target. A
    # friend's row is durable; anyone else's is dropped, after it is built,
    # once nothing on it is live.
    has_flag = "is_friend" in ccols
    only_target = {link["contact_id"] for link in links if link["label"] == "intro target"}
    friend_ids = [
        i
        for i in contacts
        if i not in only_target
        or any(link["contact_id"] == i and link["label"] != "intro target" for link in links)
        or (has_flag and contacts[i]["is_friend"])
    ]

    friends = []
    for fid in sorted(friend_ids, key=lambda i: contacts[i]["name"]):
        c = contacts[fid]
        f_asks = [a for a in asks if a["contact_id"] == fid]
        used_asks = set()
        intros = []
        for link in links:
            if link["contact_id"] != fid or (link["label"] or "") not in LINK_ROLES:
                continue
            app = apps.get(link["target_id"])
            if not app or CLOSED.match(app["status"] or ""):
                continue
            stage = intro.get(app["id"])
            if stage and stage["move"] is None:
                continue  # the introduction has closed
            match = silence.matching_asks(app, f_asks)
            used_asks.update(a["id"] for a in match)
            silent = silence.days_silent(app, match, today)
            if silent is not None and silent > WINDOW_DAYS["intro"]:
                continue
            if stage:
                move = stage["move"]
            else:
                move = match[0]["direction"] if match else "them"
            tids = targets.get(app["id"]) or [fid]
            for tid in tids:
                t = contacts.get(tid)
                intros.append(
                    {
                        "app_id": app["id"],
                        "target": _person(t, ccols),
                        "target_is_friend": tid == fid,
                        "company": app["company"],
                        "role": app["role"],
                        "jd_link": app["jd_link"],
                        "status": app["status"],
                        "stage": stage["stage"] if stage else None,
                        "move": move,
                        "days_silent": silent,
                    }
                )
        loose = [
            {
                "subject": a["subject"],
                "kind": a["kind"],
                "move": a["direction"],
                "opened_on": a["opened_on"],
            }
            for a in f_asks
            if a["id"] not in used_asks
        ]
        last = _date(c["last_contact_on"])
        friends.append(
            {
                **_person(c, ccols),
                "is_friend": bool(c["is_friend"]) if has_flag else None,
                "how_known": c["how_known"],
                "company": c["company"],
                "last_contact_on": c["last_contact_on"],
                "days_since_contact": _days(last, today),
                "reference_status": c["reference_status"] if "reference_status" in ccols else None,
                "next_ask_on": rest.get(fid),
                "asks": loose,
                "intros": intros,
            }
        )

    friends = [
        f
        for f in friends
        if f["is_friend"]
        or f["intros"]
        or f["asks"]
        or (
            not has_flag
            and f["days_since_contact"] is not None
            and f["days_since_contact"] <= RECENT_CONTACT_DAYS
        )
    ]

    interviews = []
    for app in apps.values():
        st = app["status"] or ""
        if CLOSED.match(st) or not INTERVIEW.search(st):
            continue
        silent = silence.days_silent(app, (), today)
        if silent is not None and silent > WINDOW_DAYS["interview"]:
            continue
        interviews.append(
            {
                "app_id": app["id"],
                "company": app["company"],
                "role": app["role"],
                "status": st,
                "jd_link": app["jd_link"],
                "days_silent": silent,
            }
        )

    return {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "windows_days": WINDOW_DAYS,
        "friends": friends,
        "interviews": interviews,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--out", default=os.environ.get("CAREER_DASHBOARD_JSON"))
    ap.add_argument("--print", action="store_true")
    ap.add_argument(
        "--tz",
        default=os.environ.get("DASHBOARD_TZ"),
        help="IANA zone that decides what today is; default the machine's",
    )
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
