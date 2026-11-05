"""
Tests for RED confirmation logic: exact matches, fuzzy matches,
existential negation bypass, and cancellation.

All tests use isolated SQLite databases and mocked dispatch.
"""
import pytest
from backend.app.agent.orchestrator import _check_confirmation
from backend.app.storage.db import init_db, save_pending_action, delete_pending_action, get_pending_action


@pytest.fixture(autouse=True)
def _setup(test_db, monkeypatch):
    """Initialize database and mock _dispatch_tool to avoid real side effects."""
    import backend.app.agent.orchestrator as orchestrator
    init_db()
    orchestrator._dispatch_tool = lambda action, args: {
        "status": "success", "message": "Mocked execution"
    }


SESSION_ID = "test_confirmation_session_123"


class TestExactConfirmation:
    """Exact 'Да' confirmation should execute the pending action."""

    async def test_confirm_da(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("Да", SESSION_ID)
        assert result is not None, "Should match 'Да'"
        assert "подтверждено" in result["response"]

    async def test_confirm_yes(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("yes", SESSION_ID)
        assert result is not None, "Should match 'yes'"
        assert "подтверждено" in result["response"]


class TestFuzzyConfirmation:
    """Short messages containing confirm words should match."""

    async def test_confirm_fuzzy(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("да, отправляй", SESSION_ID)
        assert result is not None
        assert "подтверждено" in result["response"]

    async def test_confirm_ok(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("ок", SESSION_ID)
        assert result is not None
        assert "подтверждено" in result["response"]


class TestNegationBypass:
    """Existential negations like 'нет времени' should NOT trigger cancel."""

    async def test_negation_bypass_net_vremeni(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("нет времени", SESSION_ID)
        assert result is None, "Should bypass confirmation for 'нет времени'"
        assert get_pending_action(SESSION_ID) is not None, "Action should remain pending"

    async def test_negation_bypass_net_sil(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("нет сил", SESSION_ID)
        assert result is None
        assert get_pending_action(SESSION_ID) is not None


class TestCancellation:
    """Cancel words should cancel the pending action."""

    async def test_cancel_net(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("нет", SESSION_ID)
        assert result is not None
        assert "отменено" in result["response"]
        assert get_pending_action(SESSION_ID) is None

    async def test_cancel_fuzzy(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("нет, отменяй", SESSION_ID)
        assert result is not None
        assert "отменено" in result["response"]

    async def test_cancel_no(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation("no", SESSION_ID)
        assert result is not None
        assert "отменено" in result["response"]


class TestLongMessageBypass:
    """Long messages without a confirm/cancel prefix should not match."""

    async def test_long_message_no_match(self):
        save_pending_action(SESSION_ID, "send_email", {"to": "a@b.com", "subject": "Test"})
        result = await _check_confirmation(
            "я подумал, что нет, давай завтра сделаем", SESSION_ID
        )
        assert result is None, "Long message without cancel prefix should bypass"
        assert get_pending_action(SESSION_ID) is not None


class TestNoPendingAction:
    """When there's no pending action, _check_confirmation returns None."""

    async def test_no_pending_action(self):
        delete_pending_action(SESSION_ID)
        result = await _check_confirmation("да", SESSION_ID)
        assert result is None
