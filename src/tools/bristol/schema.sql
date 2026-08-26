-- schema.sql — generated snapshot of the tickets.db schema.
-- Auto-applied by app.py on launch (idempotent: every statement is IF NOT EXISTS).
-- This is a GENERATED faithful copy of the live schema; regenerate if the DB evolves.

CREATE TABLE IF NOT EXISTS epic (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_id           INTEGER,                   -- optional strategic grouping
    name               TEXT    NOT NULL,
    type               TEXT,                      -- "Epic (bounded)", "Epic (unbounded)", …
    status             TEXT    NOT NULL DEFAULT 'not started',
    owner              TEXT,                      -- who executes (e.g. "chief_of_staff")
    approver           TEXT,                      -- who approves structural changes
    description        TEXT,                      -- "Why this epic exists" narrative
    hard_constraints   TEXT,                      -- Hard constraints section (markdown)
    definition_of_done TEXT,                      -- Definition of done (markdown)
    detail_path        TEXT,                      -- optional path to an external detail/plan doc, resolved via /config
    next_action        TEXT, created_at TEXT, closed_at TEXT,                      -- current next-action note
    FOREIGN KEY (theme_id) REFERENCES theme (id)
);

-- (There is no `epic_log` table and no `handoff` table. Both were per-agent
-- narrative state, which is exactly what the board replaces: a session's
-- carry-forward is a `doing` card with an owner and a pressure, and to-dos/done
-- are ordinary issues. schema_guard._drop_retired_handoff removes any surviving
-- `handoff` table on launch.)

CREATE TABLE IF NOT EXISTS issue_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL,
    author     TEXT    NOT NULL,    -- agent slug, or 'user' / 'system'
    body       TEXT    NOT NULL,    -- one brief progress note
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),  -- ISO-8601 UTC
    FOREIGN KEY (task_id) REFERENCES task (id)
);
-- NOTE: the legacy `history` audit table (events like 'edited'/'moved to done')
-- was consolidated into issue_log (author='system') and dropped — see
-- ui/schema_guard.py:_consolidate_legacy_history. One visible per-issue log.

-- task_link — the relations a ticket carries: to another ticket, or to an
-- external address. One table, two kinds, because everything except the target
-- is shared (owner task, author, timestamp, delete semantics) and the UI renders
-- them as one ordered list above the log.
--
--   kind='issue' — a link between two tickets, carrying a dep_type that says
--     what the relation means: 'related' (they belong together) or 'blocks'
--     (task_id must be done before other_id may start). Either way it is ONE
--     edge: a reader asks `WHERE task_id=? OR other_id=?` and sees the link
--     from either end, and a single DELETE removes it from both. Two mirrored
--     rows were rejected precisely because they can half-delete into a one-way
--     link. A 'related' row is normalized so task_id = MIN(a,b) and other_id =
--     MAX(a,b); a 'blocks' row keeps its direction instead, and renders as
--     "blocks #other" on one card and "blocked by #task" on the other.
--
--   kind='uri' — a link from one ticket to an address: a web URL, a
--     `zotero://` citation, an `obsidian://` note, or a bare filesystem path.
--     The viewer hands whatever is stored to the OS to open, so no scheme,
--     vault name or user path is ever encoded in the tool.
--
-- Why it exists: a ticket description must stay in its Build/Fix template, so
-- provenance ("this came from that review", "this relates to that note") had
-- nowhere to live and was being written into the description as an off-template
-- Source header. This table is where it belongs.
CREATE TABLE IF NOT EXISTS task_link (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT    NOT NULL,          -- 'issue' | 'uri'
    task_id    INTEGER NOT NULL,          -- related: MIN(a,b); blocks: the blocker; uri: the owning task
    other_id   INTEGER,                   -- related: MAX(a,b); blocks: the blocked ticket; NULL for uri
    dep_type   TEXT    NOT NULL DEFAULT 'related',  -- issue: 'related' | 'blocks'
    uri        TEXT,                      -- uri: the target address; NULL for issue
    label      TEXT,                      -- uri: optional human caption
    author     TEXT,                      -- agent slug, or 'user'
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (task_id)  REFERENCES task (id),
    FOREIGN KEY (other_id) REFERENCES task (id)
);
-- One row per ordered pair. A directed 'blocks' row means the pair could also
-- be written the other way round, so the writers check both orders before
-- inserting; this index is the backstop, not the whole constraint.
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_link_pair
    ON task_link (task_id, other_id) WHERE kind = 'issue';
CREATE INDEX IF NOT EXISTS idx_task_link_task  ON task_link (task_id);
CREATE INDEX IF NOT EXISTS idx_task_link_other ON task_link (other_id);

