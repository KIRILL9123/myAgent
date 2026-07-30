import sqlite3
import json
import os
from datetime import datetime
from typing import Any
from contextlib import contextmanager

DB_PATH = os.environ.get("DATABASE_PATH") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "home_agent.db")

def _get_connection():
    # Check_same_thread=False allows FastAPI to use it across async threads
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@contextmanager
def get_db_connection():
    """Context manager for SQLite connections to prevent resource leaks."""
    conn = _get_connection()
    try:
        yield conn
    finally:
        conn.close()

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

def init_db():
    """Apply pending schema migrations."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))")

        applied = {row[0] for row in cursor.execute("SELECT version FROM schema_migrations").fetchall()}

        files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
        for fname in files:
            version = int(fname.split("_", 1)[0])
            if version in applied:
                continue
            path = os.path.join(MIGRATIONS_DIR, fname)
            sql = open(path, "r", encoding="utf-8").read()
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                try:
                    cursor.execute(stmt)
                except sqlite3.OperationalError as e:
                    # Allow "duplicate column" on ALTER TABLE ADD COLUMN
                    if "ALTER TABLE" in stmt and "duplicate column" in str(e).lower():
                        continue
                    raise
            cursor.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version,))
            conn.commit()
            print(f"[MIGRATION] Applied {fname}")

        conn.commit()

# ─── Conversation Methods ──────────────────────────────────────────────────────

def save_message(
    session_id: str,
    role: str,
    content: str = "",
    tool_calls: list[dict] | None = None,
    name: str | None = None,
    tool_call_id: str | None = None,
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        cursor.execute(
            "INSERT INTO conversations (session_id, role, content, tool_calls, name, tool_call_id) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, role, content, tool_calls_json, name, tool_call_id)
        )
        conn.commit()

def get_history(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Fetch latest messages, then reverse to chronological order
        cursor.execute(
            "SELECT role, content, tool_calls, name, tool_call_id FROM conversations WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
            (session_id, limit)
        )
        rows = cursor.fetchall()

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

import secrets

def save_pending_action(session_id: str, action_name: str, args: dict[str, Any],
                         source_channel: str = "web", chat_id: str = "",
                         telegram_message_id: int | None = None) -> tuple[int, str]:
    nonce = secrets.token_urlsafe(16)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        args_json = json.dumps(args)
        cursor.execute(
            """
            INSERT INTO pending_actions (session_id, action_name, args, status, nonce_hash,
                                         source_channel, chat_id, telegram_message_id)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET 
                action_name=excluded.action_name,
                args=excluded.args,
                status='pending',
                nonce_hash=excluded.nonce_hash,
                source_channel=excluded.source_channel,
                chat_id=excluded.chat_id,
                telegram_message_id=excluded.telegram_message_id,
                created_at=CURRENT_TIMESTAMP
            """,
            (session_id, action_name, args_json, nonce,
             source_channel, chat_id, telegram_message_id)
        )
        conn.commit()
        cursor.execute("SELECT rowid FROM pending_actions WHERE session_id=?", (session_id,))
        row = cursor.fetchone()
        return (row[0], nonce) if row else (0, nonce)

def get_pending_action(session_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COALESCE(id, rowid) AS id, session_id, action_name, args, status, nonce_hash,
                      source_channel, chat_id, telegram_message_id, expires_at
               FROM pending_actions WHERE session_id = ? AND status = 'pending'""",
            (session_id,)
        )
        row = cursor.fetchone()

    if row:
        return _pending_row(row)
    return None

def delete_pending_action(session_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_actions WHERE session_id = ?", (session_id,))
        conn.commit()

def find_pending_by_nonce(nonce: str, chat_id: str = "") -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COALESCE(id, rowid) AS id, session_id, action_name, args, status, nonce_hash,
                      source_channel, chat_id, telegram_message_id, expires_at
               FROM pending_actions
               WHERE nonce_hash = ? AND status = 'pending'
               AND (expires_at IS NULL OR expires_at > datetime('now'))""",
            (nonce,)
        )
        row = cursor.fetchone()
    if not row:
        return None
    row_dict = _pending_row(row)
    if chat_id and str(row_dict.get("chat_id", "")) != str(chat_id):
        return None
    return row_dict

def claim_pending_action(action_id: int, nonce: str, chat_id: str = "") -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE pending_actions SET status='executing'
               WHERE rowid=? AND nonce_hash=? AND status='pending'
               AND (expires_at IS NULL OR expires_at > datetime('now'))""",
            (action_id, nonce)
        )
        if cursor.rowcount == 0:
            return None
        conn.commit()
        cursor.execute(
            """SELECT COALESCE(id, rowid) AS id, session_id, action_name, args, status, nonce_hash,
                      source_channel, chat_id, telegram_message_id, expires_at
               FROM pending_actions WHERE rowid=?""",
            (action_id,)
        )
        row = cursor.fetchone()
    return _pending_row(row) if row else None

def finalize_pending_action(action_id: int, status: str, error: str = ""):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_actions SET status=? WHERE rowid=?", (status, action_id)
        )
        conn.commit()

def _pending_row(row) -> dict[str, Any]:
    args = {}
    if row[3]:
        try:
            args = json.loads(row[3])
        except json.JSONDecodeError:
            pass
    return {
        "id": row[0], "session_id": row[1], "action": row[2], "args": args,
        "status": row[4], "nonce_hash": row[5], "source_channel": row[6],
        "chat_id": row[7], "telegram_message_id": row[8], "expires_at": row[9],
    }

# ─── Mail Sync State Methods ───────────────────────────────────────────────────

def get_last_seen_uid(account: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_seen_uid FROM mail_sync_state WHERE account = ?", (account,))
        row = cursor.fetchone()
    return row[0] if row else 0

def update_last_seen_uid(account: str, uid: int):
    with get_db_connection() as conn:
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
