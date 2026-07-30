#!/usr/bin/env python3
"""
gmail_harvest.py
Part of the career-coach local pipeline (Tier 0 of the JD-acquisition
architecture — see README.md for the full tiering rationale).

What this does:
  - Connects to Gmail via the Gmail API (OAuth, read-only).
  - Searches for job-alert emails from the past N days (configurable in settings.json).
  - Parses each email to extract: title, company, location, source, and canonical URL.
  - Follows redirect URLs to identify the actual ATS host (Greenhouse, Lever, Workday, etc.).
  - Deduplicates against the applications tracker CSV so already-tracked jobs are skipped.
  - Writes structured output to applications/pipeline/job_feed.json.

What this does NOT do:
  - It does not scrape job boards. That is jd_scraper.py's job.
  - It does not try to extract full JD text. The scraper does that.
  - It does not touch LinkedIn/Indeed job pages (just their alert emails).

Output schema (one object per job in job_feed.json):
  {
    "id": "linkedin_1234567890",         # source + job_id or hash
    "title": "Example Job Title",
    "company": "Example Corp",
    "location": "Remote",
    "source": "linkedin",                # linkedin | indeed | ziprecruiter | flexjobs | greenhouse | lever | workday | ashby | unknown
    "canonical_url": "https://...",      # resolved after following redirects
    "ats_host": "linkedin.com",          # the domain of the canonical URL
    "email_snippet": "...",              # short excerpt from the alert email
    "email_date": "YYYY-MM-DD",
    "jd_file": null,                     # filled in by jd_scraper.py if text is fetched
    "jd_fetch_status": "pending_playwright" | "pending_chrome_extension" | "pending_manual" | "fetched" | "fetch_failed",
    "already_applied": false,
    "triage_status": "pending"           # pending | triaged | skip
  }

Run:
  python3 tools/gmail_harvest.py
  Or via daily_pipeline.py.
"""

import base64
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Google API client imports (pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_env = os.environ.get("CAREER_COACH_DIR")
if not _env:
    sys.exit(
        "gmail_harvest: ERROR -- set CAREER_COACH_DIR to this agent's "
        "provisioned data root before running (see setup_cron.sh / README.md)"
    )
BASE_DIR = Path(_env)
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"


def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Gmail authentication
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service(settings):
    creds_path = BASE_DIR / settings["gmail"]["credentials_file"]
    token_path = BASE_DIR / settings["gmail"]["token_file"]

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            # Opens a browser window for one-time OAuth. After approval, token is saved.
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Gmail search and message parsing
# ---------------------------------------------------------------------------

def search_messages(service, query, after_date_str):
    """Return list of message IDs matching the query, filtered to after_date."""
    full_query = f"{query} after:{after_date_str}"
    messages = []
    kwargs = {"userId": "me", "q": full_query}

    response = service.users().messages().list(**kwargs).execute()
    if "messages" in response:
        messages.extend(response["messages"])

    while "nextPageToken" in response:
        kwargs["pageToken"] = response["nextPageToken"]
        response = service.users().messages().list(**kwargs).execute()
        if "messages" in response:
            messages.extend(response["messages"])

    return [m["id"] for m in messages]


def get_message_parts(service, msg_id):
    """Fetch a message and return (sender, subject, date, body_text, body_html)."""
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="full")
        .execute()
    )
    headers = {
        h["name"].lower(): h["value"]
        for h in msg.get("payload", {}).get("headers", [])
    }
    sender = headers.get("from", "")
    subject = headers.get("subject", "")
    date_str = headers.get("date", "")

    # Parse email date to YYYY-MM-DD
    email_date = _parse_email_date(date_str)

    # Walk the MIME tree to collect text/plain and text/html parts
    plain_parts = []
    html_parts = []
    _walk_parts(msg.get("payload", {}), plain_parts, html_parts)

    body_plain = "\n\n".join(plain_parts)
    body_html = "\n\n".join(html_parts)

    return sender, subject, email_date, body_plain, body_html


def _parse_email_date(date_str):
    """Best-effort parse of an RFC 2822 date string to YYYY-MM-DD."""
    # Strip timezone name in parens if present, e.g. "(PDT)"
    date_str = re.sub(r"\s*\([^)]*\)\s*$", "", date_str).strip()
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
    ):
        try:
            return datetime.datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.date.today().isoformat()


