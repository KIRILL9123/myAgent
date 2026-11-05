CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tool_calls TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
