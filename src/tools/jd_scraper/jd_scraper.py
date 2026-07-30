#!/usr/bin/env python3
"""
jd_scraper.py
Part of the career-coach local pipeline (Tier 1 of the JD-acquisition
architecture — see README.md for the full tiering rationale).

WHAT THIS DOES:
  1. Reads applications/pipeline/job_feed.json (written by gmail_harvest.py).
  2. For each entry with jd_fetch_status == "pending_playwright", opens the URL
     in a local Playwright browser, extracts text, and saves to:
       applications/job_descriptions_raw/YYYY-MM-DD/[idx]_[company]_[role].txt    (text)
       applications/job_descriptions_raw/YYYY-MM-DD/[idx]_[company]_[role].png    (screenshot fallback)
  3. Updates job_feed.json with jd_file path and one of:
       jd_fetch_status = "fetched"      readable text extracted (>= 300 chars)
       jd_fetch_status = "screenshot"   text was thin; full-page PNG saved for coach vision
       jd_fetch_status = "fetch_failed" page errored or screenshot also failed

PERSISTENT BROWSER PROFILE:
  The scraper uses a persistent Chromium profile at config/browser_profile/.
  This means login sessions (FlexJobs, ZipRecruiter, etc.) survive across runs.
  ONE-TIME SETUP per site that requires a login:
    1. Edit config/settings.json: set playwright_headless to false.
    2. Run:  python3 tools/jd_scraper.py --login
       (a browser window will open with no jobs to scrape, but you can navigate
        to FlexJobs/ZipRecruiter and log in manually)
    3. See login_mode() below; it also auto-fills credentials.json if present.
    4. Set playwright_headless back to true when done.

ROUTING:
  playwright_hosts (settings.json): scrape with Playwright + screenshot fallback
  skip_hosts:                        LinkedIn only -- handled by the Chrome
                                     extension same-origin fetch recipe, run
                                     interactively by the coach (see README.md).
  Everything else:                   set pending_manual, skip.

INSTALL:
  pip install playwright requests --break-system-packages
  playwright install chromium

RUN:
  python3 tools/jd_scraper.py          # normal daily run
  python3 tools/jd_scraper.py --login  # headful browser for one-time site login
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_env = os.environ.get("CAREER_COACH_DIR")
if not _env:
    sys.exit(
        "jd_scraper: ERROR -- set CAREER_COACH_DIR to this agent's "
        "provisioned data root before running (see setup_cron.sh / README.md)"
    )
BASE_DIR = Path(_env)
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
BROWSER_PROFILE_DIR = BASE_DIR / "config" / "browser_profile"

# Minimum characters in extracted text before we fall back to screenshot.
_MIN_TEXT_LENGTH = 300


def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Redirect resolution
# ---------------------------------------------------------------------------

# Hosts that use tracking/redirect URLs that may resolve to a real ATS page.
# We try a plain HTTP HEAD request (no JS) to follow the chain before scraping.
_TRACKING_HOSTS = {
    "ziprecruiter.com",
    "www.ziprecruiter.com",
    "indeed.com",
    "www.indeed.com",
    "flexjobs.com",
    "www.flexjobs.com",
}

_REDIRECT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def resolve_redirect(url, timeout=10):
    """
    Follow HTTP redirects for known tracking URLs without loading a page in a browser.
    Returns (resolved_url, changed: bool).

    If the URL resolves to a different host, the caller can use the destination URL
    (often a real ATS host like greenhouse.io or lever.co) instead of the tracking URL.
    If the URL stays on the same host, or if the request fails, returns the original.
    """
    try:
        original_host = urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return url, False

    if not any(th in (urlparse(url).netloc.lower()) for th in _TRACKING_HOSTS):
        return url, False  # not a tracking host; skip

    try:
        resp = requests.head(
            url,
            headers=_REDIRECT_HEADERS,
            allow_redirects=True,
            timeout=timeout,
        )
        final_url = resp.url
        final_host = urlparse(final_url).netloc.lower().lstrip("www.")
        if final_host and final_host != original_host.lstrip("www."):
            return final_url, True
        return url, False
    except Exception as exc:
        # HEAD failed (Cloudflare blocks HEAD too sometimes). Try GET with stream=True
        # to avoid downloading the body but still follow redirects.
        try:
            resp = requests.get(
                url,
                headers=_REDIRECT_HEADERS,
                allow_redirects=True,
                timeout=timeout,
                stream=True,
            )
            resp.close()
            final_url = resp.url
            final_host = urlparse(final_url).netloc.lower().lstrip("www.")
            if final_host and final_host != original_host.lstrip("www."):
                return final_url, True
        except Exception:
            pass
        return url, False


# ---------------------------------------------------------------------------
# Filename utilities
# ---------------------------------------------------------------------------

def sanitize_filename(text, max_length=40):
    safe = re.sub(r"[^\w\-]", "_", str(text or ""))
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe[:max_length] if safe else "unknown"


def make_jd_filename(company, title, idx, ext="txt"):
    c = sanitize_filename(company or "unknown_company")
    t = sanitize_filename(title or "unknown_role")
    return f"{idx:03d}_{c}_{t}.{ext}"


# ---------------------------------------------------------------------------
# Page loading (shared by text and screenshot paths)
# ---------------------------------------------------------------------------

def _load_page(page, url, timeout_ms, scroll_wait_ms):
    """
    Navigate to url, wait for content, scroll to trigger lazy loading.
    Raises on hard failure. Returns nothing (mutates page state).
    """
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        # Many SPAs never reach networkidle. Fall back to domcontentloaded + fixed wait.
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(scroll_wait_ms * 2)
        except Exception as exc:
            raise RuntimeError(f"Page load failed for {url}: {exc}") from exc

    page.wait_for_timeout(scroll_wait_ms)

    # Scroll to bottom to trigger lazy-loading / reveal full JD text
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(scroll_wait_ms)
    except Exception:
        pass  # non-fatal


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

# Ordered selector lists per ATS host substring -> tries each until >= _MIN_TEXT_LENGTH
_ATS_SELECTORS = {
    "greenhouse.io": ["#app_body", ".job__description", "article", "main", "body"],
    "lever.co":      [".content", ".posting-content", "main", "body"],
    "workday":       ["[data-automation-id='jobPostingDescription']", ".job-description", "main", "body"],
    "myworkdayjobs": ["[data-automation-id='jobPostingDescription']", ".job-description", "main", "body"],
    "ashbyhq.com":   [".job-description", "main", "body"],
    # Generic fallback for Indeed, ZipRecruiter, FlexJobs, and anything else
    "_default":      ["main", "article", "#job-description", ".job-description",
                      "[data-testid='jobsearch-JobComponent']", ".jobsearch-JobComponent",
                      "body"],
}


def extract_text(page, url):
    """
    Try site-specific selectors first, then fall back to body.
    Returns the best text found (may be short -- caller checks length).
    """
    host = url.split("/")[2].lower() if "//" in url else ""

    selector_list = _ATS_SELECTORS["_default"]
    for key, selectors in _ATS_SELECTORS.items():
        if key != "_default" and key in host:
            selector_list = selectors
            break

    best = ""
    for selector in selector_list:
        try:
            candidate = page.inner_text(selector)
            if len(candidate.strip()) > len(best.strip()):
                best = candidate
            if len(best.strip()) >= _MIN_TEXT_LENGTH:
                break
        except Exception:
            continue

    # Whitespace normalization
    best = re.sub(r"[ \t]+", " ", best)
    best = re.sub(r"\n[ \t]*", "\n", best)
    best = re.sub(r"\n{3,}", "\n\n", best)
    return best.strip()


# ---------------------------------------------------------------------------
# Screenshot fallback
# ---------------------------------------------------------------------------

def take_screenshot(page, path):
    """
    Full-page screenshot saved to path (PNG).
    Returns True on success.
    """
    try:
        page.screenshot(path=str(path), full_page=True)
        return True
    except Exception as exc:
        print(f"  Screenshot failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Single-job scrape (text + screenshot fallback)
# ---------------------------------------------------------------------------

def scrape_job(page, job, jd_dir, idx, settings):
    """
    Scrape one job. Returns (jd_file_path_or_None, status_string).

    status values:
      "fetched"      text extracted successfully
      "screenshot"   PNG saved; coach reads it with vision
      "fetch_failed" everything failed
    """
    url = job.get("canonical_url", "")
    company = job.get("company", "")
    title = job.get("title", "")
    timeout_ms = int(settings["scraper"]["network_idle_timeout_ms"])
    scroll_wait_ms = int(settings["scraper"]["scroll_wait_ms"])

    try:
        _load_page(page, url, timeout_ms, scroll_wait_ms)
    except RuntimeError as exc:
        print(f"  Load error: {exc}")
        return None, "fetch_failed"

    # --- Attempt 1: text extraction ---
    text = extract_text(page, url)

    if len(text) >= _MIN_TEXT_LENGTH:
        filename = make_jd_filename(company, title, idx, ext="txt")
        jd_file = jd_dir / filename
        today = datetime.date.today().isoformat()
        with open(jd_file, "w", encoding="utf-8") as f:
            f.write(f"SOURCE: {job.get('source', 'unknown')}\n")
            f.write(f"URL: {url}\n")
            f.write(f"DATE: {today}\n")
            f.write(f"COMPANY: {company}\n")
            f.write(f"TITLE: {title}\n")
            f.write("---\n\n")
            f.write(text)
        print(f"  Text extracted ({len(text)} chars) -> {jd_file.name}")
        return str(jd_file), "fetched"

    # --- Attempt 2: full-page screenshot ---
    print(f"  Text too short ({len(text)} chars). Taking full-page screenshot...")
    filename = make_jd_filename(company, title, idx, ext="png")
    png_file = jd_dir / filename
    if take_screenshot(page, png_file):
        print(f"  Screenshot saved -> {png_file.name}")
        return str(png_file), "screenshot"

    # --- Both failed ---
    print(f"  Screenshot also failed. Marking fetch_failed.")
    return None, "fetch_failed"


# ---------------------------------------------------------------------------
# Feed I/O
# ---------------------------------------------------------------------------

def read_feed(feed_path):
    with open(feed_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_feed(feed, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Host routing
# ---------------------------------------------------------------------------

def classify_host(url, playwright_hosts, skip_hosts):
    """Returns 'playwright', 'skip_linkedin', 'skip_manual'."""
    try:
        host = url.split("/")[2].lower()
    except IndexError:
        return "skip_manual"

    for h in skip_hosts:
        if h in host:
            return "skip_linkedin"

    for h in playwright_hosts:
        if h in host:
            return "playwright"

    return "skip_manual"


# ---------------------------------------------------------------------------
# Login mode helper
# ---------------------------------------------------------------------------

def login_mode(settings):
    """
    Open a headful browser with the persistent profile so you can log in to
    ZipRecruiter, FlexJobs, Indeed, or any other site that requires auth.

    If config/credentials.json exists, credentials are auto-filled where supported.
    Cookies are saved automatically to config/browser_profile/ when you close.

    credentials.json format (create this file manually; it is gitignored):
      {
        "ziprecruiter": { "username": "your@email.com", "password": "yourpassword" },
        "flexjobs":     { "username": "your@email.com", "password": "yourpassword" },
        "indeed":       { "username": "your@email.com", "password": "yourpassword" }
      }
    """
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    # Load credentials if available
    creds_file = BASE_DIR / "config" / "credentials.json"
    creds = {}
    if creds_file.exists():
        with open(creds_file) as f:
            creds = json.load(f) or {}
        print(f"Credentials loaded for: {', '.join(k for k in creds.keys() if not k.startswith('_'))}")
    else:
        print(f"No credentials file found at {creds_file}.")
        print("You can create it to enable auto-fill (see --login docstring).")
        print("Or just log in manually in the browser.")

    # Sites to log into, in order
    login_sites = [
        {
            "name": "ZipRecruiter",
            "url": "https://www.ziprecruiter.com/login",
            "cred_key": "ziprecruiter",
            "email_selector": "input[name='email'], input[type='email']",
            "password_selector": "input[name='password'], input[type='password']",
            "submit_selector": "button[type='submit']",
        },
        {
            "name": "FlexJobs",
            "url": "https://www.flexjobs.com/login",
            "cred_key": "flexjobs",
            "email_selector": "input[name='email'], input[type='email'], #email",
            "password_selector": "input[name='password'], input[type='password'], #password",
            "submit_selector": "button[type='submit'], input[type='submit']",
        },
        {
            "name": "Indeed",
            "url": "https://secure.indeed.com/auth",
            "cred_key": "indeed",
            "email_selector": "input[name='__email'], input[type='email']",
            "password_selector": "input[name='__password'], input[type='password']",
            "submit_selector": "button[type='submit']",
        },
    ]

    print("\nOpening browser with persistent profile...")
    print("For each site: credentials will be auto-filled if available.")
    print("Solve any CAPTCHA or 2FA manually, then wait for the page to load.")
    print("Close the browser window when done with all sites.\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.pages[0] if context.pages else context.new_page()

        for site in login_sites:
            name = site["name"]
            site_creds = creds.get(site["cred_key"], {})

            print(f"Opening {name}...")
            try:
                page.goto(site["url"], wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(2000)
            except Exception as exc:
                print(f"  Could not load {name} login page: {exc}")
                continue

            if site_creds.get("username") and site_creds.get("password"):
                print(f"  Auto-filling credentials for {name}...")
                try:
                    # Try each selector variant
                    for sel in site["email_selector"].split(", "):
                        try:
                            page.fill(sel.strip(), site_creds["username"])
                            break
                        except Exception:
                            continue
                    page.wait_for_timeout(500)
                    for sel in site["password_selector"].split(", "):
                        try:
                            page.fill(sel.strip(), site_creds["password"])
                            break
                        except Exception:
                            continue
                    page.wait_for_timeout(500)
                    print(f"  Credentials filled. Solve any CAPTCHA/2FA, then wait for login.")
                    print(f"  (NOT auto-submitting -- you control when to click Sign In.)")
                except Exception as exc:
                    print(f"  Auto-fill failed ({exc}). Log in manually.")
            else:
                print(f"  No credentials for {name}. Log in manually.")

            # Pause so the user can complete login before we move to next site
            print(f"  Press ENTER in this terminal when logged in and ready to continue...")
            input()

        print("\nAll sites done. Close the browser window to save cookies.")
        print("Waiting for browser to close...")
        try:
            # Keep context alive until user closes the window
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass

    print("Login mode done. Session cookies saved to config/browser_profile/.")
    print("Future scraper runs will use these cookies automatically.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="JD scraper for career-coach pipeline")
    parser.add_argument(
        "--login", action="store_true",
        help="Open headful browser for one-time site login. Run this once per site."
    )
    args = parser.parse_args()

    settings = load_settings()

    if args.login:
        login_mode(settings)
        return

    project_root = Path(settings["paths"]["project_root"]).expanduser()
    feed_path = project_root / settings["paths"]["job_feed"]
    jd_base = project_root / settings["paths"]["job_descriptions_base"]
    today = datetime.date.today().isoformat()
    jd_dir = jd_base / today
    jd_dir.mkdir(parents=True, exist_ok=True)
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    playwright_hosts = settings["scraper"]["playwright_hosts"]
    skip_hosts = settings["scraper"]["skip_hosts"]
    headless = bool(settings["pipeline"].get("playwright_headless", True))

    if not feed_path.exists():
        print(f"No job feed at {feed_path}. Run gmail_harvest.py first.")
        return

    feed = read_feed(feed_path)
    feed_by_id = {j["id"]: j for j in feed}

    # Classify and update status for entries still sitting at pending_playwright
    # Also handle entries that are pending_manual/unknown host routing on re-run:
    # we re-check routing in case settings.json changed.
    for job in feed:
        if job.get("jd_fetch_status") in ("fetched", "screenshot"):
            continue  # already done
        if job.get("jd_file"):
            continue  # already has a file

        url = job.get("canonical_url", "")
        route = classify_host(url, playwright_hosts, skip_hosts)

        if route == "skip_linkedin":
            if job.get("jd_fetch_status") != "pending_chrome_extension":
                job["jd_fetch_status"] = "pending_chrome_extension"
        elif route == "playwright":
            if job.get("jd_fetch_status") not in ("pending_playwright", "fetch_failed"):
                job["jd_fetch_status"] = "pending_playwright"
        else:
            if job.get("jd_fetch_status") not in ("pending_manual",):
                job["jd_fetch_status"] = "pending_manual"

    to_scrape = [
        j for j in feed
        if j.get("jd_fetch_status") in ("pending_playwright", "fetch_failed")
        and not j.get("jd_file")
    ]

    counts = {s: sum(1 for j in feed if j.get("jd_fetch_status") == s) for s in
              ("fetched", "screenshot", "pending_playwright", "pending_chrome_extension",
               "pending_manual", "fetch_failed")}

    print(f"Feed: {len(feed)} total entries")
    print(f"  fetched/screenshot:        {counts['fetched'] + counts['screenshot']}")
    print(f"  to scrape (Playwright):    {len(to_scrape)}")
    print(f"  pending Chrome extension:  {counts['pending_chrome_extension']}  (LinkedIn; coach handles)")
    print(f"  pending manual:            {counts['pending_manual']}")
    print(f"  fetch_failed (prior):      {counts['fetch_failed']}")

    if not to_scrape:
        print("\nNothing to scrape. Exiting.")
        write_feed(list(feed_by_id.values()), feed_path)
        return

    print(f"\nLaunching browser (headless={headless}, profile=config/browser_profile/)...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.pages[0] if context.pages else context.new_page()

        for idx, job in enumerate(to_scrape, start=1):
            job_id = job["id"]
            url = job.get("canonical_url", "")
            print(f"\n[{idx}/{len(to_scrape)}] {job.get('title', '(no title)')[:80]}")
            print(f"  {url[:100]}")

            # Attempt to resolve tracking URLs (ZipRecruiter /km/, Indeed, etc.)
            # before loading in Playwright. If the URL redirects to a real ATS host
            # (Greenhouse, Lever, Workday, etc.) we get clean text without Cloudflare.
            resolved_url, redirected = resolve_redirect(url)
            if redirected:
                new_host = urlparse(resolved_url).netloc.lower()
                print(f"  Redirect resolved -> {new_host}: {resolved_url[:90]}")
                job["canonical_url"] = resolved_url
                job["ats_host"] = new_host
                url = resolved_url
                # Re-classify: the new host might be a playwright_host we already handle well
                new_route = classify_host(url, playwright_hosts, skip_hosts)
                if new_route == "skip_linkedin":
                    job["jd_fetch_status"] = "pending_chrome_extension"
                    feed_by_id[job_id] = job
                    print(f"  Resolved to LinkedIn -- marking pending_chrome_extension.")
                    continue
            else:
                new_host = urlparse(url).netloc.lower()
                if any(th in new_host for th in _TRACKING_HOSTS):
                    print(f"  Redirect unresolved; still on {new_host}. Trying with persistent session...")
                    # Fall through to Playwright. If config/browser_profile/ has a
                    # valid login session for this site, Cloudflare passes. If not,
                    # the screenshot captures whatever rendered (including a login wall)
                    # and status = "screenshot". Run --login to set up the session.

            jd_file, status = scrape_job(page, job, jd_dir, idx, settings)

            feed_by_id[job_id]["jd_fetch_status"] = status
            feed_by_id[job_id]["jd_file"] = jd_file

            time.sleep(1.5)  # polite rate limit

        context.close()

    write_feed(list(feed_by_id.values()), feed_path)
    print(f"\nDone. Updated {feed_path}.")

    # Summary
    final_feed = list(feed_by_id.values())
    ok = sum(1 for j in final_feed if j.get("jd_fetch_status") in ("fetched", "screenshot"))
    failed = sum(1 for j in final_feed if j.get("jd_fetch_status") == "fetch_failed")
    manual = sum(1 for j in final_feed if j.get("jd_fetch_status") == "pending_manual")
    chrome = sum(1 for j in final_feed if j.get("jd_fetch_status") == "pending_chrome_extension")
    print(f"Result: {ok} fetched/screenshot, {failed} failed, {manual} pending manual, {chrome} pending Chrome extension")


if __name__ == "__main__":
    main()