-- task_event — the mechanical change log. One row per changed task field:
-- field, new value, actor, timestamp. NOT a second state store — `task` holds
-- current state, this holds the moments it changed.
--
-- Every row is machine-written, by triggers, in a fixed grammar. No agent and
-- no person composes an entry, explains a change, or adds a reason; the moment
-- an entry carries prose it has become a narration of work rather than a record
-- of it. Title and description changes record only that they changed, never the
-- text, so the log never becomes a second copy of the ticket.
--
-- The triggers live in each writing connection's TEMP schema, created with that
-- connection's actor as a literal (see bristol/ui/schema_guard.py and
-- ticket_tools/ticket_write.py). Two readers: Bristol Tickets' Log pane, which
-- interleaves these with issue_log comments under one pair of filter
-- checkboxes, and the reports package, which measures cycle time and work-item
-- age from the status and stage rows.
CREATE TABLE IF NOT EXISTS task_event (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL,
    at         TEXT    NOT NULL,          -- ISO-8601 UTC, the moment of the change
    actor      TEXT,                      -- 'user' (Bristol Tickets) or an agent write signature
    field      TEXT    NOT NULL,          -- the task column that changed
    from_value TEXT,                      -- prior value (NULL on creation, or redacted)
    to_value   TEXT    NOT NULL,          -- new value; '(changed)' for title/description
    FOREIGN KEY (task_id) REFERENCES task (id)
);
CREATE INDEX IF NOT EXISTS idx_task_event_task ON task_event (task_id, at);

-- (There is no cross-agent `inbox` table. Cross-agent
-- suggestions are ordinary backlog cards — task.assignee = the target agent,
-- task.reporter = the originator — so they live in the same board the user
-- watches, visible and editable, instead of a separate hidden store.)

CREATE TABLE IF NOT EXISTS scope (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_id     INTEGER NOT NULL,
    version     TEXT    NOT NULL,   -- "v1", "v2", "Phase 0", "Phase 1", …
    label       TEXT,               -- short label, e.g. "proof of concept"
    description TEXT,               -- full scope description (markdown OK)
    FOREIGN KEY (epic_id) REFERENCES epic (id)
);

-- (There are no `sprint` / `sprint_task` tables. The board is full-Kanban: a
-- task's tab is task.stage (backlog | active | archive) rather than derived
-- from sprint membership, and manual order
-- is task.sort_order. schema_guard._migrate_stage_from_sprints backfills those
-- two columns from any old sprint membership and drops these tables on launch.)

CREATE TABLE IF NOT EXISTS task (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_id     INTEGER,
    scope_id    INTEGER,            -- optional: which scope this task belongs to
    title       TEXT    NOT NULL,
    description TEXT,
    status      TEXT    NOT NULL DEFAULT 'todo',      -- todo | doing | done (the board columns)
    pressure    INTEGER NOT NULL DEFAULT 0, estimate TEXT, created_at TEXT, updated_at TEXT, closed_at TEXT, assignee TEXT, reporter TEXT, story_points INTEGER DEFAULT 0,          -- pressure: 0-100 gestalt of how hard the card is pushing. A rating, not a rank. A dependency is a 'blocks' link, not a column here.
    record_type TEXT    NOT NULL DEFAULT 'build',     -- 'build' (Story + acceptance criteria) | 'fix' (Expected/Observed).
    stage       TEXT    NOT NULL DEFAULT 'backlog',   -- backlog | active | archive (which tab; orthogonal to status).
    sort_order  INTEGER NOT NULL DEFAULT 0,           -- manual drag-to-reorder position; lower = higher in its list.
    block_reason TEXT,                                -- NULL | dependency | decision | capability | transient.
                                                      -- What kind of thing has stopped the card, never which card:
                                                      -- 'dependency' is resolved live from the 'blocks' links, and the
                                                      -- prose belongs in an issue_log comment. (The retired
                                                      -- task.blocked / task.depends_on pair named the blocking card
                                                      -- here and went stale; that job is the link's.)
    FOREIGN KEY (epic_id)  REFERENCES epic  (id),
    FOREIGN KEY (scope_id) REFERENCES scope (id)
);

CREATE TABLE IF NOT EXISTS task_meta (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id      INTEGER NOT NULL,
    issue_type   TEXT,
    assignee     TEXT,
    reporter     TEXT,
    labels       TEXT,
    story_points INTEGER,
    due_date     TEXT,
    FOREIGN KEY (task_id) REFERENCES task (id)
);

CREATE TABLE IF NOT EXISTS theme (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    description    TEXT,                          -- theme body / goals text
    is_milestone   INTEGER NOT NULL DEFAULT 0     -- 1 if marked ★ milestone
);
