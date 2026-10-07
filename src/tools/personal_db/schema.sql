-- personal.db — unified personal-tracking database schema (v1)
-- ---------------------------------------------------------------------------
-- SoT for the user's personal-tracking domains. The DB is the source of truth;
-- the xlsx files are generated *views/snapshots* (see render_snapshot.py),
-- kept as a visual backup + mistake-finding aid. Long-term backup of the
-- underlying files is Time Machine's job, not the snapshot's.
--
-- Modeled on:
--   data/<instance>/library/db/schema.sql    (books/loans/lists pattern)
--   src/tools/ticket_tools/                 (write-safety + discovery conventions)
--
-- Multi-domain by design. Each domain = one (or a few) tables + an optional
-- stats view, registered in the `domains` table. Adding a future domain
-- (e.g. health) means: create its table(s) + optional view, INSERT a row into
-- `domains`, and add a render spec — no change to existing domains or tools.
-- ---------------------------------------------------------------------------

PRAGMA foreign_keys = ON;

-- ── Meta / versioning ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- ── Domain registry (future-proofing) ───────────────────────────────────────
-- Enumerable list of tracked domains so the renderer + a future custom viewer
-- can iterate domains generically instead of hardcoding them.
-- `source` says which database the domain's rows come from. Not every domain
-- lives here: books live in Zotero but still render a snapshot, so the
-- registry has to be able to name a source of truth outside this file.
CREATE TABLE IF NOT EXISTS domains (
    name          TEXT PRIMARY KEY,   -- machine slug: 'applications' | 'books' | 'health' ...
    display_name  TEXT NOT NULL,
    source        TEXT NOT NULL DEFAULT 'personal_db',  -- 'personal_db' | 'zotero'
    primary_table TEXT NOT NULL,      -- main data table for the domain, in `source`
    snapshot_file TEXT,               -- xlsx filename rendered for this domain (in the snapshots dir)
    stats_view    TEXT,               -- optional analytics view name; NULL when `source` is not this DB
    active        INTEGER NOT NULL DEFAULT 1,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    notes         TEXT
);

