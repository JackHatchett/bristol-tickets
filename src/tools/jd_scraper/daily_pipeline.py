#!/usr/bin/env python3
"""
daily_pipeline.py
Career-coach pipeline orchestrator. This is the entry point for the cron job.

What this does:
  1. Runs gmail_harvest.py to pull job alert emails into
     applications/pipeline/job_feed.json.
  2. Runs jd_scraper.py to fetch JD text for Playwright-eligible sources.
  3. Writes a .pipeline_ready marker so the morning briefing (scheduled task
     in Cowork) knows the harvest is complete and can start triage.
  4. Logs everything to applications/pipeline/logs/pipeline.log.

What this does NOT do:
  - Triage, fit analysis, cover letters. Those are the coach's job.
  - LinkedIn JD fetching (that uses the Chrome extension recipe inside Cowork).
  - Application submissions (never automated).

Cron entry (6:00 AM daily, adjust path to match your Python install and this
agent's provisioned tools/data root, e.g. $CAREER_COACH_DIR):
  0 6 * * * /usr/local/bin/python3 $CAREER_COACH_DIR/tools/daily_pipeline.py >> $CAREER_COACH_DIR/applications/pipeline/logs/cron_output.log 2>&1

macOS launchd alternative: see README.md.

Run manually:
  python3 tools/daily_pipeline.py
"""

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

_env = os.environ.get("CAREER_COACH_DIR")
if not _env:
    sys.exit(
        "daily_pipeline: ERROR -- set CAREER_COACH_DIR to this agent's "
        "provisioned data root before running (see setup_cron.sh / README.md)"
    )
BASE_DIR = Path(_env)
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"


def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)


def log(message, log_path):
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_script(script_name, log_path):
    script_path = BASE_DIR / "tools" / script_name
    if not script_path.exists():
        log(f"ERROR: Script not found: {script_path}", log_path)
        return False

    log(f"Running {script_name}...", log_path)
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                log(f"  [stdout] {line}", log_path)
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                log(f"  [stderr] {line}", log_path)
        if result.returncode != 0:
            log(
                f"ERROR: {script_name} exited with code {result.returncode}.",
                log_path,
            )
            return False
        log(f"OK: {script_name} completed.", log_path)
        return True
    except Exception as e:
        log(f"EXCEPTION running {script_name}: {e}", log_path)
        return False


def write_ready_marker(settings, log_path, new_count, pending_chrome, pending_manual):
    """
    Write a small JSON marker file that the Cowork morning briefing can read
    to confirm the pipeline ran and learn what needs coach attention.
    """
    marker_path = (
        Path(settings["paths"]["project_root"]).expanduser()
        / settings["paths"]["ready_marker"]
    )
    payload = {
        "pipeline_date": datetime.date.today().isoformat(),
        "pipeline_ran_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "new_jobs_harvested": new_count,
        "pending_chrome_extension": pending_chrome,
        "pending_manual_paste": pending_manual,
        "feed_path": settings["paths"]["job_feed"],
    }
    with open(marker_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    log(f"Ready marker written to {marker_path}.", log_path)


def count_feed_stats(settings):
    """Return (total_pending, pending_chrome, pending_manual) from job_feed.json."""
    feed_path = (
        Path(settings["paths"]["project_root"]).expanduser()
        / settings["paths"]["job_feed"]
    )
    if not feed_path.exists():
        return 0, 0, 0
    try:
        with open(feed_path, "r", encoding="utf-8") as f:
            feed = json.load(f)
    except Exception:
        return 0, 0, 0

    pending_total = sum(
        1 for j in feed if j.get("triage_status") == "pending"
    )
    pending_chrome = sum(
        1 for j in feed if j.get("jd_fetch_status") == "pending_chrome_extension"
    )
    pending_manual = sum(
        1 for j in feed if j.get("jd_fetch_status") == "pending_manual"
    )
    return pending_total, pending_chrome, pending_manual


def main():
    settings = load_settings()
    log_path = (
        Path(settings["paths"]["project_root"]).expanduser()
        / settings["paths"]["pipeline_log"]
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log("=== career-coach daily pipeline starting ===", log_path)

    # Step 1: Gmail harvest
    ok_harvest = run_script("gmail_harvest.py", log_path)
    if not ok_harvest:
        log("Harvest failed. Aborting pipeline.", log_path)
        return

    # Step 2: Playwright JD scraping (Lever, Workday, Ashby, Greenhouse)
    ok_scrape = run_script("jd_scraper.py", log_path)
    if not ok_scrape:
        log(
            "Scraper failed or had errors. Continuing to write ready marker anyway.",
            log_path,
        )

    # Step 3: Write ready marker for the Cowork morning briefing
    pending_total, pending_chrome, pending_manual = count_feed_stats(settings)
    write_ready_marker(
        settings, log_path, pending_total, pending_chrome, pending_manual
    )

    log(
        f"=== Pipeline complete. "
        f"Jobs pending triage: {pending_total} "
        f"(Chrome extension: {pending_chrome}, manual paste: {pending_manual}) ===",
        log_path,
    )


if __name__ == "__main__":
    main()
