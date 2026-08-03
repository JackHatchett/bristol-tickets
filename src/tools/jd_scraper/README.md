# JD Scraper

Getting job-description text from a job alert into a triage-ready file.

**Optional.** `career_coach` runs every playbook off a pasted job description.
This folder automates the incoming half and asks for real setup: a mail account
receiving job alerts, Google API credentials (`credentials.example.json` is the
shape), a settings file (`settings.example.json`), the OS keychain, and a
schedule (`setup_cron.sh`). Skipping it breaks nothing else.

Examples below use `$CAREER_COACH_DIR` for this agent's data root, resolved
per instance through config.

## Tiers

Full JD text is needed only at the cover-letter stage; a triage verdict runs off
a snippet. Sources resist scraping differently — JS rendering, bot walls, login
walls — so each posting routes by source to the cheapest method that reaches it.

- **Tier 0, email harvest** — `gmail_harvest.py` parses job-alert mail into
  `applications/pipeline/job_feed.json`: company, title, location, canonical
  link and usually a snippet.
- **Tier 1, local scrape** — `jd_scraper.py` drives headless Playwright against
  the `playwright_hosts` in settings. Greenhouse is server-rendered and yields
  full text with no JS; Lever, Workday and Ashby need a real browser context.
  ZipRecruiter, Indeed and FlexJobs need the persistent login profile at
  `config/browser_profile/`, and a native ZipRecruiter-hosted posting falls
  through to tier 3 even then.
- **Tier 2, same-origin fetch in the browser** — the LinkedIn recipe below,
  run in-session. LinkedIn sits in `skip_hosts` and never reaches tier 1.
- **Tier 2b, vision fallback** — a screenshot of the rendered page, read
  in-session. Site-agnostic, and the last resort before a paste.
- **Tier 3, manual paste** — the floor. Cover letters are capped per run and
  triage needs no full text, so this is cheap and fully reliable.

- **Never run a scraper from a network-allowlisted sandbox.** There is no route
  out to a job board from inside one; acquisition runs on the user's own machine
  or inside their real logged-in browser.
- **Take one screenshot as a diagnostic read, never as a retry loop.** Read it
  once, decide bot wall, login wall or real page, and route a wall straight to
  manual paste. Retrying against a bot check gets an address flagged.

## Scripts

| Script | Tier | Responsibility |
|---|---|---|
| `gmail_harvest.py` | 0 | Gmail API to `applications/pipeline/job_feed.json` |
| `jd_scraper.py` | 1 | Playwright to JD text files |
| `daily_pipeline.py` | — | the orchestrator, and the only thing a schedule calls |
| `keyring_utils.py`, `migrate_to_keyring.py` | — | secrets in the OS keychain, never in plaintext config |
| `setup_cron.sh` | — | installs the cron entry, reading `CAREER_COACH_DIR` from the environment |

## The LinkedIn recipe

Needs LinkedIn open and logged in in the user's own Chrome, approved for the
Chrome extension, and the extension's JavaScript tool.

- **Go straight to the JavaScript tool.** The navigate, read-page and screenshot
  tools time out on LinkedIn.
  // Those tools wait for a load-settled signal LinkedIn's single-page app never
  // emits cleanly.

1. **Take the job ID** — the `currentJobId` query parameter on a search or
   detail URL, or the path segment of a `/jobs/view/{id}/` URL.
2. **Run this on the LinkedIn tab:**

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

3. **Take `body.innerText` with whitespace collapsed**, never a specific
   selector. The guest markup's class names vary. The header carries title,
   company and location; the body is the posting.

Where the guest endpoint stops working, read a live internal endpoint out of the
browser's network activity rather than hardcoding one — those paths change.

## Setup

**Dependencies.**

```bash
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 \
             google-api-python-client playwright requests
playwright install chromium
```

**Gmail credentials.** In the Google Cloud console, create or reuse a project,
enable the Gmail API, and create an OAuth client ID of type Desktop app. Save
the downloaded JSON to `$CAREER_COACH_DIR/config/gmail_credentials.json`. On the
consent screen set user type External, add the account as a test user, and add
the `https://www.googleapis.com/auth/gmail.readonly` scope.

**First run.** `python3 tools/gmail_harvest.py` from `$CAREER_COACH_DIR` opens a
browser to approve access once, then writes `config/gmail_token.json` and
refreshes it automatically.

**Alert filtering.** The search query lives in `config/settings.json`. Labelling
job-alert mail and adding `label:<name>` to the query cuts the noise.

**Scheduling.** A cron entry or a launchd job calls `daily_pipeline.py` daily,
ahead of any morning briefing, logging into
`applications/pipeline/logs/`. `setup_cron.sh` installs the cron form.

**Test.** `python3 tools/daily_pipeline.py`, then read
`applications/pipeline/job_feed.json` and `applications/pipeline/logs/pipeline.log`.

## Troubleshooting

- **`No module named google.auth` or `playwright`** — the dependency step did
  not complete. Re-run it, and `playwright install chromium` with it.
- **The OAuth browser window never opens** — the terminal has no display
  access. Run it from a plain terminal window.
- **A scrape returns a few hundred characters** — the page is client-rendered
  and the job is marked `fetch_failed`. Add the host to `skip_hosts` where it
  fails consistently; it falls to manual paste.
- **A scheduled run never fires** — macOS withholds Full Disk Access from
  `/usr/sbin/cron` until it is granted in System Settings.
