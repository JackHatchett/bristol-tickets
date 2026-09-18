---
name: searching-job-boards
description: Finds which postings an employer actually has open and gets the text of each one, routing by the recruiting system the careers host runs rather than by the aggregator that listed it. Use when a company is named and its openings are wanted, when a posting has to be confirmed still open, or when a role and a location are being searched.
license: MIT
compatibility: Needs a web fetch tool for the direct reads and a browser the user is signed into for the two hosts that refuse one.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# searching-job-boards

Input: a named employer, or a role and a location. Operation: the route below.
Output: postings open at the moment of the run, each carrying the text its next
stage needs.

## The employer's own host is the only thing that settles it

- **Confirm every posting on the careers host the employer runs.** An
  aggregator's copy settles nothing: one reads complete and current there while
  the employer's own host has no such requisition, and one an aggregator calls
  removed is often open again under a new requisition number.
- **Find that host before searching anywhere else.** A site-restricted web
  search over it returns requisition pages directly.
- **Treat a search index as a list of candidates.** The requisition page is the
  answer; an indexed page that reports itself missing is a closed requisition.
- **Identify the recruiting system from the URL** and take its route below. The
  system decides what is readable, and the employer does not.

## Oracle HCM Candidate Experience — `*/hcmUI/CandidateExperience/...`

- **Discover through the requisition resource**, not the search page:
  `/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=<site>,keyword=<term>,limit=<n>,sortBy=POSTING_DATES_DESC`,
  every argument percent-encoded. It returns Id, Title, PrimaryLocation and
  PostedDate per requisition, and it honours the filters passed to it.
- **Omit `expand=requisitionList` and only the facet counts come back** — useful
  for sizing a search before running it.
- **`siteNumber` is the site segment of the careers URL**, and the tenant
  default `CX_1` answers for the whole tenant where a named site does not.
- **Take full text from `<site root>/job/<Id>/`**, which carries the whole
  description to a plain fetch.
- **Never filter by query parameter on the human search page.** It returns the
  tenant's unfiltered count, and a pass built on it reads every requisition the
  employer has.

## Greenhouse — `job-boards.greenhouse.io`

- **Discover from the board page**, which lists every role with its id.
- **Take full text from `/jobs/<id>`**, description and posted salary range
  included, to a plain fetch.

## Workday — `*.myworkdayjobs.com`

- **Drive it in a browser.** The host refuses a plain fetch, and the JSON path
  its own front end calls refuses one too.
- **Pass the search term as `?q=<term>` on the search page**, which this host
  honours.
- **Build a requisition URL with its location segment** —
  `/job/<Location>/<Slug>_<Req>`. Without it the host reports the page does not
  exist, whether or not the requisition is open.

## LinkedIn — triage-grade, and only in the user's own browser

- **Never fetch a job path with an automated client.** The site's own rules
  disallow them, the guest description endpoint included, and a same-origin call
  issued from inside a signed-in tab is that same request by another route.
- **Drive it in the browser the user is signed into and read what renders.**
- **Scroll the requisition page before reading it.** The description mounts on
  scroll, and a page read without one yields about fifteen hundred characters of
  frame, title and employer, and no description.
- **Slice the rendered text from `About the job` to `Benefits found in job post`
  or `Set alert for similar jobs`.** Element selectors on this host change
  between reads; those headings do not.
- **Take a LinkedIn read as triage-grade.** A long description stays collapsed
  behind a control the page does not reliably expose, so a slice can end early
  with nothing in the text saying it did.

## Reading any rendered page

- **Read the page's own rendered text rather than a screenshot of it.** A
  screenshot of a signed-in tab captures everything else that tab is showing,
  the user's private messages included.
- **Extract by heading boundaries rather than by element selectors**, which are
  a per-host treadmill.

## Stop rather than vary

- **Three attempts per source, then stop on that source.** An empty shell, a
  timeout, a refusal, a sign-in wall and a challenge page each count.
- **Say what the source did, in the words of what came back**, and move on.
- **Fall to the next route rather than to a variation of the same call.** The
  order is the employer's own host by direct fetch, then a browser on that host,
  then the user's own paste.
- **Set the cap per source before the pass starts, from what that source costs
  to read.** A requisition page on an employer's own host is one cheap read; a
  host that has to be driven in a browser is several times that. One number
  applied to both sizes the pass wrongly at one end of it.

## How much text each stage needs

- **Triage on title, employer, location and posting date**, which every route
  above returns without a full read.
- **Take full description only for the postings a letter is being written for**,
  and take the user's paste for those where no route above returns it whole.
