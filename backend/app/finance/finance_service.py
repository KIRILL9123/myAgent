from datetime import datetime, date
from typing import Any
import calendar

from backend.app.storage.db import get_db_connection

def _get_default_date_range() -> tuple[str, str]:
    today = date.today()
    start_date = today.replace(day=1).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    return start_date, end_date

def add_transaction(type: str, amount: float, category: str, description: str, transaction_date: str) -> dict[str, Any]:
    if type not in ["income", "expense"]:
        return {"status": "error", "message": "type must be 'income' or 'expense'"}

    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "add_transaction",
                "type": type,
                "amount": amount,
                "category": category,
                "description": description,
                "date": transaction_date,
            },
        }

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Verify category exists
        cursor.execute("SELECT name FROM categories WHERE name = ?", (category,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Category '{category}' does not exist."}
            
        cursor.execute(
            "INSERT INTO transactions (type, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            (type, amount, category, description, transaction_date)
        )
        conn.commit()
        inserted_id = cursor.lastrowid
    
    return {
        "status": "success",
        "message": f"Added {type} of {amount} in {category}",
        "transaction_id": inserted_id
    }

def get_transactions(start_date: str | None = None, end_date: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
    if not start_date or not end_date:
        def_start, def_end = _get_default_date_range()
        start_date = start_date or def_start
        end_date = end_date or def_end

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT id, type, amount, category, description, date FROM transactions WHERE date >= ? AND date <= ?"
        params = [start_date, end_date]
        
        if category:
            query += " AND category = ?"
            params.append(category)
            
        query += " ORDER BY date DESC, id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
    
    return [
        {
            "id": row[0],
            "type": row[1],
            "amount": row[2],
            "category": row[3],
            "description": row[4],
            "date": row[5]
        }
        for row in rows
    ]

def get_summary(start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    if not start_date or not end_date:
        def_start, def_end = _get_default_date_range()
        start_date = start_date or def_start
        end_date = end_date or def_end

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT type, SUM(amount) FROM transactions WHERE date >= ? AND date <= ? GROUP BY type",
            (start_date, end_date)
        )
        rows = cursor.fetchall()
        
        total_income = 0.0
        total_expense = 0.0
        
        for r_type, amount in rows:
            if r_type == "income":
                total_income = amount
            else:
                total_expense = amount
                
        cursor.execute(
            "SELECT category, SUM(amount) FROM transactions WHERE date >= ? AND date <= ? AND type = 'expense' GROUP BY category",
            (start_date, end_date)
        )
        expense_breakdown = [{"category": row[0], "amount": row[1]} for row in cursor.fetchall()]
        
        cursor.execute(
            "SELECT category, SUM(amount) FROM transactions WHERE date >= ? AND date <= ? AND type = 'income' GROUP BY category",
            (start_date, end_date)
        )
        income_breakdown = [{"category": row[0], "amount": row[1]} for row in cursor.fetchall()]
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": total_income - total_expense,
        "expense_breakdown": expense_breakdown,
        "income_breakdown": income_breakdown
    }

def update_transaction(
    transaction_id: int,
    *,
    type: str | None = None,
    amount: float | None = None,
    category: str | None = None,
    description: str | None = None,
    transaction_date: str | None = None,
) -> dict[str, Any]:
    updates = {
        "type": type,
        "amount": amount,
        "category": category,
        "description": description,
        "date": transaction_date,
    }
    changes = {field: value for field, value in updates.items() if value is not None}

    if not changes:
        return {"status": "error", "message": "No transaction changes supplied."}
    if type is not None and type not in ["income", "expense"]:
        return {"status": "error", "message": "type must be 'income' or 'expense'"}
    if amount is not None and amount <= 0:
        return {"status": "error", "message": "amount must be greater than zero"}

    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "update_transaction",
                "transaction_id": transaction_id,
                "changes": changes,
            },
        }

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Transaction with ID {transaction_id} not found."}

        if category is not None:
            cursor.execute("SELECT name FROM categories WHERE name = ?", (category,))
            if not cursor.fetchone():
                return {"status": "error", "message": f"Category '{category}' does not exist."}

        assignments = ", ".join(f"{field} = ?" for field in changes)
        cursor.execute(
            f"UPDATE transactions SET {assignments} WHERE id = ?",
            [*changes.values(), transaction_id],
        )
        conn.commit()

    return {"status": "success", "message": f"Transaction {transaction_id} updated."}

