import sqlite3

import pytest


def test_recurring_transaction_links_first_entry_to_template(test_db, real_mode):
    from backend.app.finance.finance_service import create_recurring_transaction, get_transactions

    result = create_recurring_transaction(
        "expense", 12.5, "Подписки", "Test subscription", "2026-08-03"
    )

    assert result["status"] == "success"
    transactions = get_transactions("2026-08-01", "2026-08-31")
    assert transactions == [
        {
            "id": result["transaction_id"],
            "type": "expense",
            "amount": 12.5,
            "category": "Подписки",
            "description": "Test subscription",
            "date": "2026-08-03",
            "source_template_id": result["template_id"],
        }
    ]


def test_template_can_only_create_one_transaction_per_month(test_db, real_mode):
    from backend.app.finance.finance_service import create_recurring_transaction
    from backend.app.storage.db import get_db_connection

    result = create_recurring_transaction("expense", 9.99, "Подписки", "Test", "2026-08-03")

    with get_db_connection() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO transactions
                   (type, amount, category, description, date, recurring_template_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("expense", 9.99, "Подписки", "Test", "2026-08-24", result["template_id"]),
            )


def test_categories_come_from_database(test_db, real_mode):
    from backend.app.finance.finance_service import get_categories

    categories = get_categories()

    assert {"name": "Еда", "type": "expense"} in categories
    assert {"name": "Зарплата/Стипендия", "type": "income"} in categories
