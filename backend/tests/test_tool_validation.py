import unittest.mock as mock
import pytest
from pydantic import ValidationError

from backend.app.agent.tool_models import (
    ListEventsArgs,
    SearchEventsArgs,
    CreateEventArgs,
    DeleteEventArgs,
    ModifyEventArgs,
    FindCalendarSlotsArgs,
    ListTasksArgs,
    CreateTaskArgs,
    RescheduleTaskArgs,
    TaskIdArgs,
    ListUnreadEmailsArgs,
    SearchEmailsArgs,
    SendEmailArgs,
    AddTransactionArgs,
    AddRecurringTemplateArgs,
    GetTransactionsArgs,
    GetSummaryArgs,
    GetFinanceForecastArgs,
    AddCountdownArgs,
    GetAllCountdownsArgs,
    DeleteCountdownArgs,
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


class TestFindCalendarSlotsArgs:
    def test_valid_defaults(self):
        model = FindCalendarSlotsArgs(start_date="2026-08-06")

        assert model.end_date is None
        assert model.duration_minutes == 60
        assert model.earliest_time == "09:00"
        assert model.latest_time == "18:00"
        assert model.max_results == 5

    def test_valid_custom_window(self):
        model = FindCalendarSlotsArgs(
            start_date="2026-08-06",
            end_date="2026-08-08",
            duration_minutes=90,
            earliest_time="10",
            latest_time="17:30",
            max_results=3,
        )

        assert model.model_dump(exclude_none=True)["duration_minutes"] == 90
        assert model.earliest_time == "10"

    @pytest.mark.parametrize("payload", [
        {"start_date": "2026-08-06", "duration_minutes": 14},
        {"start_date": "2026-08-06", "duration_minutes": 1441},
        {"start_date": "2026-08-06", "earliest_time": "9:5"},
        {"start_date": "2026-08-06", "latest_time": "18:00:00"},
    ])
    def test_invalid_constraints(self, payload):
        with pytest.raises(ValidationError):
            FindCalendarSlotsArgs(**payload)

    def test_execute_invalid_missing_start_date(self):
        result = _exec_mock("find_calendar_slots", {})

        assert result["status"] == "error"
        assert "start_date" in result["message"]


class TestCreateEventArgs:
    def test_valid(self):
        m = CreateEventArgs(title="Meeting", start_datetime="2026-08-01T10:00:00")
        assert m.title == "Meeting"
        assert m.end_datetime is None

    def test_valid_with_optional(self):
        m = CreateEventArgs(title="M", start_datetime="2026-08-01T10:00:00", end_datetime="2026-08-01T11:00:00", description="desc")
        assert m.description == "desc"

    def test_preserves_recurrence_and_reminder_fields(self):
        m = CreateEventArgs(
            title="Birthday",
            start_datetime="2026-08-01T00:00:00",
            all_day=True,
            recurrence="yearly",
            recurrence_until="2030-08-01",
            reminder_minutes=1440,
        )
        assert m.model_dump(exclude_none=True)["all_day"] is True
        assert m.recurrence == "yearly"
        assert m.reminder_minutes == 1440

    def test_invalid_missing_title(self):
        with pytest.raises(ValidationError):
            CreateEventArgs(start_datetime="2026-08-01T10:00:00")

    def test_execute_invalid_blocked(self):
        result = _exec_mock("create_event", {"title": "T"})
        assert result["status"] == "error"
        assert "start_datetime" in result["message"]


class TestTaskArgs:
    def test_list_tasks_defaults_to_open_tasks(self):
        model = ListTasksArgs()

        assert model.status is None
        assert model.include_completed is False

    def test_list_tasks_accepts_status(self):
        assert ListTasksArgs(status="ACTIVE", include_completed=True).status == "ACTIVE"

    def test_create_task_accepts_optional_schedule(self):
        model = CreateTaskArgs(
            title="Send documents",
            deadline_at="2026-08-07T17:00:00+02:00",
            reminder_at="2026-08-07T09:00:00+02:00",
        )

        assert model.title == "Send documents"
        assert model.deadline_at.endswith("+02:00")

    def test_create_task_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            CreateTaskArgs(title="")

    def test_reschedule_task_requires_id_and_deadline(self):
        with pytest.raises(ValidationError):
            RescheduleTaskArgs(task_id="task-1")
        assert RescheduleTaskArgs(task_id="task-1", deadline_at="2026-08-07T17:00:00+02:00").task_id == "task-1"

    def test_task_id_tools_reject_empty_id(self):
        with pytest.raises(ValidationError):
            TaskIdArgs(task_id="")

    def test_execute_invalid_task_call_is_blocked_before_dispatch(self):
        result = _exec_mock("complete_task", {})

        assert result["status"] == "error"
        assert "task_id" in result["message"]


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


class TestFinanceConversationArgs:
    def test_forecast_defaults_to_three_months(self):
        model = GetFinanceForecastArgs()
        assert model.months == 3

    def test_recurring_template_accepts_weekly_schedule_and_currency(self):
        model = AddRecurringTemplateArgs(
            type="expense",
            amount=20,
            category="Еда",
            currency="EUR",
            frequency="weekly",
            day_of_week=4,
        )
        assert model.day_of_week == 4
        assert model.frequency == "weekly"

    @pytest.mark.parametrize("payload", [
        {"type": "expense", "amount": 20, "category": "Еда", "frequency": "weekly"},
        {"type": "expense", "amount": 20, "category": "Еда", "frequency": "yearly", "day_of_month": 1},
        {"type": "expense", "amount": 20, "category": "Еда", "currency": "EURO"},
    ])
    def test_recurring_template_rejects_incomplete_schedule(self, payload):
        with pytest.raises(ValidationError):
            AddRecurringTemplateArgs(**payload)


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


def test_registry_has_all_tools():
    expected = {
        "list_events", "search_events", "find_calendar_slots", "get_calendar_conflicts", "list_tasks", "create_task", "reschedule_task", "complete_task", "cancel_task", "get_weather", "web_search", "web_fetch", "search_documents", "list_documents", "scan_document_proposals", "propose_document_action", "get_host_diagnostics", "host_control", "create_event", "modify_event", "delete_event",
        "create_goal", "list_goals", "update_goal", "create_project", "list_projects", "update_project", "link_task_to_project", "create_decision", "list_decisions", "revisit_decision",
        "list_unread_emails", "search_emails", "send_email",
        "add_transaction", "get_transactions", "get_summary", "get_finance_forecast", "add_recurring_template",
        "add_countdown", "get_all_countdowns", "delete_countdown",
        "sandbox_list_files", "sandbox_read_file", "sandbox_write_file", "sandbox_run_check", "sandbox_get_diff", "sandbox_delete_file", "sandbox_request_apply",
    }
    from backend.app.agent.tool_registry import TOOL_REGISTRY
    assert set(TOOL_REGISTRY.keys()) == expected


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
