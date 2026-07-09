import sqlite3
import json
import os
from datetime import datetime
from typing import Any

DB_PATH = os.environ.get("DATABASE_PATH") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "home_agent.db")

def _get_connection():
    # Check_same_thread=False allows FastAPI to use it across async threads
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """Create the necessary tables if they do not exist."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            tool_calls TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_actions (
            session_id TEXT PRIMARY KEY,
            action_name TEXT NOT NULL,
            args TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mail_sync_state (
            account TEXT PRIMARY KEY,
            last_seen_uid INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category) REFERENCES categories(name)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS countdowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target_date DATE NOT NULL,
            category TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            source_conversation_id INTEGER,
            confidence REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending_approval',
            FOREIGN KEY (source_conversation_id) REFERENCES conversations(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_a_id INTEGER NOT NULL,
            fact_b_id INTEGER NOT NULL,
            relation_type TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fact_a_id) REFERENCES user_facts(id) ON DELETE CASCADE,
            FOREIGN KEY (fact_b_id) REFERENCES user_facts(id) ON DELETE CASCADE
        )
    ''')

    # Seed default categories if none exist
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ("Еда", "expense"),
            ("Транспорт/Бензин", "expense"),
            ("Авто (запчасти/ремонт)", "expense"),
            ("Гейминг/Хобби", "expense"),
            ("Подписки", "expense"),
            ("Разное", "expense"),
            ("Зарплата/Стипендия", "income"),
            ("Фриланс/Разработка", "income"),
            ("Продажа вещей", "income")
        ]
        cursor.executemany("INSERT INTO categories (name, type) VALUES (?, ?)", default_categories)

    # Migration: Add merged_into_id column to user_facts if it doesn't exist
    try:
        cursor.execute("ALTER TABLE user_facts ADD COLUMN merged_into_id INTEGER REFERENCES user_facts(id)")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN tool_call_id TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

# ─── Conversation Methods ──────────────────────────────────────────────────────

def save_message(
    session_id: str,
    role: str,
    content: str = "",
    tool_calls: list[dict] | None = None,
    name: str | None = None,
    tool_call_id: str | None = None,
):
    conn = _get_connection()
    cursor = conn.cursor()
    tool_calls_json = json.dumps(tool_calls) if tool_calls else None
    cursor.execute(
        "INSERT INTO conversations (session_id, role, content, tool_calls, name, tool_call_id) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, role, content, tool_calls_json, name, tool_call_id)
    )
    conn.commit()
    conn.close()

def get_history(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    # Fetch latest messages, then reverse to chronological order
    cursor.execute(
        "SELECT role, content, tool_calls, name, tool_call_id FROM conversations WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
        (session_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in reversed(rows):
        role, content, tool_calls_json, name, tool_call_id = row
        msg = {"role": role, "content": content or ""}
        if tool_calls_json:
            try:
                tcalls = json.loads(tool_calls_json)
                # Normalize function arguments from JSON string to dictionary
                # because Ollama requires arguments to be a dictionary inside history
                for tc in tcalls:
                    if "function" in tc and "arguments" in tc["function"]:
                        args = tc["function"]["arguments"]
                        if isinstance(args, str):
                            try:
                                tc["function"]["arguments"] = json.loads(args)
                            except json.JSONDecodeError:
                                pass
                msg["tool_calls"] = tcalls
            except json.JSONDecodeError:
                pass
        if name:
            msg["name"] = name
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        history.append(msg)
    
    return history

# ─── Pending Action Methods ────────────────────────────────────────────────────

def save_pending_action(session_id: str, action_name: str, args: dict[str, Any]):
    conn = _get_connection()
    cursor = conn.cursor()
    args_json = json.dumps(args)
    cursor.execute(
        """
        INSERT INTO pending_actions (session_id, action_name, args, status)
        VALUES (?, ?, ?, 'pending')
        ON CONFLICT(session_id) DO UPDATE SET 
            action_name=excluded.action_name,
            args=excluded.args,
            status='pending',
            created_at=CURRENT_TIMESTAMP
        """,
        (session_id, action_name, args_json)
    )
    conn.commit()
    conn.close()

def get_pending_action(session_id: str) -> dict[str, Any] | None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT action_name, args FROM pending_actions WHERE session_id = ? AND status = 'pending'",
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        action_name, args_json = row
        args = {}
        if args_json:
            try:
                args = json.loads(args_json)
            except json.JSONDecodeError:
                pass
        return {"action": action_name, "args": args}
    return None

def delete_pending_action(session_id: str):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_actions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# ─── Mail Sync State Methods ───────────────────────────────────────────────────

def get_last_seen_uid(account: str) -> int:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_seen_uid FROM mail_sync_state WHERE account = ?", (account,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def update_last_seen_uid(account: str, uid: int):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mail_sync_state (account, last_seen_uid)
        VALUES (?, ?)
        ON CONFLICT(account) DO UPDATE SET last_seen_uid=excluded.last_seen_uid
        """,
        (account, uid)
    )
    conn.commit()
    conn.close()
