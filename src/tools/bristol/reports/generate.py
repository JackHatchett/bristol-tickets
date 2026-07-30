"""generate.py — orchestration and CLI for the Bristol report.

`generate_report` is the single entry point, used identically by Bristol's
Clear Done button, an agent session, and (eventually) the Python head.

PERIOD BOUNDARIES
-----------------
A period runs from the end of the last report to now. That boundary is read
back out of the previous report's own frontmatter rather than stored anywhere,
which keeps the whole feature free of a second state store — the repo's
standing rule is that roadmap.db is the only place state lives, and a report is
an artefact, not state. Delete the folder and the next report simply starts a
fresh series.

FAILURE POSTURE
---------------
Called from the Qt button, this must never be able to cost the user their Clear
Done. The sweep has already committed by the time we run; a missing notebook,
an unmounted iCloud folder or a bug in here returns a result object saying so
instead of raising. The CLI surfaces the same information as an exit code.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):  # allow `python3 generate.py` from the folder
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from reports import metrics, render as render_mod  # type: ignore
    from reports.paths import resolve_reports_dir  # type: ignore
else:
    from . import metrics
    from . import render as render_mod
    from .paths import resolve_reports_dir

FILENAME_PATTERN = "bristol_report_%Y-%m-%d_%H%M"
INDEX_NAME = "_index.md"
_FRONTMATTER_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


class ReportResult:
    """What happened, in a form both the GUI and the CLI can act on."""

    def __init__(self, written=None, skipped=None, error=None, facts=None):
        self.written = written      # Path, when a report was produced
        self.skipped = skipped      # str reason, when there was nothing to do
        self.error = error          # str, when something went wrong
        self.facts = facts

    @property
    def ok(self):
        return self.written is not None

    def __str__(self):
        if self.written:
            return f"wrote {self.written}"
        if self.skipped:
            return f"skipped: {self.skipped}"
        return f"failed: {self.error}"


# ---------------------------------------------------------------------------
# previous-report lookup
# ---------------------------------------------------------------------------

def _parse_frontmatter(text):
    """Read the leading `---` block as a flat dict, numbers coerced.

    A deliberately small parser rather than a PyYAML dependency: Bristol's only
    third-party requirement is PySide6, and adding one so a report can read its
    own predecessor would be a poor trade. We write this frontmatter ourselves,
    so its shape is known — flat scalars plus one list of tags, which we skip.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        match = _FRONTMATTER_LINE.match(line.strip())
        if not match:
            continue
        key, raw = match.group(1), match.group(2).strip()
        if raw in ("", "null"):
            out[key] = None
            continue
        try:
            out[key] = float(raw) if "." in raw else int(raw)
        except ValueError:
            out[key] = raw.strip('"').strip("'")
    return out


def _previous_report(reports_dir):
    """The most recent report note in the folder, as (slug, frontmatter)."""
    if reports_dir is None or not reports_dir.is_dir():
        return None, {}
    candidates = sorted(
        (p for p in reports_dir.glob("bristol_report_*.md") if p.is_file()),
        key=lambda p: p.name,
    )
    if not candidates:
        return None, {}
    latest = candidates[-1]
    try:
        return latest.stem, _parse_frontmatter(latest.read_text(encoding="utf-8"))
    except OSError:
        return latest.stem, {}


