"""Persistent error reports with an explicit remediation lifecycle."""

import json
from datetime import datetime, timezone
from typing import Any

from backend.app.storage.db import get_db_connection

STATUSES = ("new", "fixing", "fixed", "verified", "closed")
SEVERITIES = ("critical", "high", "medium", "low")
TRANSITIONS = {
    "new": "fixing",
    "fixing": "fixed",
    "fixed": "verified",
    "verified": "closed",
    "closed": None,
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_context(context: dict[str, Any] | None) -> dict[str, Any]:
    if not context:
        return {}
    safe: dict[str, Any] = {}
    blocked = {"content", "message", "body", "args", "token", "key", "secret", "password"}
    for key, value in context.items():
        if str(key).lower() in blocked:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)] = value
    return safe


def _row_to_report(row: Any) -> dict[str, Any]:
    try:
        context = json.loads(row[8]) if row[8] else {}
    except json.JSONDecodeError:
        context = {}
    return {
        "id": row[0], "title": row[1], "summary": row[2], "severity": row[3],
        "status": row[4], "component": row[5], "correlation_id": row[6],
        "error_type": row[7], "context": context, "fix_reference": row[9],
        "verification_result": row[10], "resolution_note": row[11],
        "created_at": row[12], "updated_at": row[13], "resolved_at": row[14],
    }


def _select_clause(status: str | None = None) -> tuple[str, list[Any]]:
    if status is None or status == "all":
        return "", []
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    return " WHERE status = ?", [status]


def create_error_report(
    title: str,
    summary: str = "",
    *,
    severity: str = "medium",
    component: str | None = None,
    correlation_id: str | None = None,
    error_type: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = str(title).strip()
    if not title or len(title) > 240:
        raise ValueError("title must contain 1-240 characters")
    if severity not in SEVERITIES:
        raise ValueError(f"severity must be one of {SEVERITIES}")
    with get_db_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO error_reports
               (title, summary, severity, component, correlation_id, error_type, context_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, str(summary)[:4000], severity, component, correlation_id, error_type,
             json.dumps(_safe_context(context), ensure_ascii=False)),
        )
        conn.commit()
        report_id = cursor.lastrowid
    return get_error_report(report_id)  # type: ignore[arg-type]


def get_error_report(report_id: int) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT id, title, summary, severity, status, component, correlation_id,
                      error_type, context_json, fix_reference, verification_result,
                      resolution_note, created_at, updated_at, resolved_at
               FROM error_reports WHERE id = ?""",
            (report_id,),
        ).fetchone()
    return _row_to_report(row) if row else None


def list_error_reports(status: str | None = None, limit: int = 100) -> dict[str, Any]:
    where, params = _select_clause(status)
    limit = max(1, min(int(limit), 200))
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""SELECT id, title, summary, severity, status, component, correlation_id,
                       error_type, context_json, fix_reference, verification_result,
                       resolution_note, created_at, updated_at, resolved_at
                FROM error_reports{where} ORDER BY CASE status WHEN 'new' THEN 0 WHEN 'fixing' THEN 1 WHEN 'fixed' THEN 2 WHEN 'verified' THEN 3 ELSE 4 END, updated_at DESC LIMIT ?""",
            (*params, limit),
        ).fetchall()
        counts = conn.execute(
            "SELECT status, COUNT(*) FROM error_reports GROUP BY status"
        ).fetchall()
    summary = {value: 0 for value in STATUSES}
    summary.update({row[0]: row[1] for row in counts})
    return {"reports": [_row_to_report(row) for row in rows], "summary": summary}


def update_error_report(
    report_id: int,
    status: str,
    *,
    fix_reference: str | None = None,
    verification_result: str | None = None,
    resolution_note: str | None = None,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    current = get_error_report(report_id)
    if not current:
        raise ValueError("error report not found")
    if status != current["status"] and TRANSITIONS[current["status"]] != status:
        raise ValueError(f"invalid transition: {current['status']} -> {status}")
    now = _now()
    resolved_at = now if status == "closed" else current["resolved_at"]
    with get_db_connection() as conn:
        conn.execute(
            """UPDATE error_reports
               SET status = ?, fix_reference = COALESCE(?, fix_reference),
                   verification_result = COALESCE(?, verification_result),
                   resolution_note = COALESCE(?, resolution_note),
                   updated_at = ?, resolved_at = ?
               WHERE id = ?""",
            (status, fix_reference, verification_result, resolution_note, now, resolved_at, report_id),
        )
        conn.commit()
    return get_error_report(report_id)  # type: ignore[return-value]
