from datetime import date

import pytest

from backend.app.finance.finance_service import (
    add_recurring_template,
    add_transaction,
    get_forecast,
    get_summary,
    get_transactions,
)
from backend.app.finance.recurrence import occurrences_between
from backend.app.storage import db


@pytest.fixture
def finance_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "finance.db"))
    monkeypatch.setenv("EXECUTION_MODE", "real")
    db.init_db()


def test_recurrence_rules_cover_weekly_monthly_and_yearly_dates():
    assert occurrences_between(
        {"frequency": "weekly", "day_of_week": 0},
        date(2026, 8, 3),
        date(2026, 8, 17),
    ) == [date(2026, 8, 3), date(2026, 8, 10), date(2026, 8, 17)]
    assert occurrences_between(
        {"frequency": "monthly", "day_of_month": 31},
        date(2026, 2, 1),
        date(2026, 4, 30),
    ) == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]
    assert occurrences_between(
        {"frequency": "yearly", "day_of_month": 29, "month_of_year": 2},
        date(2027, 1, 1),
        date(2028, 12, 31),
    ) == [date(2027, 2, 28), date(2028, 2, 29)]


def test_finance_keeps_mixed_currencies_separate(finance_db, monkeypatch):
    monkeypatch.delenv("FINANCE_DEFAULT_CURRENCY", raising=False)
    add_transaction("expense", 10, "Разное", "USD purchase", "2026-08-01", "USD")
    add_transaction("income", 20, "Разное", "EUR income", "2026-08-02", "EUR")

    transactions = get_transactions("2026-08-01", "2026-08-31")
    summary = get_summary("2026-08-01", "2026-08-31")

    assert {item["currency"] for item in transactions} == {"EUR", "USD"}
    assert summary["mixed_currency"] is True
    assert summary["currencies"] == ["EUR", "USD"]
    assert summary["by_currency"]["EUR"]["total_income"] == 20
    assert summary["by_currency"]["USD"]["total_expense"] == 10
    assert summary["total_income"] == 20
    assert summary["total_expense"] == 0


def test_forecast_groups_active_templates_by_currency(finance_db):
    add_recurring_template(
        "expense", 12, "Разное", "Weekly USD", currency="USD",
        frequency="weekly", day_of_week=0,
    )
    add_recurring_template(
        "expense", 30, "Разное", "Monthly EUR", currency="EUR",
        frequency="monthly", day_of_month=31,
    )
    add_recurring_template(
        "income", 100, "Разное", "Yearly EUR", currency="EUR",
        frequency="yearly", day_of_month=15, month_of_year=2,
    )

    forecast = get_forecast(months=3, start_date="2026-01-01")

    assert forecast["end_date"] == "2026-03-31"
    assert forecast["currencies"] == ["EUR", "USD"]
    assert forecast["by_currency"]["USD"]["occurrences"] == 13
    assert forecast["by_currency"]["USD"]["total_expense"] == 156
    assert forecast["by_currency"]["EUR"]["occurrences"] == 4
    assert forecast["by_currency"]["EUR"]["total_expense"] == 90
    assert forecast["by_currency"]["EUR"]["total_income"] == 100
    assert {item["date"] for item in forecast["occurrences"] if item["description"] == "Monthly EUR"} == {
        "2026-01-31", "2026-02-28", "2026-03-31"
    }
