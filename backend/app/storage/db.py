import sqlite3
import json
import os
from datetime import datetime
from typing import Any
from contextlib import contextmanager

DB_PATH = os.environ.get("DATABASE_PATH") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "home_agent.db")
PENDING_ACTION_TTL_MINUTES = 15

def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_db_connection() -> Any:
    """Context manager for SQLite connections to prevent resource leaks."""
    conn = _get_connection()
    try:
        yield conn
    finally:
        conn.close()

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

def init_db() -> None:
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
) -> None:
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
                                         source_channel, chat_id, telegram_message_id, expires_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?,
                    datetime('now', '+' || ? || ' minutes'))
            ON CONFLICT(session_id) DO UPDATE SET 
                action_name=excluded.action_name,
                args=excluded.args,
                status='pending',
                nonce_hash=excluded.nonce_hash,
                source_channel=excluded.source_channel,
                chat_id=excluded.chat_id,
                telegram_message_id=excluded.telegram_message_id,
                expires_at=excluded.expires_at,
                failure_reason=NULL,
                claimed_at=NULL,
                resolved_at=NULL,
                created_at=CURRENT_TIMESTAMP
            """,
            (session_id, action_name, args_json, nonce,
             source_channel, chat_id, telegram_message_id, PENDING_ACTION_TTL_MINUTES)
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
                      source_channel, chat_id, telegram_message_id, expires_at,
                      failure_reason, claimed_at, resolved_at
               FROM pending_actions
               WHERE session_id = ? AND status = 'pending'
                 AND (expires_at IS NULL OR expires_at > datetime('now'))""",
            (session_id,)
        )
        row = cursor.fetchone()

    if row:
        return _pending_row(row)
    return None

def delete_pending_action(session_id: str) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_actions WHERE session_id = ?", (session_id,))
        conn.commit()

def find_pending_by_nonce(nonce: str, chat_id: str = "",
                          source_channel: str | None = None,
                          action_id: int | None = None,
                          session_id: str | None = None) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        clauses = [
            "nonce_hash = ?",
            "status = 'pending'",
            "(expires_at IS NULL OR expires_at > datetime('now'))",
        ]
        params: list[Any] = [nonce]
        if source_channel is not None:
            clauses.append("source_channel = ?")
            params.append(source_channel)
        if chat_id:
            clauses.append("COALESCE(chat_id, '') = ?")
            params.append(str(chat_id))
        if action_id is not None:
            clauses.append("COALESCE(id, rowid) = ?")
            params.append(action_id)
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        cursor.execute(
            f"""SELECT COALESCE(id, rowid) AS id, session_id, action_name, args, status, nonce_hash,
                      source_channel, chat_id, telegram_message_id, expires_at,
                      failure_reason, claimed_at, resolved_at
               FROM pending_actions
               WHERE {' AND '.join(clauses)}""",
            params,
        )
        row = cursor.fetchone()
    return _pending_row(row) if row else None

def claim_pending_action(action_id: int, nonce: str, chat_id: str = "",
                         source_channel: str = "web",
                         session_id: str | None = None) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        session_clause = "" if session_id is None else " AND session_id = ?"
        cursor.execute(
            f"""UPDATE pending_actions
               SET status='executing', claimed_at=CURRENT_TIMESTAMP
               WHERE COALESCE(id, rowid)=? AND nonce_hash=? AND status='pending'
               AND source_channel=? AND COALESCE(chat_id, '')=?
               {session_clause}
               AND (expires_at IS NULL OR expires_at > datetime('now'))""",
            [action_id, nonce, source_channel, str(chat_id), *([session_id] if session_id is not None else [])],
        )
        if cursor.rowcount == 0:
            return None
        conn.commit()
        cursor.execute(
            """SELECT COALESCE(id, rowid) AS id, session_id, action_name, args, status, nonce_hash,
                      source_channel, chat_id, telegram_message_id, expires_at,
                      failure_reason, claimed_at, resolved_at
               FROM pending_actions WHERE COALESCE(id, rowid)=?""",
            (action_id,)
        )
        row = cursor.fetchone()
    return _pending_row(row) if row else None

def finalize_pending_action(action_id: int, status: str, error: str = "",
                            source_channel: str | None = None,
                            chat_id: str = "",
                            session_id: str | None = None) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        clauses = ["COALESCE(id, rowid)=?"]
        params: list[Any] = [status, error or None, action_id]
        if source_channel is not None:
            clauses.extend([
                "status = 'executing'",
                "source_channel = ?",
                "COALESCE(chat_id, '') = ?",
            ])
            params.extend([source_channel, str(chat_id)])
            if session_id is not None:
                clauses.append("session_id = ?")
                params.append(session_id)
        cursor.execute(
            f"""UPDATE pending_actions
               SET status=?, failure_reason=?, resolved_at=CURRENT_TIMESTAMP
               WHERE {' AND '.join(clauses)}""",
            params,
        )
        conn.commit()
        return cursor.rowcount == 1

def cancel_pending_action(action_id: int, nonce: str, source_channel: str,
                          chat_id: str = "", session_id: str | None = None) -> bool:
    """Atomically cancel a still-pending action owned by this identity."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        session_clause = "" if session_id is None else " AND session_id = ?"
        params: list[Any] = [action_id, nonce, source_channel, str(chat_id)]
        if session_id is not None:
            params.append(session_id)
        cursor.execute(
            f"""UPDATE pending_actions
               SET status='cancelled', failure_reason=NULL,
                   resolved_at=CURRENT_TIMESTAMP
               WHERE COALESCE(id, rowid)=? AND nonce_hash=?
                 AND status='pending'
                 AND source_channel=? AND COALESCE(chat_id, '')=?
                 {session_clause}
                 AND (expires_at IS NULL OR expires_at > datetime('now'))""",
            params,
        )
        conn.commit()
        return cursor.rowcount == 1

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
        "failure_reason": row[10], "claimed_at": row[11], "resolved_at": row[12],
    }

# ─── Mail Sync State Methods ───────────────────────────────────────────────────

def get_last_seen_uid(account: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_seen_uid FROM mail_sync_state WHERE account = ?", (account,))
        row = cursor.fetchone()
    return row[0] if row else 0

def update_last_seen_uid(account: str, uid: int) -> None:
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
