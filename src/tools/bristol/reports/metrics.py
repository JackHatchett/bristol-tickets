"""metrics.py — turn the roadmap DB into a dict of computed facts.

No file I/O, no Markdown, no notebook knowledge: give it a connection and the
ids of the cards that just left the board, get back a plain dict. That makes
every number here testable in isolation and re-renderable in any format.

WHAT IS AND IS NOT MEASURABLE
-----------------------------
Two different durations get called "how long did it take", and conflating them
is the most common way a delivery report lies:

  * lead time  = created_at -> closed_at. Always available. It answers "how
    long from raising this to finishing it", and it includes all the time the
    card sat untouched. On a personal board with a deep backlog this number is
    dominated by waiting, not working.
  * cycle time = first entry into `doing` -> closed_at. Answers "how long once
    started". Requires the transition log (`task_event`), which only began
    recording when it was added, so it is available for recent cards and
    genuinely absent for older ones. We report the coverage rather than
    silently averaging whatever happens to exist.

Percentiles use the nearest-rank method, and the pair reported is median + 85th
percentile. That pairing is the flow-metrics convention for a reason: the
median is the typical case, and the 85th is what you can actually promise,
because completion-time distributions are right-skewed and a mean is dragged
around by one stalled card.

Everything here degrades rather than fails. A board with two cards and no
history still produces a valid report that says so.
"""

from __future__ import annotations

import math
import sqlite3
from datetime import datetime, timezone

# A card closed within this many seconds of being created was almost certainly
# logged after the fact rather than planned then worked. Distinguishing the two
# matters: the first is bookkeeping, the second is delivery, and a board full of
# the former makes lead time meaningless.
INSTANT_CLOSE_SECONDS = 3600

# Cards sharing a closed_at to the second were closed by one bulk action, so
# that timestamp is an administrative moment, not the moment the work finished.
BATCH_CLOSE_TOLERANCE_SECONDS = 2

# Backlog items untouched for longer than this are stale: either they matter and
# are being avoided, or they do not and should be deleted.
STALE_BACKLOG_DAYS = 30

# Below this share of cards carrying an estimate or story points, sizing data is
# too sparse to compute anything from — treated the same as having none at all.
SIZING_COVERAGE_FLOOR = 0.2

SECONDS_PER_DAY = 86400.0


# ---------------------------------------------------------------------------
# small numeric helpers (stdlib only — Bristol's only dependency is PySide6)
# ---------------------------------------------------------------------------

def _parse_ts(value):
    """Parse a stored timestamp, tolerating every shape this DB has held.

    Rows written at different times carry full ISO-8601 with an offset, naive
    ISO, or a bare date (older epics). Anything unparseable returns None and is
    excluded from the statistic rather than defaulted to now(), which would
    quietly invent a duration.
    """
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    for candidate in (text, text.split(".")[0], text[:10]):
        try:
            dt = datetime.fromisoformat(candidate)
        except (ValueError, TypeError):
            continue
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def _days_between(start, end):
    a, b = _parse_ts(start), _parse_ts(end)
    if a is None or b is None:
        return None
    delta = (b - a).total_seconds() / SECONDS_PER_DAY
    return round(delta, 2) if delta >= 0 else None


def _percentile(values, pct):
    """Nearest-rank percentile: the smallest value at or below which `pct` of
    the sample falls. `pct` is a fraction (0.85 for p85).

    Nearest-rank rather than an interpolating method because the result should
    be an observed duration — "a card actually took this long" — not a number
    no card ever took.
    """
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return None
    rank = max(1, min(len(clean), math.ceil(pct * len(clean))))
    return clean[rank - 1]


def _median(values):
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return None
    mid = len(clean) // 2
    if len(clean) % 2:
        return clean[mid]
    return round((clean[mid - 1] + clean[mid]) / 2, 2)


def _distribution(values, series):
    """Count how many values fall in each labelled bucket of `series`.

    `series` is a list of (label, upper_bound_exclusive); the last bound may be
    None meaning "everything above". Used for the lead-time histogram.
    """
    out = []
    clean = [v for v in values if v is not None]
    lower = 0.0
    for label, upper in series:
        if upper is None:
            count = sum(1 for v in clean if v >= lower)
        else:
            count = sum(1 for v in clean if lower <= v < upper)
        out.append({"label": label, "count": count})
        lower = upper if upper is not None else lower
    return out


