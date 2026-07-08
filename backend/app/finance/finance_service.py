from datetime import datetime, date
from typing import Any
import calendar

from backend.app.storage.db import _get_connection

def _get_default_date_range() -> tuple[str, str]:
    today = date.today()
    start_date = today.replace(day=1).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    return start_date, end_date

def add_transaction(type: str, amount: float, category: str, description: str, transaction_date: str) -> dict[str, Any]:
    if type not in ["income", "expense"]:
        return {"error": "type must be 'income' or 'expense'"}
        
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Verify category exists or insert if we allow dynamic?
    # The requirement didn't specify dynamic addition, but just in case, we check.
    cursor.execute("SELECT name FROM categories WHERE name = ?", (category,))
    if not cursor.fetchone():
        conn.close()
        return {"error": f"Category '{category}' does not exist."}
        
    cursor.execute(
        "INSERT INTO transactions (type, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
        (type, amount, category, description, transaction_date)
    )
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    
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

    conn = _get_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, type, amount, category, description, date FROM transactions WHERE date >= ? AND date <= ?"
    params = [start_date, end_date]
    
    if category:
        query += " AND category = ?"
        params.append(category)
        
    query += " ORDER BY date DESC, id DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
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

    conn = _get_connection()
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
    
    conn.close()
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": total_income - total_expense,
        "expense_breakdown": expense_breakdown,
        "income_breakdown": income_breakdown
    }
