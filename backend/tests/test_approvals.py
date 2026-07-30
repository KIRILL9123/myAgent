import pytest

from backend.app.approvals.approval_service import list_approvals, resolve_approval
from backend.app.commitments.commitment_service import create_commitment
from backend.app.memory.memory_service import save_pending_fact
from backend.app.storage import db


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
