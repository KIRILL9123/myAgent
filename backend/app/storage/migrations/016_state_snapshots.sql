CREATE TABLE IF NOT EXISTS state_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL UNIQUE,
    generated_at TEXT NOT NULL,
    health TEXT NOT NULL CHECK (health IN ('clear', 'watch', 'attention')),
    headline TEXT NOT NULL,
    counts_json TEXT NOT NULL DEFAULT '{}',
    alerts_json TEXT NOT NULL DEFAULT '[]',
    snapshot_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_state_snapshots_date
    ON state_snapshots(snapshot_date DESC);
