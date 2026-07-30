import os
import sqlite3

import pytest


@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch):
    async def fake_chat(*args, **kwargs):
        return {"message": {"content": '[]'}}
    monkeypatch.setattr("backend.app.agent.llm.chat", fake_chat)


@pytest.fixture
def test_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_temporal_memory.db")
    monkeypatch.setattr("backend.app.storage.db.DB_PATH", db_path)
    from backend.app.storage.db import init_db
    init_db()
    yield db_path
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture
def sample_facts(test_db):
    from backend.app.memory.memory_service import save_pending_fact, approve_fact
    import asyncio

    f1 = save_pending_fact("Факт без valid_to", "preference", 0.9)
    asyncio.run(approve_fact(f1))

    f2 = save_pending_fact("Факт в будущем", "preference", 0.9)
    asyncio.run(approve_fact(f2))
    with _conn(test_db) as conn:
        conn.execute("UPDATE user_facts SET valid_to = '2099-12-31' WHERE id = ?", (f2,))
        conn.commit()

    f3 = save_pending_fact("Факт истёкший", "preference", 0.9)
    asyncio.run(approve_fact(f3))
    with _conn(test_db) as conn:
        conn.execute("UPDATE user_facts SET valid_to = '2020-01-01' WHERE id = ?", (f3,))
        conn.commit()

    return f1, f2, f3


def _conn(db_path):
    return sqlite3.connect(db_path)


def test_fact_with_null_valid_to_returned(test_db, sample_facts):
    f1, f2, f3 = sample_facts
    from backend.app.memory.memory_service import get_approved_facts

    facts = get_approved_facts()
    ids = {f["id"] for f in facts}
    assert f1 in ids, "Fact with valid_to=NULL should be returned"
    assert f2 in ids, "Fact with valid_to in future should be returned"
    assert f3 not in ids, "Fact with valid_to in past should NOT be returned"


def test_fact_with_future_valid_to_returned(test_db, sample_facts):
    f1, f2, f3 = sample_facts
    from backend.app.memory.memory_service import get_approved_facts

    facts = get_approved_facts()
    future_fact = next(f for f in facts if f["id"] == f2)
    assert future_fact["valid_to"] == "2099-12-31"


def test_fact_with_past_valid_to_excluded(test_db, sample_facts):
    f1, f2, f3 = sample_facts
    from backend.app.memory.memory_service import get_approved_facts

    facts = get_approved_facts()
    expired_ids = {f["id"] for f in facts}
    assert f3 not in expired_ids


def test_old_fact_without_new_fields_returned(test_db):
    with _conn(test_db) as conn:
        conn.execute("""
            INSERT INTO user_facts (content, category, confidence, status)
            VALUES ('Old fact no migration', 'habit', 0.8, 'approved')
        """)
        conn.commit()

    from backend.app.memory.memory_service import get_approved_facts
    facts = get_approved_facts()
    old = [f for f in facts if f["content"] == "Old fact no migration"]
    assert len(old) == 1
    assert old[0]["source_type"] == "unknown"
    assert old[0]["valid_to"] is None
    assert old[0]["valid_from"] is None
    assert old[0]["last_confirmed_at"] is None


def test_new_fact_has_correct_fields(test_db, sample_facts):
    f1, f2, f3 = sample_facts
    from backend.app.memory.memory_service import get_approved_facts

    facts = get_approved_facts()
    f = next(f for f in facts if f["id"] == f1)
    assert f["source_type"] == "llm_extraction"
    assert f["valid_to"] is None
    assert f["valid_from"] is not None
    assert f["last_confirmed_at"] is not None


def test_patch_validity_sets_valid_to(test_db, sample_facts):
    f1, f2, f3 = sample_facts
    from fastapi.testclient import TestClient
    from backend.app.main import app

    os.environ["HOME_AGENT_API_KEY"] = "test-key"
    client = TestClient(app)
    headers = {"X-API-Key": "test-key"}

    resp = client.patch(
        f"/api/memory/facts/{f1}/validity",
        json={"valid_to": "2025-12-31"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["valid_to"] == "2025-12-31"

    with _conn(test_db) as conn:
        row = conn.execute("SELECT valid_to FROM user_facts WHERE id = ?", (f1,)).fetchone()
    assert row[0] == "2025-12-31"


def test_patch_validity_clears_valid_to(test_db, sample_facts):
    f1, f2, f3 = sample_facts
    from fastapi.testclient import TestClient
    from backend.app.main import app

    os.environ["HOME_AGENT_API_KEY"] = "test-key"
    client = TestClient(app)
    headers = {"X-API-Key": "test-key"}

    resp = client.patch(
        f"/api/memory/facts/{f1}/validity",
        json={"valid_to": None},
        headers=headers,
    )
    assert resp.status_code == 200

    with _conn(test_db) as conn:
        row = conn.execute("SELECT valid_to FROM user_facts WHERE id = ?", (f1,)).fetchone()
    assert row[0] is None


def test_patch_validity_not_found(test_db):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    os.environ["HOME_AGENT_API_KEY"] = "test-key"
    client = TestClient(app)
    headers = {"X-API-Key": "test-key"}

    resp = client.patch(
        "/api/memory/facts/99999/validity",
        json={"valid_to": "2099-01-01"},
        headers=headers,
    )
    assert resp.status_code == 404
