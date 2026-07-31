import pytest

import backend.app.agent.orchestrator as orchestrator
from backend.app.agent.orchestrator import _check_confirmation
from backend.app.approvals.approval_service import list_approvals, resolve_approval
from backend.app.commitments.commitment_service import create_commitment
from backend.app.memory.memory_service import save_pending_fact
from backend.app.storage import db
from backend.app.subscriptions.subscription_service import create_subscription, get_subscription


@pytest.fixture
def approval_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "approvals.db"))
    db.init_db()


@pytest.mark.asyncio
async def test_unified_center_syncs_and_resolves_fact(approval_db):
    fact_id = save_pending_fact("Любит планировать неделю заранее", "preference", 0.9)

    pending = list_approvals()
    assert len(pending) == 1
    assert pending[0]["kind"] == "FACT"
    assert pending[0]["payload"]["fact_id"] == fact_id

    resolved = await resolve_approval(pending[0]["id"], "approve")
    assert resolved["status"] == "APPROVED"
    assert list_approvals() == []


@pytest.mark.asyncio
async def test_unified_center_rejects_commitment(approval_db):
    commitment = create_commitment("Позвонить в страховую", source_type="CHAT")

    pending = list_approvals()
    assert [item["kind"] for item in pending] == ["COMMITMENT"]

    resolved = await resolve_approval(pending[0]["id"], "reject", "Неактуально")
    assert resolved["status"] == "REJECTED"
    assert list_approvals() == []


@pytest.mark.asyncio
async def test_unified_center_approves_subscription(approval_db):
    subscription = create_subscription(
        "Streaming trial", source_type="EMAIL", subscription_type="TRIAL",
        trial_ends_at="2030-01-10T12:00:00+00:00",
    )

    pending = list_approvals()
    assert len(pending) == 1
    assert pending[0]["kind"] == "SUBSCRIPTION"
    assert pending[0]["payload"]["subscription_id"] == subscription["id"]

    resolved = await resolve_approval(pending[0]["id"], "approve", "Проверено пользователем")

    assert resolved["status"] == "APPROVED"
    assert get_subscription(subscription["id"])["status"] == "ACTIVE"
    assert list_approvals() == []


@pytest.mark.asyncio
async def test_unified_center_rejects_subscription(approval_db):
    subscription = create_subscription("Unknown renewal", source_type="EMAIL")
    pending = list_approvals()

    resolved = await resolve_approval(pending[0]["id"], "reject")

    assert resolved["status"] == "REJECTED"
    assert get_subscription(subscription["id"])["status"] == "CANCELLED"
    assert list_approvals() == []


@pytest.mark.asyncio
async def test_cancel_in_chat_marks_action_rejected_not_approved(approval_db):
    action_id, _ = db.save_pending_action("session-1", "send_email", {"to": "a@b.c"})

    pending = list_approvals()
    assert len(pending) == 1
    assert pending[0]["kind"] == "ACTION"

    db.finalize_pending_action(action_id, "cancelled")

    rejected = list_approvals("REJECTED")
    assert any(item["kind"] == "ACTION" and item["source_id"] == str(action_id) for item in rejected)
    approved = list_approvals("APPROVED")
    assert all(item["kind"] != "ACTION" for item in approved)


@pytest.mark.asyncio
async def test_telegram_complete_marks_action_approved_not_rejected(approval_db):
    action_id, _ = db.save_pending_action("session-2", "send_email", {"to": "a@b.c"})

    pending = list_approvals()
    assert len(pending) == 1
    assert pending[0]["kind"] == "ACTION"

    db.finalize_pending_action(action_id, "completed")

    approved = list_approvals("APPROVED")
    assert any(item["kind"] == "ACTION" and item["source_id"] == str(action_id) for item in approved)
    rejected = list_approvals("REJECTED")
    assert all(item["kind"] != "ACTION" for item in rejected)


@pytest.mark.asyncio
async def test_chat_confirm_marks_action_approved_not_stale_pending(approval_db, monkeypatch):
    monkeypatch.setattr(
        orchestrator, "_dispatch_tool",
        lambda action, args: {"status": "success", "message": "Mocked execution"},
    )

    action_id, _ = db.save_pending_action("session-3", "send_email", {"to": "a@b.c"})
    assert list_approvals("PENDING")[0]["kind"] == "ACTION"

    result = await _check_confirmation("да", "session-3")
    assert result is not None
    assert "подтверждено" in result["response"]

    approved = list_approvals("APPROVED")
    assert any(item["kind"] == "ACTION" and item["source_id"] == str(action_id) for item in approved)
    assert list_approvals("PENDING") == []
