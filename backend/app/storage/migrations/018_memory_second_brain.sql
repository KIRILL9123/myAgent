ALTER TABLE user_facts ADD COLUMN approval_mode TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE user_facts ADD COLUMN provenance_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE user_facts ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS memory_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_search USING fts5(
    item_type UNINDEXED,
    item_id UNINDEXED,
    title,
    content,
    tags
);

CREATE INDEX IF NOT EXISTS idx_memory_notes_status_updated ON memory_notes(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_facts_status_category ON user_facts(status, category);
