CREATE TABLE IF NOT EXISTS observability_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT,
    event_type TEXT NOT NULL,
    component TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms REAL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_observability_events_created
    ON observability_events(created_at);
CREATE INDEX IF NOT EXISTS idx_observability_events_type_status
    ON observability_events(event_type, status);
CREATE INDEX IF NOT EXISTS idx_observability_events_correlation
    ON observability_events(correlation_id);