-- ═══════════════════════════════════════════════════════════════════════════
-- DOMAIN: applications
-- Column set mirrors data/<instance>/career/SCHEMA.md 1:1. See that file for the
-- Fit Verdict vocabulary and Gap taxonomy (kept as the living reference).
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS applications (
    id             INTEGER PRIMARY KEY,
    company        TEXT NOT NULL,
    role           TEXT,
    fit_notes      TEXT,                        -- freeform: ATS codes, approach, contacts, narrative
    fit_verdict    TEXT,                        -- Apply/Borderline/Skip/Strong/... (SCHEMA.md vocab)
    gaps           TEXT,                        -- comma-separated gap keywords (SCHEMA.md taxonomy)
    location       TEXT,
    ats_platform   TEXT,
    date_evaluated TEXT,                        -- ISO date or as-logged
    cover_letter   TEXT,                        -- Yes/No/short note
    status         TEXT,                        -- Applied/Pending/Rejected/Interviewing/...
    intro_stage    TEXT,                        -- set on an introduction row only; vocabulary below
    intro_stage_on TEXT,                        -- ISO date intro_stage was last set
    last_touch_on  TEXT,                        -- ISO date of the last exchange about it; a reopen sets it
    contact        TEXT,
    referral       TEXT,
    jd_link        TEXT,
    year           INTEGER,
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_applications_company ON applications(company);
CREATE INDEX IF NOT EXISTS idx_applications_status  ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_year    ON applications(year);

-- Analytics view (recomputed live; the xlsx Stats tab mirrors this).
CREATE VIEW IF NOT EXISTS v_application_stats AS
SELECT
    (SELECT COUNT(*)                       FROM applications)                         AS total_applications,
    (SELECT COUNT(DISTINCT LOWER(company)) FROM applications)                         AS distinct_companies,
    (SELECT COUNT(*) FROM applications WHERE status LIKE 'Applied%')                  AS status_applied,
    (SELECT COUNT(*) FROM applications WHERE status LIKE 'Interview%')                AS status_interviewing,
    (SELECT COUNT(*) FROM applications WHERE status LIKE 'Rejected%')                 AS status_rejected,
    (SELECT COUNT(*) FROM applications WHERE status LIKE 'Pending%')                  AS status_pending,
    (SELECT COUNT(*) FROM applications WHERE cover_letter IN ('Yes','yes','Y'))       AS with_cover_letter,
    (SELECT COUNT(*) FROM applications WHERE referral IS NOT NULL AND TRIM(referral)<>'') AS with_referral;

-- ═══════════════════════════════════════════════════════════════════════════
-- DOMAIN: contacts
-- Who is owed what, and since when. Three places already describe a person —
-- the applications table's contact and referral text, the career dossiers, and
-- the notebook's own pages — and none of them holds a date. This domain is the
-- state layer beside them rather than a fourth description: nothing migrates
-- into it and nothing it holds is a copy of what they hold.
--
-- A contact is one person, once. An ask is one thing outstanding between the
-- user and that person, in either direction. A link joins a contact to
-- something else — an application, a document, a client — so a person can be
-- attached to many of them over time without any of their identifiers becoming
-- a column here.
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS contact (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    aliases         TEXT,                     -- other names this person answers to, comma separated
    how_known       TEXT,                     -- how the user knows them, in their own words
    company         TEXT,                     -- where they are now
    title           TEXT,                     -- what they do there now
    cadence_days    INTEGER,                  -- how often to be in touch; NULL means no cadence is owed
    last_contact_on TEXT,                     -- ISO date of the last exchange either way
    email           TEXT,                     -- optional; nothing asks for it when absent
    linkedin_url    TEXT,                     -- optional; nothing asks for it when absent
    is_friend       INTEGER,                  -- 1 for a friend: a durable row on the dashboard, never removed by expiry
    reference_status TEXT,                    -- none | to_ask | asked | yes | declined
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_contact_name ON contact(LOWER(name));

-- One row per thing outstanding. `direction` says who the ask waits on: 'us'
-- when the next move is the user's, 'them' when it is the other person's.
CREATE TABLE IF NOT EXISTS contact_ask (
    id         INTEGER PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contact(id),
    kind       TEXT NOT NULL,                 -- reconnect | referral | application-submit | recommendation | intro | favour-owed | other
    direction  TEXT NOT NULL DEFAULT 'them',  -- us | them — who the next move waits on
    subject    TEXT,                          -- what the ask is about, in one line
    opened_on  TEXT NOT NULL DEFAULT (date('now')),
    due_on     TEXT,                          -- ISO date this becomes late; NULL means no date was set
    status     TEXT NOT NULL DEFAULT 'open',  -- open | done | dropped
    last_touch TEXT                           -- ISO date of the last move on this ask
);
CREATE INDEX IF NOT EXISTS idx_ask_contact ON contact_ask(contact_id);
CREATE INDEX IF NOT EXISTS idx_ask_status  ON contact_ask(status);

-- One row per thing a contact is connected to. `target_id` names a row in this
-- database and `target_path` a declared path; a row carries whichever of the
-- two its kind has, and never an identifier copied onto the contact itself.
CREATE TABLE IF NOT EXISTS contact_link (
    id          INTEGER PRIMARY KEY,
    contact_id  INTEGER NOT NULL REFERENCES contact(id),
    target_kind TEXT NOT NULL,                -- application | document | client | course | other
    target_id   INTEGER,
    target_path TEXT,
    label       TEXT,                         -- what this link is, for a reader
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_link_contact ON contact_link(contact_id);

-- An introduction is one applications row whose intro_stage is set, joined to
-- the people on it by contact_link rows labelled 'introducer' (or 'referrer',
-- for a friend referring the user at the friend's own company) and
-- 'intro target'. One friend may hold both labels on one row.
--
-- intro_stage: to_ask | asked | introduced | submitted | interviewing, while
-- open; offer | rejected | no_response | dropped, once closed. `move` says
-- whose move an open introduction waits on, and is NULL once it has closed.
CREATE VIEW IF NOT EXISTS v_introduction AS
SELECT a.id          AS app_id,
       a.company     AS company,
       a.role        AS role,
       a.intro_stage AS stage,
       CASE WHEN a.intro_stage IN ('to_ask', 'introduced')               THEN 'us'
            WHEN a.intro_stage IN ('asked', 'submitted', 'interviewing') THEN 'them'
       END           AS move,
       (SELECT l.contact_id FROM contact_link l
         WHERE l.target_kind = 'application' AND l.target_id = a.id
           AND l.label IN ('introducer', 'referrer')
         ORDER BY l.id LIMIT 1)                                AS introducer_id,
       (SELECT l.contact_id FROM contact_link l
         WHERE l.target_kind = 'application' AND l.target_id = a.id
           AND l.label = 'intro target'
         ORDER BY l.id LIMIT 1)                                AS target_id
FROM applications a
WHERE a.intro_stage IS NOT NULL;

-- A friend rests after an introduction through them resolves: the next ask is
-- fine REST_DAYS (21) after it closed. A referral at the friend's own company
-- (introducer and target the same person, or no target linked) costs them little and starts no
-- rest, and a friend with an introduction still open is not resting but busy.
-- A row appears only while the rest runs; outside it there is nothing to show.
CREATE VIEW IF NOT EXISTS v_friend_rest AS
SELECT c.id                                        AS contact_id,
       c.name                                      AS name,
       MAX(i_closed.closed_on)                     AS last_resolved_on,
       date(MAX(i_closed.closed_on), '+21 days')   AS next_ask_on
FROM contact c
JOIN (SELECT v.introducer_id, a.intro_stage_on AS closed_on
        FROM v_introduction v JOIN applications a ON a.id = v.app_id
       WHERE v.move IS NULL
         AND v.target_id IS NOT NULL
         AND v.target_id <> v.introducer_id
         AND a.intro_stage_on IS NOT NULL) i_closed
  ON i_closed.introducer_id = c.id
WHERE c.is_friend = 1
  AND NOT EXISTS (SELECT 1 FROM v_introduction o
                   WHERE o.introducer_id = c.id AND o.move IS NOT NULL)
GROUP BY c.id
HAVING date(MAX(i_closed.closed_on), '+21 days') > date('now');

-- What is due: a contact whose cadence has come round, and an ask past the date
-- it was given. One view rather than two, because the question they answer is
-- one question — who is owed something today.
CREATE VIEW IF NOT EXISTS v_contact_due AS
SELECT c.id                                                        AS contact_id,
       c.name                                                      AS name,
       'cadence'                                                   AS reason,
       NULL                                                        AS ask_id,
       NULL                                                        AS kind,
       c.last_contact_on                                           AS since,
       date(c.last_contact_on, '+' || c.cadence_days || ' days')   AS due_on
FROM contact c
WHERE c.cadence_days IS NOT NULL
  AND c.cadence_days > 0
  AND (c.last_contact_on IS NULL
       OR date(c.last_contact_on, '+' || c.cadence_days || ' days') <= date('now'))
UNION ALL
SELECT c.id, c.name, 'ask', a.id, a.kind, a.opened_on, a.due_on
FROM contact_ask a
JOIN contact c ON c.id = a.contact_id
WHERE a.status = 'open'
  AND a.due_on IS NOT NULL
  AND a.due_on <= date('now');

CREATE VIEW IF NOT EXISTS v_contact_stats AS
SELECT
    (SELECT COUNT(*) FROM contact)                                   AS contacts,
    (SELECT COUNT(*) FROM contact_ask WHERE status='open')           AS open_asks,
    (SELECT COUNT(*) FROM v_contact_due WHERE reason='ask')          AS asks_past_due,
    (SELECT COUNT(*) FROM v_contact_due WHERE reason='cadence')      AS cadence_due;

-- ═══════════════════════════════════════════════════════════════════════════
-- DOMAIN: books — NOT IN THIS DB
-- Zotero is the source of truth for book data. This file holds no books, loans,
-- lists, list_items or book_snapshots tables and no v_book_stats view; reading
-- lists are Zotero collections, ownership is the Shelved tag, and the library
-- xlsx is rendered from tools/zotero/zotero_export.py.
-- Nothing replaces them here — a books table in this file would be a second
-- source of truth for a domain that already has one.
-- ═══════════════════════════════════════════════════════════════════════════
