#!/usr/bin/env python3
"""
close_stale.py — close every open application and introduction that has gone
silent past its window.

The windows and the reading of "silent" are silence.py. Each close is written
through personal_write.py, so personal.db stays the record and the
applications snapshot is rendered from it once at the end: the status becomes
No response, an introduction's stage becomes no_response, and the open asks
about it close as dropped without moving anyone's last contact, since silence
is not an exchange.

Prints one line naming what closed — "Closed for silence: Company, Role; …" —
and nothing when nothing did, which is the line the morning briefing carries.

    python3 close_stale.py              # close, and print the line
    python3 close_stale.py --dry-run    # print what would close, write nothing

Reopening one is `personal_write.py reopen --id N`.
"""

import argparse
import contextlib
import datetime as dt
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_common as dbc
import personal_write as pw
import silence


def stale(today=None):
    """Every open item past its window, with the open asks about it."""
    conn = dbc.connect()
    try:
        apps = [dict(r) for r in conn.execute("SELECT * FROM applications")]
        links = [
            dict(r)
            for r in conn.execute(
                "SELECT contact_id, target_id FROM contact_link WHERE target_kind='application'"
            )
        ]
        asks = [dict(r) for r in conn.execute("SELECT * FROM contact_ask WHERE status='open'")]
    finally:
        conn.close()
    out = []
    for app in apps:
        people = {link["contact_id"] for link in links if link["target_id"] == app["id"]}
        about = silence.matching_asks(app, [a for a in asks if a["contact_id"] in people])
        if silence.is_stale(app, about, today):
            out.append((app, about))
    return out


def _run(argv):
    """One personal_write.py command, its own report swallowed so this
    program's single line is the whole of its output."""
    args = pw.build_parser().parse_args(argv)
    with contextlib.redirect_stdout(io.StringIO()):
        args.func(args)


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", help="YYYY-MM-DD to measure from; default today")
    args = ap.parse_args(argv)
    today = dt.date.fromisoformat(args.today) if args.today else None
    items = stale(today)
    if not items:
        return 0
    if not args.dry_run:
        for app, about in items:
            cmd = [
                "update-application",
                "--id",
                str(app["id"]),
                "--status",
                "No response",
                "--no-render",
            ]
            if app.get("intro_stage"):
                cmd += ["--intro-stage", "no_response"]
            _run(cmd)
            for a in about:
                _run(
                    [
                        "close-ask",
                        "--id",
                        str(a["id"]),
                        "--status",
                        "dropped",
                        "--keep-last-contact",
                        "--no-render",
                    ]
                )
        with contextlib.redirect_stdout(io.StringIO()):
            pw._rerender("applications")
            pw._rerender("contacts")
    names = "; ".join(f"{a['company']}, {a['role'] or 'role not recorded'}" for a, _ in items)
    print(
        f"Closed for silence: {names}"
        if not args.dry_run
        else f"Would close for silence ({len(items)}): {names}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
