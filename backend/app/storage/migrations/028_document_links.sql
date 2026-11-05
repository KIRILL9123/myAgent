CREATE TABLE IF NOT EXISTS document_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK (target_type IN ('commitment', 'calendar_event', 'subscription')),
    target_id TEXT NOT NULL,
    target_label TEXT NOT NULL,
    relationship TEXT NOT NULL DEFAULT 'related',
    created_by TEXT NOT NULL DEFAULT 'web',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, target_type, target_id)
);

CREATE INDEX IF NOT EXISTS idx_document_links_document
    ON document_links(document_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_links_target
    ON document_links(target_type, target_id);
