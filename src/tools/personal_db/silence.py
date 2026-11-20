#!/usr/bin/env python3
"""
silence.py — how long an open application or introduction may go silent, and
how long it has been.

The one place the silence windows live. close_stale.py closes what has run past
its window; dashboard_data.py leaves the same items out of the career
dashboard. Both read the window and the last touch from here, so the dashboard
and the database never disagree about what is dead.

A window by kind:
  applied   — applied, and no person at the company has been in touch: 30 days
  interview — a recruiter screen or an interview has happened: 21 days
  intro     — an introduction, or an application waiting on a referral: 30 days
"""

import calendar
import datetime as dt
import re

WINDOW_DAYS = {"applied": 30, "interview": 21, "intro": 30}

CLOSED = re.compile(r"^(rejected|withdrawn|abandoned|no response|offer declined|closed)", re.I)
INTERVIEW = re.compile(r"interview|screen|recruiter call|assignment|in progress", re.I)
APPLIED = re.compile(r"^applied", re.I)
REFERRAL_GATED = re.compile(r"referral", re.I)
INTRO_OPEN = ("to_ask", "asked", "introduced", "submitted", "interviewing")


def parse_date(value, end=False):
    """An ISO date, a year-month, or a year, as a date.

    A partial date is read as the start of its period, or with `end` as its last
    day — the reading that can only make an item look younger, never older.
    """
    if not value:
        return None
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", str(value))
    if not m:
        return None
    y = int(m[1])
    if m[2] is None:
        return dt.date(y, 12, 31) if end else dt.date(y, 1, 1)
    mo = int(m[2])
    if m[3] is None:
        return dt.date(y, mo, calendar.monthrange(y, mo)[1]) if end else dt.date(y, mo, 1)
    return dt.date(y, mo, int(m[3]))


def kind(app):
    """The window an open application falls under, or None when it has none —
    closed already, only evaluated, or a status this rule does not reach."""
    status = app.get("status") or ""
    stage = app.get("intro_stage")
    if stage:
        return "intro" if stage in INTRO_OPEN else None
    if CLOSED.match(status):
        return None
    if REFERRAL_GATED.search(status) and not INTERVIEW.search(status):
        return "intro"
    if INTERVIEW.search(status):
        return "interview"
    if APPLIED.match(status):
        return "applied"
    return None


def matching_asks(app, asks):
    """The asks that are about this application: its id or its company in the
    subject. `asks` are the asks of the people linked to it."""

    def subj(a):
        return a.get("subject") or ""

    return [
        a
        for a in asks
        if f"app {app['id']}" in subj(a)
        or str(app["id"]) in re.findall(r"\d+", subj(a))
        or (app.get("company") or "~").lower() in subj(a).lower()
    ]


def last_touch(app, asks=()):
    """The latest recorded exchange on an application: the day it was
    evaluated, the last touch recorded on it, the day its introduction stage
    was set, and the last touch of every ask about it."""
    touches = [
        parse_date(app.get("date_evaluated"), end=True) or parse_date(app.get("year"), end=True),
        parse_date(app.get("last_touch_on")),
        parse_date(app.get("intro_stage_on")),
    ]
    touches += [parse_date(a.get("last_touch")) or parse_date(a.get("opened_on")) for a in asks]
    return max([t for t in touches if t], default=None)


def days_silent(app, asks=(), today=None):
    t = last_touch(app, asks)
    return ((today or dt.date.today()) - t).days if t else None


def is_stale(app, asks=(), today=None):
    """True when an open item has been silent longer than its window."""
    k = kind(app)
    silent = days_silent(app, asks, today)
    return bool(k and silent is not None and silent > WINDOW_DAYS[k])
