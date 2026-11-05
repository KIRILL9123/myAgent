CREATE TABLE IF NOT EXISTS error_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'fixing', 'fixed', 'verified', 'closed')),
    component TEXT,
    correlation_id TEXT,
    error_type TEXT,
    context_json TEXT NOT NULL DEFAULT '{}',
    fix_reference TEXT,
    verification_result TEXT,
    resolution_note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_error_reports_status_updated
    ON error_reports(status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_error_reports_correlation
    ON error_reports(correlation_id);
