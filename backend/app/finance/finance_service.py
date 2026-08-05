import logging
import os
from datetime import date, datetime, timedelta
from typing import Any

from backend.app.finance.recurrence import (
    is_due_today,
    normalize_currency,
    occurrences_between,
    period_bounds,
    validate_schedule,
)
from backend.app.storage.db import get_db_connection


def _get_default_date_range() -> tuple[str, str]:
    today = date.today()
    start_date = today.replace(day=1).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    return start_date, end_date


def _default_currency() -> str:
    return normalize_currency(os.getenv("FINANCE_DEFAULT_CURRENCY", "EUR"))


def add_transaction(
    type: str,
    amount: float,
    category: str,
    description: str,
    transaction_date: str,
    currency: str | None = None,
) -> dict[str, Any]:
    if type not in ["income", "expense"]:
        return {"status": "error", "message": "type must be 'income' or 'expense'"}
    if amount < 0:
        return {"status": "error", "message": "amount must not be negative"}
    try:
        currency = normalize_currency(currency, _default_currency())
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "add_transaction",
                "type": type,
                "amount": amount,
                "currency": currency,
                "category": category,
                "description": description,
                "date": transaction_date,
            },
        }

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories WHERE name = ?", (category,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Category '{category}' does not exist."}
        cursor.execute(
            "INSERT INTO transactions (type, amount, currency, category, description, date) VALUES (?, ?, ?, ?, ?, ?)",
            (type, amount, currency, category, description, transaction_date),
        )
        conn.commit()
        inserted_id = cursor.lastrowid

    return {
        "status": "success",
        "message": f"Added {type} of {amount} {currency} in {category}",
        "transaction_id": inserted_id,
        "currency": currency,
    }


def get_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    if not start_date or not end_date:
        def_start, def_end = _get_default_date_range()
        start_date = start_date or def_start
        end_date = end_date or def_end

    with get_db_connection() as conn:
        query = """SELECT id, type, amount, currency, category, description, date,
                          source_template_id
                   FROM transactions WHERE date >= ? AND date <= ?"""
        params: list[Any] = [start_date, end_date]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY date DESC, id DESC"
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "id": row[0],
            "type": row[1],
            "amount": row[2],
            "currency": row[3] or "EUR",
            "category": row[4],
            "description": row[5],
            "date": row[6],
            "source_template_id": row[7],
        }
        for row in rows
    ]


def _empty_totals() -> dict[str, float]:
    return {"total_income": 0.0, "total_expense": 0.0, "net_balance": 0.0}


