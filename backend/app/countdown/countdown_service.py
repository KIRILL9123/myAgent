from datetime import datetime
from typing import Any, Dict, List
from backend.app.storage.db import get_db_connection
from backend.app.audit.audit_log import log_action
from backend.app.core.execution_mode import is_dry_run
from backend.app.temporal.time_context import TemporalContext, build_temporal_context, days_until

def add_countdown(title: str, target_date: str, category: str = "другое") -> Dict[str, Any]:
    """Add a new countdown deadline."""
    if is_dry_run():
        log_action("add_countdown", "DRY_RUN", f"Would add deadline '{title}' for {target_date}")
        return {
            "status": "dry_run",
            "would_do": {
                "action": "add_countdown",
                "title": title,
                "target_date": target_date,
                "category": category,
            },
        }

    try:
        # Validate date format
        datetime.strptime(target_date, "%Y-%m-%d")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO countdowns (title, target_date, category) VALUES (?, ?, ?)",
                (title, target_date, category)
            )
            conn.commit()
            countdown_id = cursor.lastrowid
        
        log_action("add_countdown", "SUCCESS", f"Added deadline '{title}' for {target_date}")
        return {"status": "success", "id": countdown_id, "message": f"Deadline '{title}' saved successfully."}
    except Exception as e:
        log_action("add_countdown", "ERROR", str(e))
        return {"status": "error", "message": str(e)}

def get_all_countdowns(
    reference_time: datetime | None = None,
    *,
    timezone_name: str | None = None,
    temporal_context: TemporalContext | None = None,
) -> Dict[str, Any]:
    """Get all countdowns and calculate remaining days."""
    try:
        if temporal_context is not None and reference_time is not None:
            raise ValueError("provide either reference_time or temporal_context")
        context = temporal_context or build_temporal_context(reference_time, timezone_name)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, target_date, category, created_at FROM countdowns ORDER BY target_date ASC")
            rows = cursor.fetchall()

        countdowns: List[Dict[str, Any]] = []

        for row in rows:
            c_id, title, target_date_str, category, created_at = row
            days_remaining = days_until(target_date_str, context)
            
            countdowns.append({
                "id": c_id,
                "title": title,
                "target_date": target_date_str,
                "category": category,
                "days_remaining": days_remaining,
                "created_at": created_at
            })
            
        # Sort by days remaining (closest first)
        countdowns.sort(key=lambda x: x["days_remaining"])
        
        return {"status": "success", "countdowns": countdowns}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def delete_countdown(countdown_id: int) -> Dict[str, Any]:
    """Delete a countdown by ID."""
    if is_dry_run():
        log_action("delete_countdown", "DRY_RUN", f"Would delete deadline {countdown_id}")
        return {
            "status": "dry_run",
            "would_do": {
                "action": "delete_countdown",
                "countdown_id": countdown_id,
            },
        }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM countdowns WHERE id = ?", (countdown_id,))
            if cursor.rowcount == 0:
                return {"status": "error", "message": f"Countdown {countdown_id} not found."}
            conn.commit()
        
        log_action("delete_countdown", "SUCCESS", f"Deleted deadline {countdown_id}")
        return {"status": "success", "message": f"Deadline {countdown_id} deleted successfully."}
    except Exception as e:
        log_action("delete_countdown", "ERROR", str(e))
        return {"status": "error", "message": str(e)}
