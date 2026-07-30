-- personal.db — unified personal-tracking database schema (v1)
-- ---------------------------------------------------------------------------
-- SoT for the user's personal-tracking domains. The DB is the source of truth;
-- the xlsx files are generated *views/snapshots* (see render_snapshot.py),
-- kept as a visual backup + mistake-finding aid. Long-term backup of the
-- underlying files is Time Machine's job, not the snapshot's.
--
-- Modeled on:
--   data/<instance>/library/db/schema.sql    (books/loans/lists pattern)
--   src/tools/roadmap_tools/                 (write-safety + discovery conventions)
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
-- DOMAIN: books — NOT IN THIS DB
-- Zotero is the source of truth for book data. This file holds no books, loans,
-- lists, list_items or book_snapshots tables and no v_book_stats view; reading
-- lists are Zotero collections, ownership is the Shelved tag, and the library
-- xlsx is rendered from tools/zotero/zotero_export.py.
-- Nothing replaces them here — a books table in this file would be a second
-- source of truth for a domain that already has one.
-- ═══════════════════════════════════════════════════════════════════════════
