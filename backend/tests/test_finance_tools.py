from unittest.mock import patch

from backend.app.agent.tool_registry import PermissionLevel, get_tool_spec


def test_finance_chat_and_telegram_tools_share_registry_and_service_handlers():
    forecast_spec = get_tool_spec("get_finance_forecast")
    recurring_spec = get_tool_spec("add_recurring_template")

    assert forecast_spec is not None
    assert recurring_spec is not None
    assert forecast_spec.domain == "finance"
    assert recurring_spec.domain == "finance"
    assert forecast_spec.permission == PermissionLevel.GREEN
    assert recurring_spec.permission == PermissionLevel.GREEN

    with patch(
        "backend.app.finance.finance_service.get_forecast",
        return_value={"status": "success"},
    ) as forecast:
        result = forecast_spec.handler({"months": 3, "start_date": "2026-08-01"})

    assert result == {"status": "success"}
    forecast.assert_called_once_with(months=3, start_date="2026-08-01")

    recurring_arguments = {
        "type": "expense",
        "amount": 20,
        "category": "Еда",
        "description": "Пятничный обед",
        "currency": "EUR",
        "frequency": "weekly",
        "day_of_week": 4,
    }
    with patch(
        "backend.app.finance.finance_service.add_recurring_template",
        return_value={"status": "success"},
    ) as add_recurring:
        result = recurring_spec.handler(recurring_arguments)

    assert result == {"status": "success"}
    add_recurring.assert_called_once_with(
        type="expense",
        amount=20,
        category="Еда",
        description="Пятничный обед",
        currency="EUR",
        frequency="weekly",
        day_of_month=None,
        day_of_week=4,
        month_of_year=None,
    )
