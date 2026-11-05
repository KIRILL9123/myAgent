CREATE TABLE IF NOT EXISTS commitments (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT,
    status TEXT NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED', 'ACTIVE', 'COMPLETED', 'CANCELLED', 'EXPIRED')),
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    provenance_json TEXT NOT NULL DEFAULT '{}',
    source_type TEXT NOT NULL CHECK (source_type IN ('CHAT', 'EMAIL', 'DOCUMENT', 'CALENDAR')),
    source_ref TEXT,
    owner TEXT NOT NULL DEFAULT 'user',
    deadline_at TEXT,
    reminder_at TEXT,
    reminder_sent_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    activated_at TEXT,
    completed_at TEXT,
    cancelled_at TEXT,
    expired_at TEXT,
    approval_provenance_json TEXT,
    related_fact_ids_json TEXT NOT NULL DEFAULT '[]',
    related_calendar_event_ids_json TEXT NOT NULL DEFAULT '[]',
    conflicts_with_ids_json TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_commitments_status_deadline
    ON commitments(status, deadline_at);
CREATE INDEX IF NOT EXISTS idx_commitments_owner_status
    ON commitments(owner, status);

CREATE TABLE IF NOT EXISTS commitment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commitment_id TEXT NOT NULL REFERENCES commitments(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_commitment_events_commitment
    ON commitment_events(commitment_id, created_at);
