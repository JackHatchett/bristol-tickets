# jd_scraper: the JD-acquisition pipeline

**Optional.** `career_coach` works fully without any of this — the user pastes
a job description into the session and every playbook runs. This folder is for
users who want the incoming half automated, and it asks for real setup: a Gmail
account receiving job alerts, Google API credentials (`credentials.example.json`
is the shape), a settings file (`settings.example.json`), the OS keychain for
secrets, and a cron entry (`setup_cron.sh`). Skip the folder and nothing else
breaks.

Everything under this folder handles getting job-description text from a job
alert into a triage-ready file. It has two halves: a local pipeline (this
folder's scripts, run outside Cowork on the user's own machine) and an
in-session technique (the LinkedIn recipe below, run by the coach inside a
Cowork session via the Chrome extension). Together they implement a tiered
acquisition strategy: match each source to the cheapest method that actually
works for it, and never build a fragile universal scraper.

## Why tiered acquisition, not one scraper

Full JD text is only required at the cover-letter stage; triage runs fine off
a snippet. Sources fight scraping in different ways (JS rendering, bot walls,
login walls), so one scraper trying to beat every wall is the wrong shape.
Route each posting by source to the cheapest method that works for it instead:

- **Tier 0 — email harvest** (`gmail_harvest.py`, free, robust): parses the
  user's job-alert emails into `applications/pipeline/job_feed.json`. Yields company, title,
  location, canonical link, and usually a JD snippet. Most triage verdicts
  don't need the full JD text — a snippet plus the user's context files is
  enough.
- **Tier 1 — local scrape for SSR/ATS-friendly hosts** (`jd_scraper.py`, via
  Playwright, headless, scheduled): works well for Greenhouse (server-rendered,
  full JD text with zero JS), and for Lever/Workday/Ashby with a real browser
  context. ZipRecruiter, Indeed, and FlexJobs need the persistent login profile
  (`config/browser_profile/`) to get past bot walls reliably; native
  ZipRecruiter-hosted postings are Cloudflare-blocked even then and fall
  through to Tier 3.
- **Tier 2 — Chrome extension same-origin fetch (LinkedIn; in-session, coach
  handles it)**: LinkedIn is excluded from the local scraper (`skip_hosts` in
  settings). Its own guest API, called from inside a logged-in LinkedIn tab via
  the Chrome extension's JavaScript tool, returns the full JD body even though
  the extension's own page-read tools only see a stripped shell. See "The
  LinkedIn recipe" below for the exact technique. This is the one narrow,
  site-specific technique in the whole pipeline — reserved for LinkedIn because
  no other route reaches it.
- **Tier 2b — vision fallback** (universal, in-session): if a source resists
  every scripted approach, the page is still rendered somewhere a human can
  see it. A screenshot read by the coach is a site-agnostic last resort before
  falling to manual paste.
- **Tier 3 — manual paste** (the reliable floor, not a failure mode): for
  bot-hostile sources and any Tier 1/2 miss, the user pastes the JD directly.
  Because cover letters are capped at a small number per run and triage
  doesn't need full text, this floor is cheap and fully reliable — it's a
  deliberate design choice, not something to keep trying to engineer away.

A sandboxed environment with an allowlisted network (like a Cowork bash
sandbox) cannot run a scraper against arbitrary job sites — there is no route
out to those hosts from inside it. Any acquisition method that needs real
network access to a job board must run either on the user's own machine
(Tier 0/1, this folder) or inside a tool that already executes in the user's
real, logged-in browser (Tier 2/2b).

## The LinkedIn recipe (Tier 2)

Requires: LinkedIn open and logged in in the user's real Chrome, approved for
the Chrome extension, and the extension's JavaScript-execution tool (not the
page-read/navigate tools, which time out on LinkedIn's continuously-polling
search UI).

1. Get the job ID. From a search/detail URL it's the `currentJobId` query
   parameter; from a `/jobs/view/{id}/` URL it's the path segment.
2. Run this via the Chrome extension's JavaScript tool on the LinkedIn tab:

   ```js
   (async () => {
     const id = /* substitute the target jobId */;
     const r = await fetch(
       'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/' + id,
       { credentials: 'include' });
     const html = await r.text();
     const doc = new DOMParser().parseFromString(html, 'text/html');
     let t = doc.body.innerText
       .replace(/[ \t]+/g,' ').replace(/\n[ \t]*/g,'\n').replace(/\n{2,}/g,'\n').trim();
     return { status: r.status, chars: t.length, jd: t };
   })()
   ```

3. This returns the full JD text (header carries title/company/location, body
   is the posting). The guest markup's class names vary, so `body.innerText`
   with whitespace collapsed is the reliable extraction, not a specific
   selector.

Do not use the extension's navigate/read-page/screenshot tools on LinkedIn
search or job pages first — they wait for a load-settled signal LinkedIn's
single-page app never emits cleanly, and will time out. Go straight to the
JavaScript tool once the tab is open. If this guest endpoint ever stops
working, the logged-in app's own internal API endpoints are an alternate
source — read one live from the browser's network activity rather than
hardcoding a path, since those internal paths change over time.