def _tally(rows, key, unknown="(none)"):
    """Count rows by an attribute, returned biggest-first as a share of total."""
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key) or unknown
        counts[value] = counts.get(value, 0) + 1
    total = sum(counts.values()) or 1
    return [
        {"name": name, "count": count, "share": round(count / total, 3)}
        for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def _table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


# ---------------------------------------------------------------------------
# card-level facts
# ---------------------------------------------------------------------------

def _load_cards(conn, task_ids):
    """One dict per card in the batch, with its durations already resolved."""
    if not task_ids:
        return []
    placeholders = ",".join("?" * len(task_ids))
    columns = [
        "id", "title", "description", "status", "stage", "priority",
        "record_type", "assignee", "reporter", "estimate", "story_points",
        "created_at", "updated_at", "closed_at", "epic_name", "epic_id",
    ]
    rows = conn.execute(
        f"""SELECT t.id, t.title, t.description, t.status, t.stage, t.priority,
                   COALESCE(t.record_type, 'build'),
                   t.assignee, t.reporter, t.estimate, t.story_points,
                   t.created_at, t.updated_at, t.closed_at,
                   e.name, e.id
            FROM task t LEFT JOIN epic e ON e.id = t.epic_id
            WHERE t.id IN ({placeholders})""",
        list(task_ids),
    ).fetchall()

    comments = dict(conn.execute(
        f"SELECT task_id, COUNT(*) FROM issue_log WHERE task_id IN ({placeholders}) "
        "GROUP BY task_id", list(task_ids),
    ).fetchall()) if _table_exists(conn, "issue_log") else {}

    # First entry into `doing` per card — the start of cycle time. MIN(at) is
    # correct even for a card that bounced in and out of `doing`: cycle time is
    # conventionally measured from first start, so re-work is counted, not
    # forgiven.
    first_doing = {}
    if _table_exists(conn, "task_event"):
        first_doing = dict(conn.execute(
            f"SELECT task_id, MIN(at) FROM task_event "
            f"WHERE task_id IN ({placeholders}) AND field='status' AND to_value='doing' "
            "GROUP BY task_id", list(task_ids),
        ).fetchall())

    cards = []
    for row in rows:
        card = dict(zip(columns, row))
        card["comments"] = comments.get(card["id"], 0)
        card["first_doing_at"] = first_doing.get(card["id"])
        # closed_at is the ordering timestamp Clear Done stamps; a card archived
        # by some other path may not have one, so fall back to updated_at rather
        # than dropping the card from every duration statistic.
        card["closed_effective"] = card["closed_at"] or card["updated_at"]
        card["lead_days"] = _days_between(card["created_at"], card["closed_effective"])
        card["cycle_days"] = (
            _days_between(card["first_doing_at"], card["closed_effective"])
            if card["first_doing_at"] else None
        )
        card["flow_efficiency"] = (
            round(card["cycle_days"] / card["lead_days"], 3)
            if card["cycle_days"] is not None and card["lead_days"] else None
        )
        span = _days_between(card["created_at"], card["closed_effective"])
        card["instant_close"] = (
            span is not None and span * SECONDS_PER_DAY <= INSTANT_CLOSE_SECONDS
        )
        cards.append(card)
    cards.sort(key=lambda c: (-(c["priority"] or 0), c["id"]))
    return cards


def _batch_close_groups(cards):
    """Cards sharing a close timestamp were swept by one action, not finished at
    that moment. Returned as groups of >1 so the report can say how much of its
    own lead-time evidence is administrative."""
    buckets: dict[int, list[int]] = {}
    for card in cards:
        ts = _parse_ts(card["closed_effective"])
        if ts is None:
            continue
        key = int(ts.timestamp()) // max(1, BATCH_CLOSE_TOLERANCE_SECONDS)
        buckets.setdefault(key, []).append(card["id"])
    return [ids for ids in buckets.values() if len(ids) > 1]


# ---------------------------------------------------------------------------
# board-wide context
# ---------------------------------------------------------------------------

def _work_in_progress(conn, now):
    """Cards left in `doing` on the active board, with their age.

    Work-item age is the metric that actually predicts trouble: unlike lead
    time, which you only learn once a card is finished, this is measurable
    while there is still time to act on it.
    """
    rows = conn.execute(
        """SELECT t.id, t.title, t.priority, t.assignee, t.created_at,
                  COALESCE(t.record_type,'build'), e.name
           FROM task t LEFT JOIN epic e ON e.id = t.epic_id
           WHERE t.stage='active' AND t.status='doing'
           ORDER BY t.priority DESC, t.id"""
    ).fetchall()
    first_doing = {}
    if _table_exists(conn, "task_event"):
        first_doing = dict(conn.execute(
            "SELECT task_id, MIN(at) FROM task_event "
            "WHERE field='status' AND to_value='doing' GROUP BY task_id"
        ).fetchall())
    out = []
    for tid, title, priority, assignee, created_at, record_type, epic in rows:
        started = first_doing.get(tid)
        out.append({
            "id": tid, "title": title, "priority": priority,
            "assignee": assignee or "(unassigned)", "record_type": record_type,
            "epic_name": epic, "created_at": created_at, "started_at": started,
            "age_days": _days_between(created_at, now),
            "doing_days": _days_between(started, now) if started else None,
        })
    return out


def _queue_snapshot(conn, now):
    """The `todo` column — committed but not started. Its size relative to
    throughput is how long the current queue would take to drain."""
    rows = conn.execute(
        "SELECT id, priority, created_at FROM task "
        "WHERE stage='active' AND status='todo'"
    ).fetchall()
    ages = [_days_between(created, now) for _, _, created in rows]
    return {
        "size": len(rows),
        "median_age_days": _median(ages),
        "oldest_days": max((a for a in ages if a is not None), default=None),
    }


def _backlog_snapshot(conn, now):
    rows = conn.execute(
        "SELECT id, title, priority, created_at, updated_at FROM task "
        "WHERE stage='backlog'"
    ).fetchall()
    ages = [_days_between(created, now) for _, _, _, created, _ in rows]
    stale = sum(
        1 for *_, updated in rows
        if (_days_between(updated, now) or 0) > STALE_BACKLOG_DAYS
    )
    oldest = None
    if rows:
        aged = [(a, r) for a, r in zip(ages, rows) if a is not None]
        if aged:
            days, row = max(aged, key=lambda pair: pair[0])
            oldest = {"id": row[0], "title": row[1], "age_days": days}
    return {
        "size": len(rows),
        "median_age_days": _median(ages),
        "oldest_days": max((a for a in ages if a is not None), default=None),
        "oldest_card": oldest,
        "stale_count": stale,
        "stale_share": round(stale / len(rows), 3) if rows else 0.0,
    }


def _historical_throughput(conn, now, weeks=8):
    """Cards closed per week over the trailing window, from the archive.

    Gives the current batch something to be compared against on the very first
    run, before any prior report exists to diff against.
    """
    rows = conn.execute(
        "SELECT COALESCE(closed_at, updated_at) FROM task "
        "WHERE stage='archive' OR (stage='active' AND status='done')"
    ).fetchall()
    end = _parse_ts(now)
    if end is None:
        return []
    buckets = [0] * weeks
    for (ts,) in rows:
        moment = _parse_ts(ts)
        if moment is None:
            continue
        age_weeks = int((end - moment).total_seconds() / (SECONDS_PER_DAY * 7))
        if 0 <= age_weeks < weeks:
            buckets[age_weeks] += 1
    return list(reversed(buckets))  # oldest week first


# ---------------------------------------------------------------------------
# signals — threshold-driven findings, each with a recommended action
# ---------------------------------------------------------------------------

def _signals(facts):
    """Rules-based findings. Every one names the number that triggered it and
    what to do, because a finding with neither is just decoration."""
    out = []

    def add(severity, title, detail, action):
        out.append({"severity": severity, "title": title,
                    "detail": detail, "action": action})

    batch = facts["batch"]
    n = len(batch)

    # 1. Stalled work in progress. Compared against the batch's own p85 lead
    #    time where available, so the threshold adapts to how this board runs.
    threshold = facts["lead_time"]["p85"] or 14
    stalled = [w for w in facts["wip"] if (w["age_days"] or 0) > threshold]
    if stalled:
        worst = max(stalled, key=lambda w: w["age_days"] or 0)
        add("attention", "Work in progress is aging past the norm",
            f"{len(stalled)} of {len(facts['wip'])} card(s) in Doing are older than "
            f"the {threshold:.1f}-day 85th-percentile lead time for this period. "
            f"Oldest: #{worst['id']} at {worst['age_days']:.0f} days.",
            "Finish it, split it, or move it back to Todo. A card that sits in "
            "Doing stops being a status and starts being a wish.")

    # 2. Bulk closes make closed_at administrative rather than real.
    grouped = sum(len(g) for g in facts["batch_close_groups"])
    if n and grouped / n > 0.3:
        add("watch", "Most cards were closed in bulk, not individually",
            f"{grouped} of {n} cards share a close timestamp with at least one "
            f"other ({len(facts['batch_close_groups'])} group(s)). Their closed_at "
            "is the moment they were swept, not the moment the work ended.",
            "Treat this period's lead times as an upper bound. Marking cards done "
            "as you finish them makes the next report's durations real.")

    # 3. Retroactive logging.
    instant = sum(1 for c in batch if c["instant_close"])
    if n and instant / n > 0.25:
        add("watch", "A quarter or more of the batch was logged after the fact",
            f"{instant} of {n} cards were created and closed within an hour.",
            "Fine as a record, but these cards carry no delivery signal — they "
            "were never forecast. Exclude them mentally from the lead-time table.")

    # 4. Rework pressure.
    fix_ratio = facts["mix"]["fix_ratio"]
    if n >= 5 and fix_ratio > 0.25:
        add("attention", "Fixes are a large share of completed work",
            f"{facts['mix']['fix']} of {n} cards ({fix_ratio:.0%}) were Fixes.",
            "Above roughly a quarter, rework is displacing new capability. Worth "
            "asking whether the Fixes trace back to a common source.")

    # 5. Work not laddering to an epic.
    no_epic = sum(1 for c in batch if not c["epic_name"])
    if n >= 5 and no_epic / n > 0.4:
        add("watch", "Most completed work sits outside any epic",
            f"{no_epic} of {n} cards had no epic.",
            "Either the epics no longer describe the real work, or the work is "
            "drifting from the plan. Both are worth ten minutes.")

    # 6. Delivery concentration.
    by_assignee = facts["by_assignee"]
    if n >= 5 and by_assignee and by_assignee[0]["share"] > 0.7:
        top = by_assignee[0]
        add("watch", "Delivery is concentrated in one owner",
            f"{top['name']} closed {top['count']} of {n} cards ({top['share']:.0%}).",
            "Expected on a personal board; worth noting only if you meant the "
            "fleet to be sharing this load.")

    # 7. Backlog rot.
    backlog = facts["backlog"]
    if backlog["stale_count"] and backlog["stale_share"] > 0.5:
        oldest = backlog["oldest_card"]
        detail = (f"{backlog['stale_count']} of {backlog['size']} backlog cards "
                  f"have not been touched in {STALE_BACKLOG_DAYS} days.")
        if oldest:
            detail += f" Oldest: #{oldest['id']} at {oldest['age_days']:.0f} days."
        add("attention", "The backlog is mostly untouched", detail,
            "Delete what you will not do. A backlog you do not trust is one you "
            "stop reading, and then it hides the things that mattered.")

    # 8. Priority not steering delivery.
    high = [c["lead_days"] for c in batch if (c["priority"] or 0) >= 60]
    low = [c["lead_days"] for c in batch if (c["priority"] or 0) < 30]
    hi_med, lo_med = _median(high), _median(low)
    if len(high) >= 3 and len(low) >= 3 and hi_med and lo_med and hi_med > lo_med * 1.5:
        add("attention", "High-priority cards took longer than low-priority ones",
            f"Median lead time: {hi_med:.1f}d for priority 60+, {lo_med:.1f}d for "
            "priority under 30.",
            "Priority is not currently predicting order of delivery. Either it is "
            "set after the fact, or the hard cards are simply the important ones.")

    # 9. Cycle-time coverage.
    cycle = facts["cycle_time"]
    if n and cycle["coverage"] < 0.5:
        add("watch", "Cycle time is not yet measurable for most cards",
            f"Only {cycle['n']} of {n} cards have a recorded start. The transition "
            "log begins when it was added, so older cards can never have one.",
            "Nothing to fix — coverage rises on its own as cards move through the "
            "board from here. Lead time carries this report in the meantime.")

    # 10. Fields that exist but are effectively never filled. Sized rather than
    #     binary: one card out of thirty-five carrying an estimate is the same
    #     situation as none of them, for anything you could compute from it.
    quality = facts["data_quality"]
    sized = max(quality["story_points_used"], quality["estimates_used"])
    if n >= 5 and sized / n < SIZING_COVERAGE_FLOOR:
        add("watch", "Estimate and story-point fields are going unused",
            f"{quality['estimates_used']} of {n} cards carried an estimate and "
            f"{quality['story_points_used']} carried story points.",
            "Not a problem in itself — but velocity and forecast accuracy are "
            "unavailable without one of them filled consistently. Either commit "
            "to a single sizing field or drop both from the card.")

    # 11. Written trace.
    silent = facts["discussion"]["silent"]
    if n >= 5 and silent / n > 0.6:
        add("watch", "Most cards closed with no written trace",
            f"{silent} of {n} cards had no comments at all.",
            "The board records that these happened but not what was decided. "
            "One line on close is usually enough to make the archive searchable.")

    order = {"attention": 0, "watch": 1}
    out.sort(key=lambda s: order.get(s["severity"], 2))
    return out


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def collect(conn, task_ids, now=None, period_start=None, prior=None):
    """Compute every fact the report needs.

    `task_ids`      the cards this period closed (what Clear Done just swept).
    `period_start`  ISO timestamp; defaults to the earliest creation in the
                    batch, so a first-ever report still has a sane window.
    `prior`         the previous report's frontmatter dict, or None.
    """
    now = now or datetime.now(timezone.utc).isoformat()
    conn.row_factory = None
    batch = _load_cards(conn, list(task_ids))

    created = [c["created_at"] for c in batch if c["created_at"]]
    closed = [c["closed_effective"] for c in batch if c["closed_effective"]]
    if period_start is None:
        period_start = min(created) if created else now
    period_end = max(closed) if closed else now
    period_days = _days_between(period_start, period_end) or 0.0

    lead = [c["lead_days"] for c in batch]
    cycle = [c["cycle_days"] for c in batch if c["cycle_days"] is not None]
    efficiency = [c["flow_efficiency"] for c in batch if c["flow_efficiency"] is not None]

    fixes = sum(1 for c in batch if c["record_type"] == "fix")
    comments = [c["comments"] for c in batch]

    # Throughput is normalised to a week so it survives irregular periods —
    # comparing "35 cards" across a 12-day and a 3-day period says nothing.
    weeks = max(period_days / 7.0, 1e-9)

    facts = {
        "generated_at": now,
        "period_start": period_start,
        "period_end": period_end,
        "period_days": round(period_days, 2),
        "batch": batch,
        "prior": prior,
        "throughput": {
            "count": len(batch),
            "per_week": round(len(batch) / weeks, 2) if period_days > 0 else None,
            "trailing_weeks": _historical_throughput(conn, now),
        },
        "lead_time": {
            "n": sum(1 for v in lead if v is not None),
            "median": _median(lead),
            "p85": _percentile(lead, 0.85),
            "max": max((v for v in lead if v is not None), default=None),
            "min": min((v for v in lead if v is not None), default=None),
            "distribution": _distribution(lead, [
                ("same day", 1), ("1–3 days", 3), ("3–7 days", 7),
                ("1–2 weeks", 14), ("over 2 weeks", None),
            ]),
        },
        "cycle_time": {
            "n": len(cycle),
            "coverage": round(len(cycle) / len(batch), 3) if batch else 0.0,
            "median": _median(cycle),
            "p85": _percentile(cycle, 0.85),
        },
        "flow_efficiency": {
            "n": len(efficiency),
            "median": _median(efficiency),
        },
        "mix": {
            "build": len(batch) - fixes,
            "fix": fixes,
            "fix_ratio": round(fixes / len(batch), 3) if batch else 0.0,
        },
        "by_epic": _tally(batch, "epic_name", unknown="(no epic)"),
        "by_assignee": _tally(batch, "assignee", unknown="(unassigned)"),
        "by_reporter": _tally(batch, "reporter", unknown="(unknown)"),
        "wip": _work_in_progress(conn, now),
        "queue": _queue_snapshot(conn, now),
        "backlog": _backlog_snapshot(conn, now),
        "discussion": {
            "total": sum(comments),
            "median_per_card": _median(comments),
            "silent": sum(1 for c in comments if not c),
            "most_discussed": max(batch, key=lambda c: c["comments"]) if batch else None,
        },
        "batch_close_groups": _batch_close_groups(batch),
        "data_quality": {
            "story_points_used": sum(1 for c in batch if c["story_points"]),
            "estimates_used": sum(1 for c in batch if c["estimate"]),
            "missing_created_at": sum(1 for c in batch if not c["created_at"]),
            "missing_closed_at": sum(1 for c in batch if not c["closed_at"]),
            "instant_closes": sum(1 for c in batch if c["instant_close"]),
            "has_event_log": _table_exists(conn, "task_event"),
        },
    }
    facts["signals"] = _signals(facts)
    return facts
