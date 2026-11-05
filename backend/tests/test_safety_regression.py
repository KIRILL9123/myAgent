"""
Safety regression tests: API authentication, authorization, permission
boundaries, RED confirmation enforcement, and execution mode.

These tests verify that the safety architecture from Cycle 1 is
enforceable and testable.
"""
import os
import pytest
from backend.app.permissions.permission_checker import check_permission, PermissionLevel
from backend.app.core.execution_mode import is_dry_run, get_execution_mode, ExecutionMode


# ──────────────────────────────────────────────────────────────────────
# Execution Mode
# ──────────────────────────────────────────────────────────────────────


class TestExecutionMode:
    """Execution mode is the global safety switch."""

    def test_default_is_dry_run(self):
        """Without any env var, mode should default to DRY_RUN."""
        assert is_dry_run() is True

    def test_real_mode_when_set(self, monkeypatch):
        monkeypatch.setenv("EXECUTION_MODE", "real")
        assert is_dry_run() is False
        assert get_execution_mode() == ExecutionMode.REAL

    def test_invalid_mode_falls_back_to_dry_run(self, monkeypatch):
        monkeypatch.setenv("EXECUTION_MODE", "invalidstuff")
        mode = get_execution_mode()
        assert mode == ExecutionMode.DRY_RUN

    def test_dry_run_explicit(self, monkeypatch):
        monkeypatch.setenv("EXECUTION_MODE", "dry_run")
        assert is_dry_run() is True


# ──────────────────────────────────────────────────────────────────────
# Permission Levels
# ──────────────────────────────────────────────────────────────────────


class TestPermissionLevels:

    def test_read_operations_are_green(self):
        assert check_permission("list_events") == PermissionLevel.GREEN
        assert check_permission("search_events") == PermissionLevel.GREEN
        assert check_permission("list_unread_emails") == PermissionLevel.GREEN
        assert check_permission("get_transactions") == PermissionLevel.GREEN
        assert check_permission("get_summary") == PermissionLevel.GREEN
        assert check_permission("get_all_countdowns") == PermissionLevel.GREEN

    def test_create_operations_are_yellow(self):
        assert check_permission("create_event") == PermissionLevel.YELLOW

    def test_destructive_external_operations_are_red(self):
        assert check_permission("delete_event") == PermissionLevel.RED
        assert check_permission("modify_event") == PermissionLevel.RED
        assert check_permission("send_email") == PermissionLevel.RED

    def test_local_destructive_is_yellow(self):
        """delete_countdown is local SQLite — intentionally YELLOW, not RED."""
        assert check_permission("delete_countdown") == PermissionLevel.YELLOW

    def test_add_countdown_is_green(self):
        assert check_permission("add_countdown") == PermissionLevel.GREEN

    def test_add_transaction_is_green(self):
        assert check_permission("add_transaction") == PermissionLevel.GREEN

    def test_unknown_action_returns_none(self):
        assert check_permission("nonexistent_tool") is None

    def test_all_registered_tools_have_permissions(self):
        """Every tool in the canonical registry must declare a permission."""
        from backend.app.agent.tool_registry import TOOL_REGISTRY
        for tool_name in TOOL_REGISTRY:
            level = check_permission(tool_name)
            assert level is not None, (
                f"Tool '{tool_name}' has no permission entry in the tool registry"
            )


# ──────────────────────────────────────────────────────────────────────
# RED Confirmation
# ──────────────────────────────────────────────────────────────────────


class TestREDConfirmationBoundary:
    """RED actions must not execute without explicit confirmation."""

    async def test_red_action_stored_as_pending(self, test_db, real_mode):
        """A RED tool call should result in a pending action, not execution."""
        from backend.app.storage.db import save_pending_action, get_pending_action, delete_pending_action

        sid = "red_test_session"
        delete_pending_action(sid)

        save_pending_action(sid, "send_email", {"to": "test@test.com"})
        pending = get_pending_action(sid)
        assert pending is not None
        assert pending["action"] == "send_email"
        assert pending["args"]["to"] == "test@test.com"

    async def test_confirmation_executes_pending(self, test_db, real_mode):
        """Confirming a RED action should execute it."""
        from backend.app.storage.db import save_pending_action, get_pending_action
        from backend.app.agent.orchestrator import _check_confirmation
        import backend.app.agent.orchestrator as orchestrator

        # Mock dispatch to avoid real tool execution
        dispatched = []
        orchestrator._dispatch_tool = lambda action, args: dispatched.append((action, args)) or {
            "status": "success", "message": "ok"
        }

        sid = "red_confirm_session"
        save_pending_action(sid, "delete_event", {"event_uid": "test-uid"})

        result = await _check_confirmation("да", sid)
        assert result is not None
        assert len(dispatched) == 1
        assert dispatched[0][0] == "delete_event"
        assert get_pending_action(sid) is None

    async def test_cancellation_clears_pending(self, test_db, real_mode):
        """Cancelling should clear the pending action without executing."""
        from backend.app.storage.db import save_pending_action, get_pending_action
        from backend.app.agent.orchestrator import _check_confirmation
        import backend.app.agent.orchestrator as orchestrator

        dispatched = []
        orchestrator._dispatch_tool = lambda action, args: dispatched.append((action, args)) or {
            "status": "success", "message": "ok"
        }

        sid = "red_cancel_session"
        save_pending_action(sid, "delete_event", {"event_uid": "test-uid"})

        result = await _check_confirmation("нет", sid)
        assert result is not None
        assert len(dispatched) == 0  # Nothing executed
        assert get_pending_action(sid) is None  # Pending cleared

    async def test_non_confirm_message_keeps_pending(self, test_db, real_mode):
        """A non-confirming message should leave the pending action intact."""
        from backend.app.storage.db import save_pending_action, get_pending_action
        from backend.app.agent.orchestrator import _check_confirmation

        sid = "red_keep_session"
        save_pending_action(sid, "send_email", {"to": "a@b.com"})

        result = await _check_confirmation("расскажи о погоде", sid)
        assert result is None  # Not a confirm/cancel — orchestrator handles it
        assert get_pending_action(sid) is not None  # Still pending


