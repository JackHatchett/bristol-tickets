"""render.py — the facts dict from metrics.py, as a Markdown note.

House style is taken from the notebook's existing generated artefact, the daily
briefing: YAML frontmatter, an `#` title, `####` section headers, a prose
executive summary before any table, bold-lead bullets, `---` rules, and an
italic generation footer naming what produced the file. Nothing here invents a
new convention for the vault to absorb.

Two decisions worth stating:

*   Every headline number is repeated in the frontmatter. Rendered prose is for
    reading one report; frontmatter is what Dataview queries across all of
    them, which is what turns a pile of notes into a trend line. The index note
    (see generate.py) is the payoff.
*   Charts are drawn with block characters rather than an image or a plugin
    chart. They render in preview, in source mode, on mobile, and in a diff —
    and they survive being read ten years from now by something that is not
    Obsidian.

No DB access and no file I/O: this module takes a dict and returns a string.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .metrics import SIZING_COVERAGE_FLOOR, _parse_ts

BAR_FULL = "█"
BAR_EMPTY = "·"
BAR_WIDTH = 24


# ---------------------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------------------

def _date(value, fmt="%Y-%m-%d"):
    dt = _parse_ts(value)
    return dt.strftime(fmt) if dt else "—"


def _days(value, precision=1):
    if value is None:
        return "—"
    if value < 1:
        hours = value * 24
        return f"{hours:.0f}h" if hours >= 1 else "<1h"
    return f"{value:.{precision}f}d"


def _pct(value):
    return "—" if value is None else f"{value:.0%}"


def _bar(count, biggest, width=BAR_WIDTH):
    if not biggest:
        return ""
    filled = int(round(width * count / biggest))
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


def _delta(current, prior, lower_is_better=False, unit=""):
    """Signed change against the previous report, or an em dash on first run.

    The ⚠ marks movement in the unwanted direction, which depends on the
    metric: lead time falling is good, throughput falling is not, so each
    caller declares which way is better rather than the arrow implying it.

    A metric already expressed in percentage points gets no relative figure
    appended — "20pp (100%)" invites the reader to compare a change in a ratio
    against the ratio itself, which is a number with no useful meaning.
    """
    if current is None or prior is None:
        return "—"
    try:
        prior = float(prior)
    except (TypeError, ValueError):
        return "—"
    change = current - prior
    if abs(change) < 1e-9:
        return "no change"
    whole = unit == "" and float(current).is_integer() and prior.is_integer()
    magnitude = f"{change:+.0f}" if whole else f"{change:+.1f}{unit}"
    if prior and unit != "pp":
        magnitude += f" ({abs(change) / abs(prior):.0%})"
    improving = (change < 0) if lower_is_better else (change > 0)
    return f"{magnitude} {'▲' if change > 0 else '▼'}{'' if improving else ' ⚠'}"


def _escape(text):
    """Make a ticket title safe inside a Markdown table cell."""
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def _truncate(text, limit=64):
    text = _escape(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# executive summary — deterministic prose, no model call
# ---------------------------------------------------------------------------

def _summary(f):
    """Assemble the opening paragraph from the computed facts.

    Rules-based rather than generated: this runs behind a Qt button with no
    network, it must produce the same words for the same numbers, and a summary
    that can hallucinate is worse than no summary. The sentences are ordered
    the way a reader needs them — what happened, how fast, what it cost, what
    is stuck, what to look at.
    """
    n = f["throughput"]["count"]
    lead, cycle = f["lead_time"], f["cycle_time"]
    sentences = []

    period = f["period_days"]
    span = f"{period:.0f} days" if period >= 1 else "under a day"
    sentences.append(
        f"This period closed {n} card{'s' if n != 1 else ''} over {span}"
        + (f", a rate of {f['throughput']['per_week']:.1f} per week"
           if f["throughput"]["per_week"] else "")
        + "."
    )

    if lead["median"] is not None:
        sentence = (
            f"Typical card took {_days(lead['median'])} from raised to closed, "
            f"with the slowest 15% taking {_days(lead['p85'])} or more"
        )
        if lead["max"] is not None:
            sentence += f" and the longest running {_days(lead['max'], 0)}"
        sentences.append(sentence + ".")

    if cycle["n"]:
        sentences.append(
            f"Of those, {cycle['n']} had a recorded start, giving a median cycle "
            f"time of {_days(cycle['median'])} once work actually began."
        )
    else:
        sentences.append(
            "None of these cards had a recorded start, so this report measures "
            "lead time only — cycle time becomes available as cards move through "
            "the board from here."
        )

    mix = f["mix"]
    if mix["fix"]:
        sentences.append(
            f"{mix['build']} were Builds and {mix['fix']} were Fixes "
            f"({_pct(mix['fix_ratio'])} rework)."
        )

    top = f["by_epic"][0] if f["by_epic"] else None
    if top and top["name"] != "(no epic)":
        sentences.append(
            f"The heaviest epic was {top['name']} at {top['count']} card"
            f"{'s' if top['count'] != 1 else ''} ({_pct(top['share'])} of the batch)."
        )

    wip = f["wip"]
    if wip:
        oldest = max(wip, key=lambda w: w["age_days"] or 0)
        plural = len(wip) != 1
        sentences.append(
            f"{len(wip)} card{'s' if plural else ''} "
            f"{'remain' if plural else 'remains'} in Doing; the oldest, "
            f"#{oldest['id']}, has been open {_days(oldest['age_days'], 0)}."
        )
    else:
        sentences.append("Nothing is left in the Doing column.")

    attention = [s for s in f["signals"] if s["severity"] == "attention"]
    if attention:
        sentences.append(
            f"{len(attention)} finding{'s' if len(attention) != 1 else ''} below "
            f"warrant{'' if len(attention) != 1 else 's'} a look, starting with "
            f"{attention[0]['title'][0].lower()}{attention[0]['title'][1:]}."
        )
    elif f["signals"]:
        sentences.append("Nothing needs attention; the notes below are context only.")

    return " ".join(sentences)


# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------

def _frontmatter(f, slug, previous_slug):
    lead, cycle, backlog = f["lead_time"], f["cycle_time"], f["backlog"]
    wip_oldest = max((w["age_days"] or 0 for w in f["wip"]), default=0)

    def num(value):
        return "null" if value is None else value

    lines = [
        "---",
        f'created: {_date(f["generated_at"], "%Y-%m-%d %H:%M")}',
        "tags:",
        "  - bristol/report",
        "type: bristol-report",
        f'date: {_date(f["generated_at"])}',
        f"slug: {slug}",
        f'period_start: {_date(f["period_start"])}',
        f'period_end: {_date(f["period_end"])}',
        f'period_days: {f["period_days"]}',
        f'cards_closed: {f["throughput"]["count"]}',
        f'throughput_per_week: {num(f["throughput"]["per_week"])}',
        f'lead_time_median_days: {num(lead["median"])}',
        f'lead_time_p85_days: {num(lead["p85"])}',
        f'cycle_time_median_days: {num(cycle["median"])}',
        f'cycle_time_coverage: {cycle["coverage"]}',
        f'builds: {f["mix"]["build"]}',
        f'fixes: {f["mix"]["fix"]}',
        f'fix_ratio: {f["mix"]["fix_ratio"]}',
        f'wip_count: {len(f["wip"])}',
        f"wip_oldest_days: {round(wip_oldest, 2)}",
        f'queue_size: {f["queue"]["size"]}',
        f'backlog_size: {backlog["size"]}',
        f'backlog_oldest_days: {num(backlog["oldest_days"])}',
        f'signals: {len(f["signals"])}',
        f'signals_attention: {sum(1 for s in f["signals"] if s["severity"] == "attention")}',
    ]
    if previous_slug:
        lines.append(f"previous: {previous_slug}")
    lines.append("---")
    return "\n".join(lines)


def _headline_table(f):
    prior = f["prior"] or {}
    lead, cycle = f["lead_time"], f["cycle_time"]
    rows = [
        ("Cards closed", str(f["throughput"]["count"]),
         _delta(f["throughput"]["count"], prior.get("cards_closed"))),
        ("Throughput / week",
         f'{f["throughput"]["per_week"]:.1f}' if f["throughput"]["per_week"] else "—",
         _delta(f["throughput"]["per_week"], prior.get("throughput_per_week"))),
        ("Lead time (median)", _days(lead["median"]),
         _delta(lead["median"], prior.get("lead_time_median_days"),
                lower_is_better=True, unit="d")),
        ("Lead time (85th pct)", _days(lead["p85"]),
         _delta(lead["p85"], prior.get("lead_time_p85_days"),
                lower_is_better=True, unit="d")),
        ("Cycle time (median)",
         _days(cycle["median"]) + (f' · {_pct(cycle["coverage"])} coverage'
                                   if cycle["n"] else ""),
         _delta(cycle["median"], prior.get("cycle_time_median_days"),
                lower_is_better=True, unit="d")),
        ("Fix ratio", _pct(f["mix"]["fix_ratio"]),
         _delta(f["mix"]["fix_ratio"] * 100,
                (prior.get("fix_ratio") or 0) * 100 if prior.get("fix_ratio") is not None else None,
                lower_is_better=True, unit="pp")),
        ("In progress now", str(len(f["wip"])),
         _delta(len(f["wip"]), prior.get("wip_count"), lower_is_better=True)),
        ("Queued (Todo)", str(f["queue"]["size"]),
         _delta(f["queue"]["size"], prior.get("queue_size"))),
        ("Backlog", str(f["backlog"]["size"]),
         _delta(f["backlog"]["size"], prior.get("backlog_size"), lower_is_better=True)),
    ]
    out = ["| Metric | This period | vs. previous report |",
           "| --- | --- | --- |"]
    out += [f"| {label} | {value} | {change} |" for label, value, change in rows]
    if not f["prior"]:
        out.append("")
        out.append("_No previous report to compare against; this is the first in the series._")
    return "\n".join(out)


def _shipped(f):
    """The batch, grouped by epic — the "what did I actually get done" section,
    and the one most likely to be read a year from now."""
    if not f["batch"]:
        return "_No cards closed this period._"
    groups: dict[str, list] = {}
    for card in f["batch"]:
        groups.setdefault(card["epic_name"] or "(no epic)", []).append(card)
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    out = []
    for epic, cards in ordered:
        out.append(f"**{epic}** — {len(cards)} card{'s' if len(cards) != 1 else ''}")
        out.append("")
        for card in cards:
            bits = [card["record_type"].title(),
                    card["assignee"] or "unassigned",
                    _days(card["lead_days"])]
            if card["comments"]:
                bits.append(f"{card['comments']} comment"
                            f"{'s' if card['comments'] != 1 else ''}")
            out.append(f"- **#{card['id']}** {_escape(card['title'])}  \n"
                       f"  _{' · '.join(bits)}_")
        out.append("")
    return "\n".join(out).rstrip()


def _delivery_profile(f):
    lead = f["lead_time"]
    if not lead["n"]:
        return "_No card in this batch carried both a creation and a close timestamp._"
    biggest = max((b["count"] for b in lead["distribution"]), default=0)
    out = [
        "How long each card took from being raised to being closed. Lead time "
        "includes every day a card sat waiting, so on a board with a deep "
        "backlog it measures patience as much as effort.",
        "",
        "```",
    ]
    width = max(len(b["label"]) for b in lead["distribution"])
    for bucket in lead["distribution"]:
        out.append(f"{bucket['label']:<{width}}  {_bar(bucket['count'], biggest)}  "
                   f"{bucket['count']}")
    out.append("```")
    out += [
        "",
        f"- **Median** {_days(lead['median'])} — the typical card.",
        f"- **85th percentile** {_days(lead['p85'])} — what you could honestly "
        "promise, since completion times skew long.",
        f"- **Range** {_days(lead['min'])} to {_days(lead['max'])}.",
    ]

    cycle = f["cycle_time"]
    if cycle["n"]:
        out += [
            "",
            f"**Cycle time** (from first entering Doing) is available for "
            f"{cycle['n']} of {f['throughput']['count']} cards: median "
            f"{_days(cycle['median'])}, 85th percentile {_days(cycle['p85'])}.",
        ]
        if f["flow_efficiency"]["median"] is not None:
            out.append(
                f"Flow efficiency — time working over time elapsed — has a median "
                f"of {_pct(f['flow_efficiency']['median'])}. Anything under about "
                "15% means cards spend most of their life waiting, which is "
                "normal and worth knowing rather than worth fixing."
            )
    else:
        out += [
            "",
            "**Cycle time is not available for this batch.** It needs the moment a "
            "card entered Doing, which the board only began recording with the "
            "transition log. Cards that move through Doing from now on will carry "
            "it, and this section will fill in on its own.",
        ]
    return "\n".join(out)


def _flow_health(f):
    out = []
    wip = f["wip"]
    if wip:
        out += [
            "Cards still in Doing, oldest first. Work-item age is the one delivery "
            "metric you can act on while there is still time — unlike lead time, "
            "which you only learn once the card is already finished.",
            "",
            "| Card | Age | In Doing | Owner | Priority |",
            "| --- | --- | --- | --- | --- |",
        ]
        for card in sorted(wip, key=lambda w: -(w["age_days"] or 0)):
            out.append(
                f"| **#{card['id']}** {_truncate(card['title'], 46)} "
                f"| {_days(card['age_days'], 0)} "
                f"| {_days(card['doing_days'], 0) if card['doing_days'] is not None else 'not recorded'} "
                f"| {card['assignee']} | {card['priority']} |"
            )
    else:
        out.append("Nothing is in Doing. The board is between pushes.")

    queue, backlog = f["queue"], f["backlog"]
    out.append("")
    out.append(f"**Queue** — {queue['size']} card"
               f"{'s' if queue['size'] != 1 else ''} in Todo"
               + (f", median age {_days(queue['median_age_days'], 0)}"
                  if queue["median_age_days"] is not None else "") + ".")
    rate = f["throughput"]["per_week"]
    if rate and queue["size"]:
        out.append(f"  At this period's rate of {rate:.1f} cards a week, the current "
                   f"queue would drain in about {queue['size'] / rate:.1f} weeks.")

    out.append("")
    line = f"**Backlog** — {backlog['size']} card{'s' if backlog['size'] != 1 else ''}"
    if backlog["median_age_days"] is not None:
        line += f", median age {_days(backlog['median_age_days'], 0)}"
    if backlog["oldest_days"] is not None:
        line += f", oldest {_days(backlog['oldest_days'], 0)}"
    out.append(line + ".")
    if backlog["stale_count"]:
        out.append(f"  {backlog['stale_count']} of them "
                   f"({_pct(backlog['stale_share'])}) have not been touched in 30 days.")

    trailing = f["throughput"]["trailing_weeks"]
    if any(trailing):
        biggest = max(trailing)
        out += ["", "**Cards closed per week**, trailing eight weeks (oldest first):",
                "", "```"]
        for index, count in enumerate(trailing):
            label = "this week" if index == len(trailing) - 1 else f"-{len(trailing) - 1 - index}w"
            out.append(f"{label:>10}  {_bar(count, biggest)}  {count}")
        out.append("```")
        out.append("")
        out.append("_Counts every card closed, including those archived in earlier "
                   "periods, so it reads across reports rather than within one._")
    return "\n".join(out)


def _composition(f):
    out = ["**By owner**", ""]
    biggest = max((row["count"] for row in f["by_assignee"]), default=0)
    for row in f["by_assignee"]:
        out.append(f"- `{_bar(row['count'], biggest, 16)}` **{row['name']}** — "
                   f"{row['count']} ({_pct(row['share'])})")

    out += ["", "**By originator**", ""]
    biggest = max((row["count"] for row in f["by_reporter"]), default=0)
    for row in f["by_reporter"]:
        out.append(f"- `{_bar(row['count'], biggest, 16)}` **{row['name']}** — "
                   f"{row['count']} ({_pct(row['share'])})")

    mix = f["mix"]
    out += ["", f"**Record type** — {mix['build']} Build"
            f"{'s' if mix['build'] != 1 else ''}, {mix['fix']} Fix"
            f"{'es' if mix['fix'] != 1 else ''} ({_pct(mix['fix_ratio'])} rework)."]

    discussion = f["discussion"]
    line = (f"**Discussion** — {discussion['total']} comment"
            f"{'s' if discussion['total'] != 1 else ''} across the batch; "
            f"{discussion['silent']} card"
            f"{'s' if discussion['silent'] != 1 else ''} closed with none.")
    out += ["", line]
    most = discussion["most_discussed"]
    if most and most["comments"]:
        out.append(f"  Most discussed: **#{most['id']}** {_escape(most['title'])} "
                   f"({most['comments']}).")
    return "\n".join(out)


def _signals_section(f):
    if not f["signals"]:
        return "_No findings. Nothing in this period crossed a threshold worth flagging._"
    labels = {"attention": "Attention", "watch": "Worth noting"}
    out = []
    for index, signal in enumerate(f["signals"], start=1):
        out += [
            f"**{index}. {signal['title']}** — {labels.get(signal['severity'], 'Note')}",
            "",
            f"{signal['detail']}",
            "",
            f"_What to do:_ {signal['action']}",
            "",
        ]
    return "\n".join(out).rstrip()


def _data_quality(f):
    quality = f["data_quality"]
    n = f["throughput"]["count"]
    out = [
        "What this report could and could not measure, so the numbers above can "
        "be read at the right confidence.",
        "",
    ]
    if quality["has_event_log"]:
        coverage = f["cycle_time"]["coverage"]
        out.append(f"- **Transition log** present. Cycle time covered "
                   f"{_pct(coverage)} of the batch.")
    else:
        out.append("- **Transition log** absent — lead time only.")
    sized = max(quality["estimates_used"], quality["story_points_used"])
    out.append(f"- **Estimates** on {quality['estimates_used']} of {n} cards; "
               f"**story points** on {quality['story_points_used']}. "
               + ("Too sparse to compute velocity or forecast accuracy from."
                  if not n or sized / n < SIZING_COVERAGE_FLOOR
                  else "Dense enough to reason about sizing."))
    if quality["missing_closed_at"]:
        out.append(f"- {quality['missing_closed_at']} card(s) had no close "
                   "timestamp; their updated_at was used instead.")
    if quality["missing_created_at"]:
        out.append(f"- {quality['missing_created_at']} card(s) had no creation "
                   "timestamp and are excluded from every duration.")
    if quality["instant_closes"]:
        out.append(f"- {quality['instant_closes']} card(s) were created and closed "
                   "within an hour — logged after the fact, so they pull the "
                   "median down without representing any forecastable work.")
    groups = f["batch_close_groups"]
    if groups:
        out.append(f"- {sum(len(g) for g in groups)} card(s) across "
                   f"{len(groups)} group(s) share a close timestamp, meaning they "
                   "were closed in bulk. Their individual durations are "
                   "approximate.")
    return "\n".join(out)


def _ledger(f):
    if not f["batch"]:
        return "_Nothing archived._"
    out = ["| # | Card | Type | Owner | Raised | Closed | Lead | Cycle |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for card in sorted(f["batch"], key=lambda c: c["id"]):
        out.append(
            f"| {card['id']} | {_truncate(card['title'], 52)} "
            f"| {card['record_type']} | {card['assignee'] or '—'} "
            f"| {_date(card['created_at'])} | {_date(card['closed_effective'])} "
            f"| {_days(card['lead_days'])} | {_days(card['cycle_days'])} |"
        )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def render(f, slug, previous_slug=None, source_note=None):
    """Return the full Markdown note for one report."""
    header = (
        f'_Period **{_date(f["period_start"])} → {_date(f["period_end"])}** '
        f'({f["period_days"]:.0f} days) · '
        f'{f["throughput"]["count"]} card'
        f'{"s" if f["throughput"]["count"] != 1 else ""} archived._'
    )
    if previous_slug:
        header += f"\n\n← [[{previous_slug}|Previous report]] · [[_index|All reports]]"
    else:
        header += "\n\n[[_index|All reports]]"

    sections = [
        _frontmatter(f, slug, previous_slug),
        "",
        f'# Bristol Report — {_date(f["generated_at"])}',
        "",
        header,
        "",
        "#### Executive Summary",
        "",
        _summary(f),
        "",
        "---",
        "",
        "#### Headline Metrics",
        "",
        _headline_table(f),
        "",
        "#### What Shipped",
        "",
        _shipped(f),
        "",
        "#### Delivery Profile",
        "",
        _delivery_profile(f),
        "",
        "#### Flow Health",
        "",
        _flow_health(f),
        "",
        "#### Composition",
        "",
        _composition(f),
        "",
        "#### Signals",
        "",
        _signals_section(f),
        "",
        "#### Data Quality",
        "",
        _data_quality(f),
        "",
        "#### Ledger",
        "",
        _ledger(f),
        "",
        "---",
        "",
        f"*Generated automatically by [[bristol_tickets_app|Bristol]]'s Clear Done, "
        f"from the [[agent_system|agent_system]] roadmap board. "
        f"Source: `{source_note or 'src/tools/bristol/reports/'}`. "
        f"Workspace map: [[ai_workspace_hub|AI Workspace Hub]].*",
        "",
    ]
    return "\n".join(sections)


def render_index():
    """The folder's index note: Dataview tables over every report's
    frontmatter. This is where the per-report numbers become a trend — the
    reason every headline metric is duplicated into YAML. Static content: the
    queries do the reading, so the file never needs to know what reports exist.
    """
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    return f"""---
created: {generated}
tags:
  - bristol/report
