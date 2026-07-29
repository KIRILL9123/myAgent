import unittest.mock as mock
import pytest
from pydantic import ValidationError

from backend.app.agent.tool_models import (
    ListEventsArgs,
    SearchEventsArgs,
    CreateEventArgs,
    DeleteEventArgs,
    ModifyEventArgs,
    ListUnreadEmailsArgs,
    SearchEmailsArgs,
    SendEmailArgs,
    AddTransactionArgs,
    GetTransactionsArgs,
    GetSummaryArgs,
    AddCountdownArgs,
    GetAllCountdownsArgs,
    DeleteCountdownArgs,
    TOOL_MODEL_REGISTRY,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _exec_mock(function_name: str, arguments: dict) -> dict:
    import asyncio
    from backend.app.agent.orchestrator import execute_tool

    tool_call = {"function": {"name": function_name, "arguments": arguments}}
    return asyncio.run(execute_tool(tool_call, "test-session"))


# ─── Calendar models ──────────────────────────────────────────────────────────


class TestListEventsArgs:
    def test_valid(self):
        m = ListEventsArgs(start_date="2026-08-01", end_date="2026-08-02")
        assert m.start_date == "2026-08-01"
        assert m.end_date == "2026-08-02"

    def test_invalid_missing_required(self):
        with pytest.raises(ValidationError):
            ListEventsArgs(start_date="2026-08-01")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("list_events", {"start_date": "2026-08-01"})
        assert result["status"] == "error"
        assert "end_date" in result["message"]


class TestSearchEventsArgs:
    def test_valid(self):
        m = SearchEventsArgs(query="dentist")
        assert m.query == "dentist"

    def test_invalid_missing_required(self):
        with pytest.raises(ValidationError):
            SearchEventsArgs()

    def test_execute_invalid_blocked(self):
        result = _exec_mock("search_events", {})
        assert result["status"] == "error"
        assert "query" in result["message"]


class TestCreateEventArgs:
    def test_valid(self):
        m = CreateEventArgs(title="Meeting", start_datetime="2026-08-01T10:00:00")
        assert m.title == "Meeting"
        assert m.end_datetime is None

    def test_valid_with_optional(self):
        m = CreateEventArgs(title="M", start_datetime="2026-08-01T10:00:00", end_datetime="2026-08-01T11:00:00", description="desc")
        assert m.description == "desc"

    def test_invalid_missing_title(self):
        with pytest.raises(ValidationError):
            CreateEventArgs(start_datetime="2026-08-01T10:00:00")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("create_event", {"title": "T"})
        assert result["status"] == "error"
        assert "start_datetime" in result["message"]


class TestDeleteEventArgs:
    def test_valid(self):
        m = DeleteEventArgs(event_uid="abc-123")
        assert m.event_uid == "abc-123"

    def test_invalid(self):
        with pytest.raises(ValidationError):
            DeleteEventArgs()

    def test_execute_invalid_blocked(self):
        result = _exec_mock("delete_event", {})
        assert result["status"] == "error"
        assert "event_uid" in result["message"]


class TestModifyEventArgs:
    def test_valid(self):
        m = ModifyEventArgs(event_uid="uid-1", updated_fields={"title": "New"})
        assert m.updated_fields == {"title": "New"}

    def test_invalid_missing_updated_fields(self):
        with pytest.raises(ValidationError):
            ModifyEventArgs(event_uid="uid-1")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("modify_event", {"event_uid": "uid-1"})
        assert result["status"] == "error"
        assert "updated_fields" in result["message"]


# ─── Mail models ──────────────────────────────────────────────────────────────


class TestListUnreadEmailsArgs:
    def test_valid(self):
        m = ListUnreadEmailsArgs(account="gmail")
        assert m.account == "gmail"
        assert m.limit is None

    def test_valid_with_limit(self):
        m = ListUnreadEmailsArgs(account="ukrnet", limit=5)
        assert m.limit == 5

    def test_invalid_enum(self):
        with pytest.raises(ValidationError):
            ListUnreadEmailsArgs(account="yahoo")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("list_unread_emails", {"account": "yahoo"})
        assert result["status"] == "error"


class TestSearchEmailsArgs:
    def test_valid(self):
        m = SearchEmailsArgs(account="gmail", query="invoice")
        assert m.query == "invoice"

    def test_invalid_missing_both(self):
        with pytest.raises(ValidationError):
            SearchEmailsArgs()

    def test_execute_invalid_blocked(self):
        result = _exec_mock("search_emails", {"account": "gmail"})
        assert result["status"] == "error"
        assert "query" in result["message"]


class TestSendEmailArgs:
    def test_valid(self):
        m = SendEmailArgs(to="a@b.com", subject="S", body="B")
        assert m.account is None

    def test_valid_with_account(self):
        m = SendEmailArgs(to="a@b.com", subject="S", body="B", account="ukrnet")
        assert m.account == "ukrnet"

    def test_invalid_missing(self):
        with pytest.raises(ValidationError):
            SendEmailArgs(to="a@b.com")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("send_email", {"to": "a@b.com"})
        assert result["status"] == "error"


# ─── Finance models ───────────────────────────────────────────────────────────


class TestAddTransactionArgs:
    def test_valid(self):
        m = AddTransactionArgs(type="expense", amount=100.0, category="Еда")
        assert m.date is None

    def test_valid_with_optional(self):
        m = AddTransactionArgs(type="income", amount=5000.0, category="Зарплата/Стипендия", description="October", date="2026-08-01")
        assert m.description == "October"

    def test_invalid_missing_amount(self):
        with pytest.raises(ValidationError):
            AddTransactionArgs(type="expense", category="Еда")

    def test_invalid_type_enum(self):
        with pytest.raises(ValidationError):
            AddTransactionArgs(type="transfer", amount=1.0, category="Еда")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("add_transaction", {"type": "expense", "category": "Еда"})
        assert result["status"] == "error"
        assert "amount" in result["message"]


class TestGetTransactionsArgs:
    def test_valid_empty(self):
        m = GetTransactionsArgs()
        assert m.start_date is None

    def test_valid_with_dates(self):
        m = GetTransactionsArgs(start_date="2026-08-01", end_date="2026-08-31", category="Еда")
        assert m.category == "Еда"

    def test_valid_ignores_extra(self):
        m = GetTransactionsArgs.model_validate({})
        assert m.start_date is None


class TestGetSummaryArgs:
    def test_valid_empty(self):
        m = GetSummaryArgs()
        assert m.start_date is None

    def test_valid_with_dates(self):
        m = GetSummaryArgs(start_date="2026-08-01", end_date="2026-08-31")
        assert m.end_date == "2026-08-31"


# ─── Countdown models ─────────────────────────────────────────────────────────


class TestAddCountdownArgs:
    def test_valid(self):
        m = AddCountdownArgs(title="Start", target_date="2026-09-01")
        assert m.category is None

    def test_valid_with_category(self):
        m = AddCountdownArgs(title="Start", target_date="2026-09-01", category="работа")
        assert m.category == "работа"

    def test_invalid_missing_title(self):
        with pytest.raises(ValidationError):
            AddCountdownArgs(target_date="2026-09-01")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("add_countdown", {"target_date": "2026-09-01"})
        assert result["status"] == "error"
        assert "title" in result["message"]


class TestGetAllCountdownsArgs:
    def test_valid_empty(self):
        m = GetAllCountdownsArgs()
        assert isinstance(m, GetAllCountdownsArgs)


class TestDeleteCountdownArgs:
    def test_valid(self):
        m = DeleteCountdownArgs(countdown_id=42)
        assert m.countdown_id == 42

    def test_invalid_wrong_type(self):
        with pytest.raises(ValidationError):
            DeleteCountdownArgs(countdown_id="abc")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("delete_countdown", {"countdown_id": "not-a-number"})
        assert result["status"] == "error"


# ─── Registry completeness ────────────────────────────────────────────────────


def test_registry_has_all_14_tools():
    expected = {
        "list_events", "search_events", "create_event", "modify_event", "delete_event",
        "list_unread_emails", "search_emails", "send_email",
        "add_transaction", "get_transactions", "get_summary",
        "add_countdown", "get_all_countdowns", "delete_countdown",
    }
    assert set(TOOL_MODEL_REGISTRY.keys()) == expected


# ─── Permission check bypass on invalid args ──────────────────────────────────


def test_invalid_args_never_reach_permission_check():
    from backend.app.agent.orchestrator import check_permission

    original = check_permission

    def on_call(name):
        if name == "list_events":
            from backend.app.permissions.permission_checker import PermissionLevel
            return PermissionLevel.GREEN
        return original(name)

    with mock.patch("backend.app.agent.orchestrator.check_permission", wraps=on_call) as mock_perm:
        from backend.app.agent.orchestrator import execute_tool as exec_func
        import asyncio

        tool_call = {"function": {"name": "list_events", "arguments": {"start_date": "2026-08-01"}}}
        result = asyncio.run(exec_func(tool_call, "test-session"))

    assert result["status"] == "error"
    mock_perm.assert_not_called()
