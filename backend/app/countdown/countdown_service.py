from typing import Any, Dict, List
import datetime
from backend.app.storage.db import get_db_connection
from backend.app.audit.audit_log import log_action

def add_countdown(title: str, target_date: str, category: str = "другое") -> Dict[str, Any]:
    """Add a new countdown deadline."""
    try:
        # Validate date format
        datetime.datetime.strptime(target_date, "%Y-%m-%d")
        
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

def get_all_countdowns() -> Dict[str, Any]:
    """Get all countdowns and calculate remaining days."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, target_date, category, created_at FROM countdowns ORDER BY target_date ASC")
            rows = cursor.fetchall()

        countdowns: List[Dict[str, Any]] = []
        today = datetime.date.today()
        
        for row in rows:
            c_id, title, target_date_str, category, created_at = row
            target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
            days_remaining = (target_date - today).days
            
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
