-- Sauti Host SQLite schema. Shared file: claim it in the team room before editing.

-- W1: every confirmed farm sheet is a new version, never an in-place update,
-- so W5 can detect changes and we keep an audit of what Noor actually said.
CREATE TABLE IF NOT EXISTS farm_sheet_versions (
    version      INTEGER PRIMARY KEY AUTOINCREMENT,
    data         TEXT    NOT NULL,  -- FarmSheet as JSON
    content_hash TEXT    NOT NULL,  -- sha256 of the canonical JSON
    source       TEXT    NOT NULL,  -- e.g. 'w1_voice', 'w1_text'
    transcript   TEXT,              -- what Noor said, for audit
    created_at   TEXT    NOT NULL   -- ISO 8601 UTC
);
