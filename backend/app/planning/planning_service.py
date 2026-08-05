"""Application services for the personal Goals → Projects → Tasks hierarchy.

Goals and projects are explicit user records. Existing commitments remain the
single source of truth for tasks; this module only adds an optional project
relationship and never creates calendar or finance side effects.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from backend.app.storage.db import get_db_connection

GOAL_STATUSES = {"ACTIVE", "COMPLETED", "PAUSED", "ARCHIVED"}
PROJECT_STATUSES = {"PLANNED", "ACTIVE", "COMPLETED", "PAUSED", "ARCHIVED"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _date(value: str | None, field: str) -> str | None:
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD)") from exc


def _json(value: Any, default: Any) -> str:
    return json.dumps(default if value is None else value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except json.JSONDecodeError:
        return default


def _goal(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = ("id", "title", "description", "status", "target_date", "provenance", "created_at", "updated_at", "completed_at")
    result = dict(zip(keys, row))
    result["provenance"] = _loads(result["provenance"], {})
    return result


def _project(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = ("id", "goal_id", "title", "description", "status", "start_date", "target_date", "provenance", "created_at", "updated_at", "completed_at")
    result = dict(zip(keys, row))
    result["provenance"] = _loads(result["provenance"], {})
    return result


def _decision(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = ("id", "title", "decision_text", "rationale", "alternatives", "status", "decided_at", "review_at", "source_type", "provenance", "created_at", "updated_at")
    result = dict(zip(keys, row))
    result["alternatives"] = _loads(result["alternatives"], [])
    result["provenance"] = _loads(result["provenance"], {})
    return result


def _get_goal(goal_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT id, title, description, status, target_date, provenance_json, created_at, updated_at, completed_at FROM goals WHERE id = ?", (goal_id,)).fetchone()
    return _goal(row) if row else None


def create_goal(title: str, description: str | None = None, target_date: str | None = None,
                status: str = "ACTIVE", provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    title = title.strip()
    status = status.upper()
    if not title:
        raise ValueError("title must not be empty")
    if status not in GOAL_STATUSES:
        raise ValueError(f"status must be one of {sorted(GOAL_STATUSES)}")
    target_date = _date(target_date, "target_date")
    goal_id, now = str(uuid.uuid4()), _now()
    with get_db_connection() as conn:
        conn.execute("INSERT INTO goals (id, title, description, status, target_date, provenance_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (goal_id, title, description, status, target_date, _json(provenance, {}), now, now))
        conn.commit()
    return _get_goal(goal_id)  # type: ignore[return-value]


def list_goals(status: str | None = None) -> list[dict[str, Any]]:
    if status and status.upper() not in GOAL_STATUSES:
        raise ValueError(f"status must be one of {sorted(GOAL_STATUSES)}")
    clause = "WHERE status = ?" if status else ""
    params = (status.upper(),) if status else ()
    with get_db_connection() as conn:
        rows = conn.execute(f"SELECT id, title, description, status, target_date, provenance_json, created_at, updated_at, completed_at FROM goals {clause} ORDER BY CASE WHEN target_date IS NULL THEN 1 ELSE 0 END, target_date, created_at", params).fetchall()
    return [_goal(row) for row in rows]


def update_goal(goal_id: str, **changes: Any) -> dict[str, Any]:
    current = _get_goal(goal_id)
    if not current:
        raise KeyError("goal not found")
    allowed = {"title", "description", "target_date", "status"}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"unsupported fields: {sorted(unknown)}")
    if "title" in changes:
        changes["title"] = str(changes["title"]).strip()
        if not changes["title"]:
            raise ValueError("title must not be empty")
    if "status" in changes:
        changes["status"] = str(changes["status"]).upper()
        if changes["status"] not in GOAL_STATUSES:
            raise ValueError(f"status must be one of {sorted(GOAL_STATUSES)}")
    if "target_date" in changes:
        changes["target_date"] = _date(changes["target_date"], "target_date")
    if not changes:
        return current
    now = _now()
    if changes.get("status") == "COMPLETED":
        changes["completed_at"] = now
    assignments = ", ".join(f"{key} = ?" for key in changes)
    with get_db_connection() as conn:
        conn.execute(f"UPDATE goals SET {assignments}, updated_at = ? WHERE id = ?", [*changes.values(), now, goal_id])
        conn.commit()
    return _get_goal(goal_id)  # type: ignore[return-value]


def _get_project(project_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT id, goal_id, title, description, status, start_date, target_date, provenance_json, created_at, updated_at, completed_at FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project(row) if row else None


def create_project(title: str, goal_id: str | None = None, description: str | None = None,
                   status: str = "PLANNED", start_date: str | None = None, target_date: str | None = None,
                   provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    title, status = title.strip(), status.upper()
    if not title:
        raise ValueError("title must not be empty")
    if status not in PROJECT_STATUSES:
        raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
    start_date, target_date = _date(start_date, "start_date"), _date(target_date, "target_date")
    if start_date and target_date and start_date > target_date:
        raise ValueError("start_date must be before target_date")
    project_id, now = str(uuid.uuid4()), _now()
    with get_db_connection() as conn:
        if goal_id and not conn.execute("SELECT 1 FROM goals WHERE id = ?", (goal_id,)).fetchone():
            raise KeyError("goal not found")
        conn.execute("INSERT INTO projects (id, goal_id, title, description, status, start_date, target_date, provenance_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (project_id, goal_id, title, description, status, start_date, target_date, _json(provenance, {}), now, now))
        conn.commit()
    return _get_project(project_id)  # type: ignore[return-value]


def list_projects(status: str | None = None, goal_id: str | None = None) -> list[dict[str, Any]]:
    if status and status.upper() not in PROJECT_STATUSES:
        raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
    clauses, params = [], []
    if status:
        clauses.append("status = ?"); params.append(status.upper())
    if goal_id:
        clauses.append("goal_id = ?"); params.append(goal_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db_connection() as conn:
        rows = conn.execute(f"SELECT id, goal_id, title, description, status, start_date, target_date, provenance_json, created_at, updated_at, completed_at FROM projects {where} ORDER BY CASE WHEN target_date IS NULL THEN 1 ELSE 0 END, target_date, created_at", params).fetchall()
    return [_project(row) for row in rows]


def update_project(project_id: str, **changes: Any) -> dict[str, Any]:
    current = _get_project(project_id)
    if not current:
        raise KeyError("project not found")
    allowed = {"goal_id", "title", "description", "status", "start_date", "target_date"}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"unsupported fields: {sorted(unknown)}")
    if "title" in changes:
        changes["title"] = str(changes["title"]).strip()
        if not changes["title"]:
            raise ValueError("title must not be empty")
    if "status" in changes:
        changes["status"] = str(changes["status"]).upper()
        if changes["status"] not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
    for key in ("start_date", "target_date"):
        if key in changes:
            changes[key] = _date(changes[key], key)
    goal_id = changes.get("goal_id", current["goal_id"])
    with get_db_connection() as conn:
        if goal_id and not conn.execute("SELECT 1 FROM goals WHERE id = ?", (goal_id,)).fetchone():
            raise KeyError("goal not found")
    start_date, target_date = changes.get("start_date", current["start_date"]), changes.get("target_date", current["target_date"])
    if start_date and target_date and start_date > target_date:
        raise ValueError("start_date must be before target_date")
    if not changes:
        return current
    now = _now()
    if changes.get("status") == "COMPLETED":
        changes["completed_at"] = now
    assignments = ", ".join(f"{key} = ?" for key in changes)
    with get_db_connection() as conn:
        conn.execute(f"UPDATE projects SET {assignments}, updated_at = ? WHERE id = ?", [*changes.values(), now, project_id])
        conn.commit()
    return _get_project(project_id)  # type: ignore[return-value]


def link_task_to_project(project_id: str, task_id: str) -> dict[str, Any]:
    if not _get_project(project_id):
        raise KeyError("project not found")
    with get_db_connection() as conn:
        task = conn.execute("SELECT id FROM commitments WHERE id = ?", (task_id,)).fetchone()
        if not task:
            raise KeyError("task not found")
        now = _now()
        conn.execute("UPDATE commitments SET project_id = ?, updated_at = ? WHERE id = ?", (project_id, now, task_id))
        conn.execute("INSERT INTO commitment_events (commitment_id, event_type, from_status, to_status, payload_json) VALUES (?, ?, (SELECT status FROM commitments WHERE id = ?), (SELECT status FROM commitments WHERE id = ?), ?)",
                     (task_id, "PROJECT_LINKED", task_id, task_id, _json({"project_id": project_id}, {})))
        conn.commit()
    with get_db_connection() as conn:
        row = conn.execute("SELECT id, title, description, status, project_id, deadline_at, reminder_at FROM commitments WHERE id = ?", (task_id,)).fetchone()
    return dict(zip(("id", "title", "description", "status", "project_id", "deadline_at", "reminder_at"), row))


def list_project_tasks(project_id: str) -> list[dict[str, Any]]:
    if not _get_project(project_id):
        raise KeyError("project not found")
    with get_db_connection() as conn:
        rows = conn.execute("SELECT id, title, description, status, project_id, deadline_at, reminder_at FROM commitments WHERE project_id = ? ORDER BY CASE WHEN deadline_at IS NULL THEN 1 ELSE 0 END, deadline_at, created_at", (project_id,)).fetchall()
    return [dict(zip(("id", "title", "description", "status", "project_id", "deadline_at", "reminder_at"), row)) for row in rows]