def delete_transaction(transaction_id: int) -> dict[str, Any]:
    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "delete_transaction",
                "transaction_id": transaction_id,
            },
        }

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Transaction with ID {transaction_id} not found."}
        
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
    return {"status": "success", "message": f"Transaction {transaction_id} deleted."}

def add_recurring_template(type: str, amount: float, category: str, description: str, day_of_month: int) -> dict[str, Any]:
    if type not in ["income", "expense"]:
        return {"status": "error", "message": "type must be 'income' or 'expense'"}
    if not (1 <= day_of_month <= 31):
        return {"status": "error", "message": "day_of_month must be between 1 and 31"}

    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "add_recurring_template",
                "type": type,
                "amount": amount,
                "category": category,
                "description": description,
                "day_of_month": day_of_month,
            },
        }
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM categories WHERE name = ?", (category,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Category '{category}' does not exist."}
            
        cursor.execute(
            "INSERT INTO recurring_templates (type, amount, category, description, day_of_month) VALUES (?, ?, ?, ?, ?)",
            (type, amount, category, description, day_of_month)
        )
        conn.commit()
        inserted_id = cursor.lastrowid
    
    return {
        "status": "success",
        "message": f"Added recurring {type} template of {amount} in {category}",
        "template_id": inserted_id
    }

def get_recurring_templates() -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, type, amount, category, description, day_of_month FROM recurring_templates ORDER BY day_of_month ASC")
        rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "type": row[1],
            "amount": row[2],
            "category": row[3],
            "description": row[4],
            "day_of_month": row[5]
        }
        for row in rows
    ]

def delete_recurring_template(template_id: int) -> dict[str, Any]:
    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "delete_recurring_template",
                "template_id": template_id,
            },
        }

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recurring_templates WHERE id = ?", (template_id,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Template with ID {template_id} not found."}
        cursor.execute("DELETE FROM recurring_templates WHERE id = ?", (template_id,))
        conn.commit()
    return {"status": "success", "message": f"Recurring template {template_id} deleted."}

def process_recurring_transactions() -> None:
    """
    Checks daily if any recurring templates should trigger.
    Inserts a normal transaction if it hasn't been created yet for this month.

    In DRY_RUN mode: logs what would be created but does not insert transactions.
    """
    from backend.app.core.execution_mode import is_dry_run
    import logging
    logger = logging.getLogger("home_agent")
    
    today = date.today()
    current_day = today.day
    current_month_str = today.strftime("%Y-%m")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, type, amount, category, description, day_of_month FROM recurring_templates")
        templates = cursor.fetchall()
        
        import calendar
        _, last_day_of_month = calendar.monthrange(today.year, today.month)
        
        for t_id, t_type, amount, category, description, day_of_month in templates:
            # Calculate target day for this month (e.g. if template day is 31 and month has 30 days, trigger on 30)
            target_day = min(day_of_month, last_day_of_month)
            
            # Self-healing logic: Trigger if the target day has already passed or is today, 
            # and duplicate check below confirms no transaction exists yet for this month.
            if current_day >= target_day:
                cursor.execute(
                    """
                    SELECT id FROM transactions 
                    WHERE type = ? AND amount = ? AND category = ? AND description = ? 
                    AND date LIKE ?
                    """,
                    (t_type, amount, category, description, f"{current_month_str}-%")
                )
                if not cursor.fetchone():
                    if is_dry_run():
                        logger.info(
                            f"[DRY_RUN] Would trigger recurring template {t_id}: "
                            f"{t_type} of {amount} in {category}"
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO transactions (type, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
                            (t_type, amount, category, description, today.strftime("%Y-%m-%d"))
                        )
                        logger.info(f"[FINANCE] Recurring template {t_id} triggered: Added {t_type} of {amount} in {category}")
                    
        conn.commit()