def _period_start(prior_frontmatter, batch_facts_fallback=None):
    """Where this period begins: the previous report's period_end, else None
    (metrics falls back to the batch's own earliest creation)."""
    value = (prior_frontmatter or {}).get("period_end")
    if not value:
        return batch_facts_fallback
    return f"{value}T00:00:00+00:00" if len(str(value)) == 10 else str(value)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def generate_report(conn, task_ids, out_dir=None, now=None, write_index=True):
    """Write one report for `task_ids` and return a ReportResult.

    `conn`      an open sqlite3 connection to roadmap.db.
    `task_ids`  the cards this period closed. Bristol passes exactly what Clear
                Done just swept; the CLI can pass a preview of the Done column.
    `out_dir`   overrides path resolution; normally left to the config.
    """
    try:
        task_ids = [int(t) for t in task_ids]
    except (TypeError, ValueError) as exc:
        return ReportResult(error=f"bad task ids: {exc}")

    if not task_ids:
        return ReportResult(skipped="no cards closed, nothing to report on")

    reports_dir = resolve_reports_dir(out_dir)
    if reports_dir is None:
        return ReportResult(
            skipped="no reports folder configured or reachable "
                    "(set markdown_notebook.reports_dir in config.local.json, "
                    "or the BRISTOL_REPORTS_DIR env var)")

    now = now or datetime.now(timezone.utc).isoformat()
    previous_slug, prior = _previous_report(reports_dir)

    try:
        facts = metrics.collect(
            conn, task_ids, now=now,
            period_start=_period_start(prior), prior=prior or None,
        )
    except sqlite3.Error as exc:
        return ReportResult(error=f"could not read the board: {exc}")

    stamp = metrics._parse_ts(now) or datetime.now(timezone.utc)
    slug = stamp.strftime(FILENAME_PATTERN)
    target = reports_dir / f"{slug}.md"
    # Two Clear Dones inside one minute would otherwise collide; keep both
    # rather than silently overwriting the earlier one.
    suffix = 2
    while target.exists():
        target = reports_dir / f"{slug}_{suffix}.md"
        suffix += 1
    slug = target.stem

    try:
        target.write_text(
            render_mod.render(facts, slug, previous_slug,
                              source_note="src/tools/bristol/reports/"),
            encoding="utf-8",
        )
    except OSError as exc:
        return ReportResult(error=f"could not write {target}: {exc}")

    if write_index:
        try:
            (reports_dir / INDEX_NAME).write_text(
                render_mod.render_index(), encoding="utf-8")
        except OSError:
            pass  # the report itself succeeded; the index is a convenience

    return ReportResult(written=target, facts=facts)


def generate_report_safe(conn, task_ids, **kwargs):
    """generate_report with a blanket guard, for the Qt button.

    The board write has already committed by the time this runs, so no failure
    here can corrupt anything — but an exception crossing back into the Qt slot
    would surface as a crash on an action the user experienced as successful.
    """
    try:
        return generate_report(conn, task_ids, **kwargs)
    except Exception as exc:  # noqa: BLE001 — see docstring
        return ReportResult(error=f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolve_db(explicit=None):
    if explicit:
        return Path(os.path.expanduser(explicit))
    env = os.environ.get("ROADMAP_DB")
    if env:
        return Path(os.path.expanduser(env))
    root = Path(__file__).resolve().parents[4]
    matches = list((root / "data").glob("*/roadmap/roadmap.db"))
    if not matches:
        sys.exit("bristol-report: no roadmap.db found under data/*/roadmap/")
    return matches[0]


def _select_ids(conn, args):
    if args.ids:
        return [int(part) for part in args.ids.replace(",", " ").split()]
    if args.last_batch:
        # The most recent close timestamp in the archive, plus everything that
        # shares it — i.e. the cards the last Clear Done swept together.
        row = conn.execute(
            "SELECT MAX(COALESCE(closed_at, updated_at)) FROM task WHERE stage='archive'"
        ).fetchone()
        if not row or not row[0]:
            return []
        return [r[0] for r in conn.execute(
            "SELECT id FROM task WHERE stage='archive' "
            "AND COALESCE(closed_at, updated_at) >= ?",
            (row[0][:19],),
        ).fetchall()]
    # Default: preview what the next Clear Done would sweep.
    return [r[0] for r in conn.execute(
        "SELECT id FROM task WHERE stage='active' AND status='done'").fetchall()]


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="bristol-report",
        description="Write the analytic report Bristol produces on Clear Done.")
    parser.add_argument("--db", default=None, help="path to roadmap.db")
    parser.add_argument("--out-dir", default=None,
                        help="override the notebook folder reports are written to")
    parser.add_argument("--ids", default=None,
                        help="comma/space separated task ids to report on")
    parser.add_argument("--last-batch", action="store_true",
                        help="report on the cards the last Clear Done swept")
    parser.add_argument("--stdout", action="store_true",
                        help="print the Markdown instead of writing a file")
    parser.add_argument("--no-index", action="store_true",
                        help="do not rewrite the folder's _index.md")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(_resolve_db(args.db))
    try:
        ids = _select_ids(conn, args)
        if not ids:
            print("bristol-report: nothing to report on "
                  "(Done column empty and no --ids given).")
            return 0
        if args.stdout:
            now = datetime.now(timezone.utc).isoformat()
            _, prior = _previous_report(resolve_reports_dir(args.out_dir))
            facts = metrics.collect(conn, ids, now=now,
                                    period_start=_period_start(prior),
                                    prior=prior or None)
            print(render_mod.render(facts, "bristol_report_preview", None,
                                    source_note="src/tools/bristol/reports/"))
            return 0
        result = generate_report(conn, ids, out_dir=args.out_dir,
                                 write_index=not args.no_index)
        print(f"bristol-report: {result}")
        return 0 if result.ok or result.skipped else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