type: bristol-report-index
---

# Bristol Reports

_One report per Clear Done. Each measures the batch of cards that left the
board, against the board's health at that moment. Written automatically; see
[[bristol_tickets_app|Bristol]] and the [[ai_workspace_hub|AI Workspace Hub]]._

#### Trend

```dataview
TABLE
  period_start AS "From",
  period_end AS "To",
  cards_closed AS "Closed",
  throughput_per_week AS "Per week",
  lead_time_median_days AS "Lead (med)",
  lead_time_p85_days AS "Lead (p85)",
  cycle_time_median_days AS "Cycle (med)",
  fix_ratio AS "Fix %",
  signals_attention AS "⚠"
FROM #bristol/report
WHERE type = "bristol-report"
SORT date DESC
```

#### Open findings, most recent report

```dataview
LIST
FROM #bristol/report
WHERE type = "bristol-report" AND signals_attention > 0
SORT date DESC
LIMIT 5
```

#### Board load over time

```dataview
TABLE
  wip_count AS "In progress",
  wip_oldest_days AS "Oldest WIP (d)",
  queue_size AS "Queued",
  backlog_size AS "Backlog",
  backlog_oldest_days AS "Oldest backlog (d)"
FROM #bristol/report
WHERE type = "bristol-report"
SORT date DESC
```

---
*Rebuilt automatically whenever a report is written. Edits to this file are
overwritten; change `render_index` in `src/tools/bristol/reports/render.py`
instead.*
"""