# ──────────────────────────────────────────────────────────────────────
# API Authentication
# ──────────────────────────────────────────────────────────────────────


class TestAPIAuthentication:

    def test_no_key_rejected(self, api_client):
        resp = api_client.get("/api/memory/pending")
        assert resp.status_code == 401

    def test_invalid_key_rejected(self, api_client, api_headers_invalid):
        resp = api_client.get("/api/memory/pending", headers=api_headers_invalid)
        assert resp.status_code == 401

    def test_valid_key_accepted(self, api_client, api_headers):
        resp = api_client.get("/api/memory/pending", headers=api_headers)
        assert resp.status_code == 200

    def test_chat_endpoint_requires_auth(self, api_client):
        resp = api_client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 401

    def test_chat_endpoint_accepts_valid_key(self, api_client, api_headers):
        # This will fail at the LLM call, but auth should pass
        resp = api_client.post(
            "/api/chat",
            json={"message": "hello", "session_id": "test-auth"},
            headers=api_headers,
        )
        # Expect an error (no Ollama), but NOT 401
        assert resp.status_code != 401

    def test_write_endpoint_requires_auth(self, api_client):
        resp = api_client.post("/api/countdown/", json={
            "title": "Test", "target_date": "2026-12-31"
        })
        assert resp.status_code == 401

    def test_finance_endpoint_requires_auth(self, api_client):
        resp = api_client.get("/api/finance/transactions")
        assert resp.status_code == 401

    def test_calendar_endpoint_requires_auth(self, api_client):
        resp = api_client.get("/api/calendar/events?start_date=2026-01-01&end_date=2026-01-02")
        assert resp.status_code == 401

    def test_mail_endpoint_requires_auth(self, api_client):
        resp = api_client.get("/api/mail/unread")
        assert resp.status_code == 401


# ──────────────────────────────────────────────────────────────────────
# Side-effect suppression in dry_run
# ──────────────────────────────────────────────────────────────────────


class TestDryRunSideEffectSuppression:
    """Cycle 1 safety: all write operations must respect dry_run."""

    def test_send_email_suppressed_in_dry_run(self):
        from backend.app.connectors.mail_connector import send_email
        result = send_email(to="test@test.com", subject="S", body="B")
        assert result["status"] == "dry_run"

    def test_create_event_suppressed_in_dry_run(self):
        from backend.app.connectors.caldav_connector import create_event
        result = create_event(title="Test", start_datetime="2026-01-01T10:00:00")
        assert result["status"] == "dry_run"

    def test_delete_event_suppressed_in_dry_run(self):
        from backend.app.connectors.caldav_connector import delete_event
        result = delete_event(event_uid="test-uid")
        assert result["status"] == "dry_run"

    def test_modify_event_suppressed_in_dry_run(self):
        from backend.app.connectors.caldav_connector import modify_event
        result = modify_event(event_uid="test-uid", updated_fields={"title": "New"})
        assert result["status"] == "dry_run"

    def test_add_transaction_suppressed_in_dry_run(self):
        from backend.app.finance.finance_service import add_transaction
        result = add_transaction("expense", 100, "Еда", "Test", "2026-01-01")
        assert result["status"] == "dry_run"

    def test_delete_transaction_suppressed_in_dry_run(self):
        from backend.app.finance.finance_service import delete_transaction
        result = delete_transaction(1)
        assert result["status"] == "dry_run"

    def test_add_countdown_suppressed_in_dry_run(self):
        from backend.app.countdown.countdown_service import add_countdown
        result = add_countdown("Test", "2026-12-31")
        assert result["status"] == "dry_run"

    def test_delete_countdown_suppressed_in_dry_run(self):
        from backend.app.countdown.countdown_service import delete_countdown
        result = delete_countdown(1)
        assert result["status"] == "dry_run"

    def test_save_pending_fact_suppressed_in_dry_run(self):
        from backend.app.memory.memory_service import save_pending_fact
        result = save_pending_fact("Test", "preference", 0.9)
        assert result == -1  # sentinel for suppressed write

    def test_consolidate_facts_suppressed_in_dry_run(self):
        from backend.app.memory.memory_service import consolidate_facts
        result = consolidate_facts([1, 2], "Merged", "preference")
        assert result == -1

    def test_telegram_send_suppressed_in_dry_run(self):
        import asyncio
        from backend.app.notifications.telegram_notifier import send_notification
        result = asyncio.run(send_notification("Hello"))
        assert result["status"] == "dry_run"
