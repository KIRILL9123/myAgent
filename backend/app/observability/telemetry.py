import contextvars
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from backend.app.storage.db import get_db_connection


_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def set_correlation_id(value: str) -> contextvars.Token:
    return _correlation_id.set(value)


def reset_correlation_id(token: contextvars.Token) -> None:
    _correlation_id.reset(token)


def get_correlation_id() -> str:
    return _correlation_id.get()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Keep telemetry metadata useful without persisting message contents or secrets."""
    if not payload:
        return {}
    allowed: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in {"content", "message", "body", "args", "token", "key", "secret"}:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            allowed[key] = value
    return allowed


_telemetry_logger = logging.getLogger("home_agent_telemetry")
_telemetry_logger.setLevel(logging.INFO)
if not _telemetry_logger.handlers:
    log_dir = Path(__file__).resolve().parents[3] / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        str(log_dir / "telemetry.jsonl"), maxBytes=5 * 1024 * 1024,
        backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    _telemetry_logger.addHandler(handler)


def record_event(event_type: str, component: str, status: str,
                 duration_ms: float | None = None,
                 payload: dict[str, Any] | None = None,
                 correlation_id: str | None = None) -> None:
    event_payload = _safe_payload(payload)
    event = {
        "correlation_id": correlation_id or get_correlation_id() or None,
        "event_type": event_type,
        "component": component,
        "status": status,
        "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
        "payload": event_payload,
        "created_at": _now(),
    }
    _telemetry_logger.info(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
    try:
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO observability_events
                   (correlation_id, event_type, component, status, duration_ms, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event["correlation_id"], event_type, component, status,
                 event["duration_ms"], json.dumps(event_payload, ensure_ascii=False), event["created_at"]),
            )
            conn.commit()
    except Exception as exc:
        # Telemetry must never make the user's request fail.
        _telemetry_logger.error(json.dumps({"event_type": "telemetry_write_error", "error": type(exc).__name__}))


def elapsed_ms(start: float) -> float:
    return (time.monotonic() - start) * 1000


def get_telemetry_summary(hours: int = 24) -> dict[str, Any]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT event_type, component, status, COUNT(*), AVG(duration_ms)
               FROM observability_events
               WHERE created_at >= datetime('now', ?)
               GROUP BY event_type, component, status
               ORDER BY event_type, component, status""",
            (f"-{max(1, min(hours, 168))} hours",),
        ).fetchall()
        total = conn.execute(
            """SELECT COUNT(*), SUM(CASE WHEN status IN ('error', 'failed', '4xx', '5xx') THEN 1 ELSE 0 END)
               FROM observability_events
               WHERE created_at >= datetime('now', ?)""",
            (f"-{max(1, min(hours, 168))} hours",),
        ).fetchone()
    return {
        "hours": max(1, min(hours, 168)),
        "total_events": total[0] or 0,
        "error_events": total[1] or 0,
        "groups": [
            {"event_type": row[0], "component": row[1], "status": row[2],
             "count": row[3], "avg_duration_ms": round(row[4], 2) if row[4] is not None else None}
            for row in rows
        ],
    }


def get_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT id, correlation_id, event_type, component, status,
                      duration_ms, payload_json, created_at
               FROM observability_events ORDER BY id DESC LIMIT ?""",
            (max(1, min(limit, 200)),),
        ).fetchall()
    events = []
    for row in rows:
        try:
            payload = json.loads(row[6]) if row[6] else {}
        except json.JSONDecodeError:
            payload = {}
        events.append({
            "id": row[0], "correlation_id": row[1], "event_type": row[2],
            "component": row[3], "status": row[4], "duration_ms": row[5],
            "payload": payload, "created_at": row[7],
        })
    return events