def _walk_parts(part, plain_acc, html_acc):
    """Recursively walk MIME parts collecting decoded text."""
    mime = part.get("mimeType", "")
    data = part.get("body", {}).get("data")

    if data:
        decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        if mime == "text/plain":
            plain_acc.append(decoded)
        elif mime == "text/html":
            html_acc.append(decoded)

    for sub in part.get("parts", []):
        _walk_parts(sub, plain_acc, html_acc)


# ---------------------------------------------------------------------------
# URL extraction and redirect resolution
# ---------------------------------------------------------------------------

# Matches http/https URLs, stopping at whitespace, quotes, angle brackets, or common trailing punctuation
URL_PATTERN = re.compile(r"https?://[^\s\"'<>)\]]+")

# Domains whose URLs are almost always redirect/tracking wrappers
TRACKING_DOMAINS = {
    "click.indeed.com",
    "r.smartrecruiters.com",
    "tracking.tbe.taleo.net",
    "email.mail.linkedin.com",
    "email.linkedin.com",
    "lnkd.in",
    "go.ziprecruiter.com",
    "click.ziprecruiter.com",
}

# URL extensions and path patterns that indicate images, logos, or email infrastructure.
# These are never job posting links and should always be filtered out.
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"}
_INFRA_PATH_PATTERNS = [
    "/svc/fotomat/",   # ZipRecruiter company logo CDN
    "/img/",           # generic image paths (ZipRecruiter logo, etc.)
    "/static/",
    "/assets/",
    "/fonts/",
    "/pixel/",
    "track_open",
    "email_open",
    "open.gif",
    "unsubscribe",
    "optout",
    "opt-out",
    "manage-preferences",
    "email-preferences",
]
# Max number of candidate URLs to take from a single email message.
# 1 means each email contributes exactly one entry to the feed — the right default
# for single-job alert emails (LinkedIn, ZipRecruiter, Indeed). If you start
# receiving multi-job digest emails you want parsed individually, raise this and
# implement per-job HTML parsing in process_message() for that source.
_MAX_URLS_PER_MESSAGE = 1


def is_job_candidate_url(url):
    """
    Return True only if this URL could plausibly be a job posting link.
    Rejects images, logos, tracking pixels, unsubscribe links, and email chrome.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    path = parsed.path.lower()
    # Reject image file extensions
    if any(path.endswith(ext) for ext in _IMAGE_EXTENSIONS):
        return False
    # Reject known infrastructure / non-job paths
    if any(pat in path for pat in _INFRA_PATH_PATTERNS):
        return False
    # Reject bare domain (no meaningful path)
    if len(path.strip("/")) < 3:
        return False
    return True


def extract_urls_from_body(body_plain, body_html):
    """
    Extract unique job-candidate URLs from plain text and HTML bodies.
    Filters out images, logos, and email infrastructure links.
    Caps at _MAX_URLS_PER_MESSAGE to prevent digest emails from flooding the feed.
    """
    urls = []
    seen = set()
    for text in (body_plain, body_html):
        for url in URL_PATTERN.findall(text):
            url = url.rstrip(".,;:!?)")
            if url not in seen and is_job_candidate_url(url):
                seen.add(url)
                urls.append(url)
    return urls[:_MAX_URLS_PER_MESSAGE]


def resolve_redirect(url, timeout=8):
    """
    Follow HTTP redirects to get the final canonical URL.
    Uses urllib (no external dependencies beyond stdlib).
    Returns the final URL, or the original if resolution fails.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        # opener that follows redirects up to 10 hops
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        with opener.open(req, timeout=timeout) as response:
            return response.url
    except Exception:
        return url