## What each script does

| Script | Tier | Responsibility |
|---|---|---|
| `gmail_harvest.py` | 0 | Gmail API -> `applications/pipeline/job_feed.json` |
| `jd_scraper.py` | 1 | Playwright -> JD text files for Lever/Workday/Ashby/Greenhouse/ZipRecruiter/Indeed/FlexJobs |
| `daily_pipeline.py` | — | Orchestrator; the only thing cron needs to call |
| `keyring_utils.py` / `migrate_to_keyring.py` | — | Secrets in the OS keychain, never in plaintext config |

LinkedIn JDs are handled entirely by the Tier 2 in-session recipe above, never
by this local pipeline. Examples below use `$CAREER_COACH_DIR` for this
agent's provisioned tools/data root — set it per-instance (resolved via
config); don't hardcode an absolute path here.

---

## Step 1: Python dependencies

```bash
pip3 install \
  google-auth \
  google-auth-oauthlib \
  google-auth-httplib2 \
  google-api-python-client \
  playwright \
  requests
```

Then install Playwright's Chromium browser (one-time, ~150 MB):

```bash
playwright install chromium
```

---

## Step 2: Gmail API credentials (one-time setup)

This step is manual. It takes about 10 minutes.

1. Go to https://console.cloud.google.com and create a project (or reuse one).
2. Enable the Gmail API: APIs and Services > Enable APIs > search "Gmail API" > Enable.
3. Create OAuth credentials:
   - APIs and Services > Credentials > Create Credentials > OAuth client ID
   - Application type: Desktop app
   - Download the JSON and save it to:
     `$CAREER_COACH_DIR/config/gmail_credentials.json`
4. Configure the OAuth consent screen if prompted:
   - User type: External
   - Add your Gmail address as a test user
   - Scopes: add `https://www.googleapis.com/auth/gmail.readonly`

### First run (browser OAuth dance)

Run the script once manually from Terminal. It will open a browser window for you
to approve Gmail access. After approval, a token is saved to
`config/gmail_token.json` and future runs are non-interactive.

```bash
cd "$CAREER_COACH_DIR"
python3 tools/gmail_harvest.py
```

The token auto-refreshes. You should only need to do the browser step once unless
you revoke access in Google Account settings.

---

## Step 3: Gmail label / alert setup

The script searches Gmail using the query in `config/settings.json`. You can tune
it there without touching the Python.

Recommended: create a Gmail filter that labels job-alert emails with a label like
`job_alerts` and update the query to include `label:job_alerts`. This reduces noise.

---

## Step 4: Scheduling

### Option A: cron (simplest)

Open your crontab:

```bash
crontab -e
```

Add this line (adjust the Python path if needed; `which python3` shows yours):

```
0 6 * * * /usr/local/bin/python3 $CAREER_COACH_DIR/tools/daily_pipeline.py >> $CAREER_COACH_DIR/applications/pipeline/logs/cron_output.log 2>&1
```

This runs at 6:00 AM daily, ahead of any morning job-search briefing.

### Option B: launchd (macOS native, more reliable)

Create a plist at `~/Library/LaunchAgents/com.<user>.career-coach-pipeline.plist`
(substitute the instance's actual reverse-DNS label and `$CAREER_COACH_DIR`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.<user>.career-coach-pipeline</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>$CAREER_COACH_DIR/tools/daily_pipeline.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$CAREER_COACH_DIR/applications/pipeline/logs/launchd_output.log</string>
    <key>StandardErrorPath</key>
    <string>$CAREER_COACH_DIR/applications/pipeline/logs/launchd_error.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.<user>.career-coach-pipeline.plist
```

Or run `setup_cron.sh` (Option A, scripted) with `CAREER_COACH_DIR` set in the
environment.

---

## Step 5: Test run

```bash
cd "$CAREER_COACH_DIR"
python3 tools/daily_pipeline.py
```

Check `applications/pipeline/job_feed.json` and
`applications/pipeline/logs/pipeline.log` for output.

---

## Troubleshooting

**"No module named google.auth"**: run the pip install step again.

**"No module named playwright"**: run `pip3 install playwright` and `playwright install chromium`.

**Gmail auth browser window doesn't open**: ensure the terminal has display access.
Try running from a regular Terminal window (not inside iTerm pane with restricted permissions).

**Playwright scrapes very short text (~300 chars)**: the page is likely client-rendered
and JavaScript-heavy. The job will be marked `fetch_failed`. Add the host to
`skip_hosts` in `settings.json` if it consistently fails; it falls to manual paste.

**cron job doesn't run**: macOS requires granting Full Disk Access to cron.
Go to System Settings > Privacy and Security > Full Disk Access, add `/usr/sbin/cron`.

**A previously reliable scrape suddenly returns a bot wall or empty shell**: treat one
screenshot as a diagnostic read, not a retry loop — take it, read it once, decide
(bot wall / login wall / real page), and route to manual paste immediately if it's a
wall. Don't loop or retry against a bot check; that's what gets an IP flagged.
