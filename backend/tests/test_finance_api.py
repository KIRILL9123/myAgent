from fastapi import FastAPI
from fastapi.testclient import TestClient


def _finance_test_app() -> FastAPI:
    from backend.app.api.finance import router

    app = FastAPI()
    app.include_router(router, prefix="/api/finance")
    return app


def test_finance_routes_are_registered_in_the_main_application():
    from backend.app.main import app

    paths = {route.path for route in app.routes}

    assert {
        "/api/finance/transactions",
        "/api/finance/summary",
        "/api/finance/forecast",
        "/api/finance/recurring",
    }.issubset(paths)


def test_finance_read_contract_does_not_fall_through_to_not_found(monkeypatch):
    from backend.app.api import finance as finance_api

    monkeypatch.setattr(finance_api, "get_transactions", lambda *args: [])
    monkeypatch.setattr(
        finance_api,
        "get_summary",
        lambda *args: {"total_income": 0, "total_expenses": 0, "balance": 0},
    )
    monkeypatch.setattr(finance_api, "get_forecast", lambda **kwargs: {"occurrences": []})
    monkeypatch.setattr(finance_api, "get_recurring_templates", lambda: [])

    client = TestClient(_finance_test_app())
    paths = (
        "/api/finance/transactions?start_date=2026-08-01&end_date=2026-08-31",
        "/api/finance/summary?start_date=2026-08-01&end_date=2026-08-31",
        "/api/finance/forecast?months=3",
        "/api/finance/recurring",
    )

    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)