def get_summary(start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    if not start_date or not end_date:
        def_start, def_end = _get_default_date_range()
        start_date = start_date or def_start
        end_date = end_date or def_end

    by_currency: dict[str, dict[str, float]] = {}
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT COALESCE(currency, 'EUR'), type, SUM(amount)
               FROM transactions WHERE date >= ? AND date <= ?
               GROUP BY COALESCE(currency, 'EUR'), type""",
            (start_date, end_date),
        ).fetchall()
        for currency, transaction_type, amount in rows:
            totals = by_currency.setdefault(currency, _empty_totals())
            if transaction_type == "income":
                totals["total_income"] = float(amount or 0)
            else:
                totals["total_expense"] = float(amount or 0)

        breakdown_rows = conn.execute(
            """SELECT COALESCE(currency, 'EUR'), type, category, SUM(amount)
               FROM transactions WHERE date >= ? AND date <= ?
               GROUP BY COALESCE(currency, 'EUR'), type, category""",
            (start_date, end_date),
        ).fetchall()

    for totals in by_currency.values():
        totals["net_balance"] = totals["total_income"] - totals["total_expense"]

    preferred_currency = _default_currency()
    display_currency = preferred_currency if preferred_currency in by_currency else next(iter(sorted(by_currency)), preferred_currency)
    display_totals = by_currency.get(display_currency, _empty_totals())
    expense_breakdown = [
        {"category": category, "amount": float(amount)}
        for currency, transaction_type, category, amount in breakdown_rows
        if currency == display_currency and transaction_type == "expense"
    ]
    income_breakdown = [
        {"category": category, "amount": float(amount)}
        for currency, transaction_type, category, amount in breakdown_rows
        if currency == display_currency and transaction_type == "income"
    ]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "currency": display_currency,
        "display_currency": display_currency,
        "currencies": sorted(by_currency),
        "mixed_currency": len(by_currency) > 1,
        "by_currency": by_currency,
        "total_income": display_totals["total_income"],
        "total_expense": display_totals["total_expense"],
        "net_balance": display_totals["net_balance"],
        "expense_breakdown": expense_breakdown,
        "income_breakdown": income_breakdown,
    }


def delete_transaction(transaction_id: int) -> dict[str, Any]:
    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run():
        return {"status": "dry_run", "would_do": {"action": "delete_transaction", "transaction_id": transaction_id}}

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Transaction with ID {transaction_id} not found."}
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
    return {"status": "success", "message": f"Transaction {transaction_id} deleted."}


def add_recurring_template(
    type: str,
    amount: float,
    category: str,
    description: str,
    day_of_month: int | None = None,
    currency: str | None = None,
    frequency: str = "monthly",
    day_of_week: int | None = None,
    month_of_year: int | None = None,
) -> dict[str, Any]:
    if type not in ["income", "expense"]:
        return {"status": "error", "message": "type must be 'income' or 'expense'"}
    if amount < 0:
        return {"status": "error", "message": "amount must not be negative"}
    try:
        currency = normalize_currency(currency, _default_currency())
        frequency = validate_schedule(frequency, day_of_month, day_of_week, month_of_year)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories WHERE name = ?", (category,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Category '{category}' does not exist."}
        stored_day_of_month = day_of_month if day_of_month is not None else 1
        cursor.execute(
            """INSERT INTO recurring_templates
               (type, amount, currency, category, description, day_of_month,
                frequency, day_of_week, month_of_year, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (type, amount, currency, category, description, stored_day_of_month,
             frequency, day_of_week, month_of_year),
        )
        conn.commit()
        inserted_id = cursor.lastrowid

    return {
        "status": "success",
        "message": f"Added recurring {type} of {amount} {currency} in {category}",
        "template_id": inserted_id,
        "currency": currency,
        "frequency": frequency,
    }


def get_recurring_templates() -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT id, type, amount, currency, category, description,
                      day_of_month, frequency, day_of_week, month_of_year, active
               FROM recurring_templates
               ORDER BY active DESC, frequency, day_of_month ASC""",
        ).fetchall()
    return [
        {
            "id": row[0],
            "type": row[1],
            "amount": row[2],
            "currency": row[3] or "EUR",
            "category": row[4],
            "description": row[5],
            "day_of_month": row[6],
            "frequency": row[7] or "monthly",
            "day_of_week": row[8],
            "month_of_year": row[9],
            "active": bool(row[10]),
        }
        for row in rows
    ]


def delete_recurring_template(template_id: int) -> dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recurring_templates WHERE id = ?", (template_id,))
        if not cursor.fetchone():
            return {"status": "error", "message": f"Template with ID {template_id} not found."}
        cursor.execute("DELETE FROM recurring_templates WHERE id = ?", (template_id,))
        conn.commit()
    return {"status": "success", "message": f"Recurring template {template_id} deleted."}


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD") from exc


def _add_months(value: date, months: int) -> date:
    index = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(index, 12)
    return date(year, month_index + 1, 1)


def get_forecast(months: int = 3, start_date: str | None = None) -> dict[str, Any]:
    if not 1 <= months <= 24:
        raise ValueError("months must be between 1 and 24")
    start = _parse_date(start_date)
    end = _add_months(start.replace(day=1), months) - timedelta(days=1)
    templates = [template for template in get_recurring_templates() if template["active"]]
    occurrences: list[dict[str, Any]] = []
    by_currency: dict[str, dict[str, float | int]] = {}
    for template in templates:
        for occurrence in occurrences_between(template, start, end):
            currency = template["currency"]
            totals = by_currency.setdefault(currency, {"total_income": 0.0, "total_expense": 0.0, "net_balance": 0.0, "occurrences": 0})
            amount = float(template["amount"])
            if template["type"] == "income":
                totals["total_income"] = float(totals["total_income"]) + amount
            else:
                totals["total_expense"] = float(totals["total_expense"]) + amount
            totals["occurrences"] = int(totals["occurrences"]) + 1
            occurrences.append({
                "template_id": template["id"],
                "date": occurrence.isoformat(),
                "type": template["type"],
                "amount": amount,
                "currency": currency,
                "category": template["category"],
                "description": template["description"],
                "frequency": template["frequency"],
            })
    for totals in by_currency.values():
        totals["net_balance"] = float(totals["total_income"]) - float(totals["total_expense"])
    occurrences.sort(key=lambda item: (item["date"], item["template_id"]))
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "months": months,
        "currencies": sorted(by_currency),
        "by_currency": by_currency,
        "occurrences": occurrences,
    }


def process_recurring_transactions() -> None:
    """Generate at most one ledger transaction per template and period."""
    logger = logging.getLogger("home_agent")
    today = date.today()
    with get_db_connection() as conn:
        templates = conn.execute(
            """SELECT id, type, amount, currency, category, description,
                      day_of_month, frequency, day_of_week, month_of_year
               FROM recurring_templates WHERE active = 1""",
        ).fetchall()
        for row in templates:
            template = {
                "id": row[0], "type": row[1], "amount": row[2], "currency": row[3] or "EUR",
                "category": row[4], "description": row[5], "day_of_month": row[6],
                "frequency": row[7] or "monthly", "day_of_week": row[8], "month_of_year": row[9],
            }
            if not is_due_today(template, today):
                continue
            period_start, period_end = period_bounds(today, template["frequency"])
            existing = conn.execute(
                """SELECT id FROM transactions
                   WHERE source_template_id = ? AND date >= ? AND date <= ?""",
                (template["id"], period_start.isoformat(), period_end.isoformat()),
            ).fetchone()
            if existing:
                continue
            conn.execute(
                """INSERT INTO transactions
                   (type, amount, currency, category, description, date, source_template_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (template["type"], template["amount"], template["currency"], template["category"],
                 template["description"], today.isoformat(), template["id"]),
            )
            logger.info(
                "[FINANCE] Recurring template %s triggered: Added %s of %s %s in %s",
                template["id"], template["type"], template["amount"], template["currency"], template["category"],
            )
        conn.commit()
