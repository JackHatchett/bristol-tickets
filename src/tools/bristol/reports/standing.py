"""standing.py — what the projects cost over a window, and what upkeep cost
beside them.

A project epic reports when it closes, because closing it is the user saying the
effort is over. Standing work has no such moment, so this report is asked for: a
start date, an end date, and every card that finished between them, whatever its
epic. The Settings page and the reports CLI both call `standing_report`.

WHAT A SIZE COUNTS AS
---------------------
A card's estimate answers how much of a full usage budget it would take, so a
sum of estimates over a window is a share of budget rather than a count of days.
`src/skills/manage-tickets/SKILL.md` gives the bands; each size is counted at the
middle of its own band, and every report says so in its own words so no reader
has to assume a weighting. A card with no estimate is counted as a card and
never as zero spend: it is reported as unsized, because a board that sizes
nothing would otherwise read as a board that spent nothing.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if __package__ in (None, ""):  # allow `python3 standing.py` from the folder
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from reports.generate import ReportResult  # type: ignore
    from reports.paths import resolve_reports_dir  # type: ignore
else:
    from .generate import ReportResult
    from .paths import resolve_reports_dir

# The middle of each band in the size scale, as a share of one full budget.
SPEND = {"S": 0.05, "M": 0.3, "L": 0.75, "XL": 1.5}
BANDS = "S under a tenth of a budget, M a tenth to a half, L a half to a whole, XL more than one"
STANDING_KIND = "standing"
FILENAME = "bristol_standing_%Y-%m-%d"
DEFAULT_WINDOW_DAYS = 30


def default_window(today=None) -> tuple[str, str]:
    """The window offered when none was chosen: the last thirty days, ending
    today. A month is long enough to hold upkeep that happens weekly and short
    enough to still describe the board as it stands."""
    end = today or datetime.now(timezone.utc).date()
    return (end - timedelta(days=DEFAULT_WINDOW_DAYS)).isoformat(), end.isoformat()


def collect(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """Every card that finished between the two dates, split into the work an
    effort is made of and the work that keeps things running.

    A card with no epic at all is counted as standing: a card that is the whole
    of its own subject is what standing work is, and the board attributes one to
    the standing workstream as it finishes.
    """
    rows = conn.execute(
        "SELECT t.id, t.title, COALESCE(t.estimate,''), t.closed_at, "
        "       COALESCE(t.assignee,'user'), e.id, e.name, "
        "       LOWER(COALESCE(e.type,'')) "
        "  FROM task t LEFT JOIN epic e ON t.epic_id = e.id "
        " WHERE t.closed_at IS NOT NULL "
        "   AND t.closed_at >= ? AND t.closed_at <= ? "
        " ORDER BY t.closed_at",
        (f"{start}T00:00:00+00:00", f"{end}T23:59:59.999999+00:00"),
    ).fetchall()

    sides = {"project": [], "standing": []}
    epics: dict[str, dict] = {}
    for task_id, title, estimate, closed_at, owner, epic_id, epic_name, kind in rows:
        standing = epic_id is None or kind == STANDING_KIND
        card = {
            "id": task_id, "title": title, "estimate": (estimate or "").upper(),
            "closed_at": closed_at, "owner": owner,
            "epic": epic_name or "",
            "spend": SPEND.get((estimate or "").upper()),
        }
        sides["standing" if standing else "project"].append(card)
        if not standing:
            held = epics.setdefault(epic_name or f"#{epic_id}",
                                    {"cards": 0, "spend": 0.0, "unsized": 0})
            held["cards"] += 1
            held["spend"] += card["spend"] or 0.0
            held["unsized"] += 0 if card["spend"] else 1

    def summarise(cards):
        return {
            "cards": len(cards),
            "spend": round(sum(c["spend"] or 0.0 for c in cards), 2),
            "unsized": sum(1 for c in cards if not c["spend"]),
        }

    project, standing = summarise(sides["project"]), summarise(sides["standing"])
    total = round(project["spend"] + standing["spend"], 2)
    for side in (project, standing):
        side["share"] = round(side["spend"] / total, 3) if total else 0.0
    return {
        "start": start, "end": end,
        "project": project, "standing": standing,
        "total_spend": total,
        "total_cards": project["cards"] + standing["cards"],
        "epics": dict(sorted(epics.items(), key=lambda kv: -kv[1]["spend"])),
        "cards": sides,
    }


def _line(name, side) -> str:
    unsized = f"{side['unsized']} unsized" if side["unsized"] else "all sized"
    return (f"| {name} | {side['cards']} | {side['spend']:.2f} | "
            f"{side['share'] * 100:.0f}% | {unsized} |")


def render(facts: dict) -> str:
    """The note itself: two lines that answer the planning question, then the
    project side broken out by effort."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    project, standing = facts["project"], facts["standing"]
    lines = [
        "---",
        f"created: {generated}",
        "tags:",
        "  - bristol/report",
        "type: bristol-standing-report",
        f"period_start: {facts['start']}",
        f"period_end: {facts['end']}",
        f"cards_closed: {facts['total_cards']}",
        f"project_cards: {project['cards']}",
        f"project_spend: {project['spend']}",
        f"standing_cards: {standing['cards']}",
        f"standing_spend: {standing['spend']}",
        f"standing_share: {standing['share']}",
        "---",
        "",
        f"# Standing Work — {facts['start']} to {facts['end']}",
        "",
        f"_{facts['total_cards']} card(s) finished in this window._",
        "",
        "#### What it cost",
        "",
        "| Work | Cards | Budget | Share | Sizing |",
        "| --- | --- | --- | --- | --- |",
        _line("Projects", project),
        _line("Standing", standing),
        "",
        f"Budget is a share of one full usage budget, each card counted at the "
        f"middle of its size band ({BANDS}). A card with no size is counted as "
        f"a card and adds nothing to the budget column, so a window with "
        f"unsized cards cost at least what it says and probably more.",
        "",
    ]
    if facts["epics"]:
        lines += ["#### The projects", ""]
        for name, held in facts["epics"].items():
            unsized = f", {held['unsized']} unsized" if held["unsized"] else ""
            lines.append(f"- {name} — {held['cards']} card(s), "
                         f"{held['spend']:.2f} of a budget{unsized}")
        lines.append("")
    if facts["cards"]["standing"]:
        lines += ["#### The upkeep", ""]
        for card in facts["cards"]["standing"]:
            size = card["estimate"] or "unsized"
            lines.append(f"- #{card['id']} {card['title']} — {size} · "
                         f"{card['owner']}")
        lines.append("")
    lines += ["---", "",
              "*Generated by Bristol Tickets on request, over the window asked "
              "for. Source: `src/tools/bristol/reports/`.*", ""]
    return "\n".join(lines)


def standing_report(conn, start=None, end=None, out_dir=None) -> ReportResult:
    """Write the report for one window and say what happened.

    A window nothing finished in writes no file: an empty note is a note the
    next reader has to open to learn nothing.
    """
    if not start or not end:
        default_start, default_end = default_window()
        start, end = start or default_start, end or default_end
    if start > end:
        start, end = end, start

    facts = collect(conn, start, end)
    if not facts["total_cards"]:
        return ReportResult(
            skipped=f"nothing finished between {start} and {end}",
            facts=facts)

    reports_dir = resolve_reports_dir(out_dir)
    if reports_dir is None:
        return ReportResult(
            skipped="no reports folder configured or reachable "
                    "(set markdown_notebook.reports_dir in config.local.json, "
                    "or the BRISTOL_REPORTS_DIR env var)",
            facts=facts)

    target = reports_dir / f"bristol_standing_{start}_{end}.md"
    suffix = 2
    while target.exists():
        target = reports_dir / f"bristol_standing_{start}_{end}_{suffix}.md"
        suffix += 1
    try:
        target.write_text(render(facts), encoding="utf-8")
    except OSError as exc:
        return ReportResult(error=f"could not write {target}: {exc}")
    return ReportResult(written=target, facts=facts)
