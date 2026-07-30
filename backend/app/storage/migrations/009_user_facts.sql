CREATE TABLE IF NOT EXISTS user_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    source_conversation_id INTEGER,
    confidence REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending_approval',
    merged_into_id INTEGER,
    last_confirmed_at DATETIME,
    valid_from DATETIME,
    valid_to DATETIME,
    source_type TEXT,
    FOREIGN KEY (source_conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (merged_into_id) REFERENCES user_facts(id)
);
