CREATE TABLE IF NOT EXISTS approval_requests (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('FACT', 'COMMITMENT', 'ACTION')),
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    source_channel TEXT NOT NULL DEFAULT 'web',
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'FAILED')),
    resolution_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT,
    UNIQUE(kind, source_id)
);

CREATE INDEX IF NOT EXISTS idx_approval_requests_status_created
    ON approval_requests(status, created_at);