def classify_url(url):
    """
    Given a canonical URL, return (ats_host, source_label, job_id_or_none).

    source_label is used for routing in jd_scraper.py.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return url, "unknown", None

    host = parsed.netloc.lower().lstrip("www.")
    path = parsed.path

    if "linkedin.com" in host:
        # Extract jobId from ?currentJobId= or /jobs/view/{id}/
        job_id = _extract_linkedin_job_id(url)
        return host, "linkedin", job_id

    if "greenhouse.io" in host:
        return host, "greenhouse", None

    if "lever.co" in host:
        return host, "lever", None

    if "workday" in host or "myworkdayjobs.com" in host:
        return host, "workday", None

    if "ashbyhq.com" in host:
        return host, "ashby", None

    if "indeed.com" in host:
        job_id = _extract_query_param(url, "jk")
        return host, "indeed", job_id

    if "ziprecruiter.com" in host:
        return host, "ziprecruiter", None

    if "flexjobs.com" in host:
        return host, "flexjobs", None

    return host, "unknown", None


def _extract_linkedin_job_id(url):
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "currentJobId" in params:
        return params["currentJobId"][0]
    # /jobs/view/{id}/ pattern
    m = re.search(r"/jobs/view/(\d+)", url)
    if m:
        return m.group(1)
    return None


def _extract_query_param(url, param):
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return params.get(param, [None])[0]


# ---------------------------------------------------------------------------
# Job-alert email parsing
# ---------------------------------------------------------------------------

# Source detection from sender address
def detect_source_from_sender(sender):
    sender_lower = sender.lower()
    if "linkedin" in sender_lower:
        return "linkedin"
    if "indeed" in sender_lower:
        return "indeed"
    if "ziprecruiter" in sender_lower:
        return "ziprecruiter"
    if "flexjobs" in sender_lower:
        return "flexjobs"
    if "greenhouse" in sender_lower:
        return "greenhouse"
    if "lever" in sender_lower:
        return "lever"
    return None


def make_job_id(source, canonical_url, job_id_extracted=None):
    """Create a stable unique ID for a job entry."""
    if job_id_extracted:
        return f"{source}_{job_id_extracted}"
    # Fall back to a hash of the canonical URL
    url_hash = hashlib.md5(canonical_url.encode()).hexdigest()[:8]
    return f"{source}_{url_hash}"


def determine_fetch_status(source, ats_host, settings):
    """Return the initial jd_fetch_status for a job based on its source."""
    skip_hosts = settings["scraper"]["skip_hosts"]
    playwright_hosts = settings["scraper"]["playwright_hosts"]

    if any(h in ats_host for h in skip_hosts):
        if source == "linkedin":
            return "pending_chrome_extension"
        return "pending_manual"

    if any(h in ats_host for h in playwright_hosts):
        return "pending_playwright"

    # Unknown host - default to manual
    return "pending_manual"


def extract_snippet(body_plain, max_chars=300):
    """Return a short excerpt from the plain-text body."""
    if not body_plain:
        return ""
    # Trim boilerplate lines (unsubscribe links, etc.)
    lines = [
        l.strip()
        for l in body_plain.splitlines()
        if len(l.strip()) > 20
        and not any(
            kw in l.lower()
            for kw in ("unsubscribe", "privacy policy", "manage alerts", "click here")
        )
    ]
    excerpt = " ".join(lines)[:max_chars]
    return excerpt.strip()


# ---------------------------------------------------------------------------
# Already-applied deduplication
# ---------------------------------------------------------------------------

def load_applied_companies_and_roles(csv_path):
    """
    Return a set of (company_lower, role_fragment_lower) tuples already in the CSV.
    Used to skip jobs we have already applied for or evaluated.
    """
    seen = set()
    if not csv_path.exists():
        return seen
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = (row.get("Company") or "").strip().lower()
            role = (row.get("Role") or "").strip().lower()
            if company:
                seen.add((company, role))
    return seen


def is_already_applied(job_entry, applied_set):
    company = job_entry.get("company", "").lower().strip()
    role = job_entry.get("title", "").lower().strip()
    # Check exact company+role first
    if (company, role) in applied_set:
        return True
    # Also check company-only (different role at same company we've already touched)
    # This is conservative; you may want to remove this check if you apply to
    # multiple roles at the same company.
    for c, r in applied_set:
        if c == company:
            return True
    return False


# ---------------------------------------------------------------------------
# Main harvest logic
# ---------------------------------------------------------------------------

def process_message(service, msg_id, settings, applied_set):
    """
    Process one Gmail message and return a list of job dicts (may be empty).
    """
    sender, subject, email_date, body_plain, body_html = get_message_parts(
        service, msg_id
    )
    sender_source = detect_source_from_sender(sender)

    all_urls = extract_urls_from_body(body_plain, body_html)
    if not all_urls:
        return []

    jobs = []
    for raw_url in all_urls:
        parsed_raw = urllib.parse.urlparse(raw_url)
        raw_host = parsed_raw.netloc.lower()

        # Only resolve redirects if this looks like a tracking/email URL
        if any(td in raw_host for td in TRACKING_DOMAINS) or (
            sender_source and sender_source in ("linkedin", "indeed", "ziprecruiter")
        ):
            canonical_url = resolve_redirect(raw_url)
            time.sleep(0.3)  # polite rate limit
        else:
            canonical_url = raw_url

        ats_host, source, job_id = classify_url(canonical_url)

        # Skip non-job-board URLs (unsubscribe pages, images, etc.)
        if source == "unknown" and not any(
            kw in canonical_url
            for kw in ("job", "career", "position", "opening", "role")
        ):
            continue

        # Use sender-detected source if classifier returned unknown
        if source == "unknown" and sender_source:
            source = sender_source

        fetch_status = determine_fetch_status(source, ats_host, settings)
        unique_id = make_job_id(source, canonical_url, job_id)

        # Stub: title/company/location need richer per-source parsing for full accuracy.
        # For now we use the email subject as a fallback title and leave company blank.
        # The coach (me) fills in company/title at triage from the JD file or snippet.
        title = subject.strip()
        company = ""
        location = ""

        entry = {
            "id": unique_id,
            "title": title,
            "company": company,
            "location": location,
            "source": source,
            "canonical_url": canonical_url,
            "ats_host": ats_host,
            "email_snippet": extract_snippet(body_plain),
            "email_date": email_date,
            "jd_file": None,
            "jd_fetch_status": fetch_status,
            "already_applied": False,
            "triage_status": "pending",
        }

        if is_already_applied(entry, applied_set):
            entry["already_applied"] = True
            entry["triage_status"] = "skip"
            continue  # don't add already-applied jobs to the feed

        jobs.append(entry)

    return jobs


def dedupe_by_id(jobs):
    seen = set()
    result = []
    for j in jobs:
        if j["id"] not in seen:
            seen.add(j["id"])
            result.append(j)
    return result


def main():
    settings = load_settings()

    project_root = Path(settings["paths"]["project_root"]).expanduser()
    feed_path = project_root / settings["paths"]["job_feed"]
    csv_path = project_root / settings["paths"]["applications_csv"]

    feed_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing feed to carry forward already-fetched entries
    existing_feed = []
    if feed_path.exists():
        with open(feed_path, "r", encoding="utf-8") as f:
            try:
                existing_feed = json.load(f)
            except json.JSONDecodeError:
                existing_feed = []

    existing_ids = {j["id"] for j in existing_feed}
    applied_set = load_applied_companies_and_roles(csv_path)

    service = get_gmail_service(settings)

    lookback = int(settings["gmail"].get("lookback_days", 1))
    after_date = (datetime.date.today() - datetime.timedelta(days=lookback)).strftime(
        "%Y/%m/%d"
    )

    query = settings["gmail"]["query"]
    message_ids = search_messages(service, query, after_date)
    print(f"Found {len(message_ids)} job-alert messages in the past {lookback} day(s).")

    new_jobs = []
    for msg_id in message_ids:
        try:
            jobs = process_message(service, msg_id, settings, applied_set)
            for j in jobs:
                if j["id"] not in existing_ids:
                    new_jobs.append(j)
                    existing_ids.add(j["id"])
        except Exception as e:
            print(f"Error processing message {msg_id}: {e}")

    new_jobs = dedupe_by_id(new_jobs)

    max_jobs = int(settings["pipeline"].get("max_jobs_per_run", 15))
    if len(new_jobs) > max_jobs:
        print(
            f"Capping new jobs at {max_jobs} (found {len(new_jobs)}). "
            "Increase max_jobs_per_run in settings.json to raise the limit."
        )
        new_jobs = new_jobs[:max_jobs]

    merged_feed = existing_feed + new_jobs

    with open(feed_path, "w", encoding="utf-8") as f:
        json.dump(merged_feed, f, indent=2, ensure_ascii=False)

    # Also write a dated snapshot for archiving
    today = datetime.date.today().isoformat()
    snapshot_path = feed_path.parent / f"job_feed_{today}.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(new_jobs, f, indent=2, ensure_ascii=False)

    print(
        f"Harvested {len(new_jobs)} new job(s). "
        f"Feed total: {len(merged_feed)}. "
        f"Written to {feed_path}."
    )


if __name__ == "__main__":
    main()
