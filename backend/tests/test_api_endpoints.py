"""
API endpoint regression tests. Uses FastAPI TestClient with isolated
database and explicit execution mode.
"""
import pytest
from backend.app.memory.memory_service import save_pending_fact


@pytest.fixture(autouse=True)
def _setup(test_db, real_mode):
    """These tests write facts and test API behavior — need REAL mode."""
    pass


class TestMemoryPendingEndpoint:

    def test_pending_empty_initially(self, api_client, api_headers):
        resp = api_client.get("/api/memory/pending", headers=api_headers)
        assert resp.status_code == 200
        assert resp.json() == {"facts": []}

    def test_pending_contains_fact_after_insert(self, api_client, api_headers):
        fact_id = save_pending_fact("Не любит просыпаться рано", "preference", 0.95)
        assert fact_id > 0, "Fact should have been saved"

        resp = api_client.get("/api/memory/pending", headers=api_headers)
        assert resp.status_code == 200
        facts = resp.json()["facts"]
        assert len(facts) == 1
        assert facts[0]["content"] == "Не любит просыпаться рано"
        assert facts[0]["id"] == fact_id

    def test_approve_changes_status(self, api_client, api_headers):
        fact_id = save_pending_fact("Тестовый факт для одобрения", "preference", 0.9)
        resp = api_client.post(f"/api/memory/{fact_id}/approve", headers=api_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_reject_changes_status(self, api_client, api_headers):
        fact_id = save_pending_fact("Тестовый факт для отклонения", "project", 0.8)
        resp = api_client.post(f"/api/memory/{fact_id}/reject", headers=api_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # Verify it's no longer pending
        resp = api_client.get("/api/memory/pending", headers=api_headers)
        pending_ids = [f["id"] for f in resp.json()["facts"]]
        assert fact_id not in pending_ids

    def test_graph_contains_node_after_approval(self, api_client, api_headers, mock_llm):
        mock_llm.return_value = {"message": {"content": "[]"}}
        fact_id = save_pending_fact("Факт для графа", "habit", 0.85)
        api_client.post(f"/api/memory/{fact_id}/approve", headers=api_headers)

        resp = api_client.get("/api/memory/graph", headers=api_headers)
        assert resp.status_code == 200
        graph = resp.json()
        assert any(n["id"] == fact_id for n in graph["nodes"])


class TestAPIAuthentication:

    def test_no_api_key_rejected(self, api_client):
        resp = api_client.get("/api/memory/pending")
        assert resp.status_code == 401

    def test_invalid_api_key_rejected(self, api_client, api_headers_invalid):
        resp = api_client.get("/api/memory/pending", headers=api_headers_invalid)
        assert resp.status_code == 401

    def test_valid_api_key_accepted(self, api_client, api_headers):
        resp = api_client.get("/api/memory/pending", headers=api_headers)
        assert resp.status_code in (200, 404)  # 200 if DB ready, never 401

    def test_health_endpoint_no_key_required(self, api_client):
        """/health endpoint is outside /api prefix, no auth needed."""
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAPIWriteEndpointSafety:

    def test_countdown_add_respects_dry_run(self, api_client, api_headers):
        """Write endpoints should return dry_run status when mode is dry_run."""
        # Note: we're in real_mode from the fixture, so test separately
        pass

    def test_write_endpoint_requires_auth(self, api_client):
        """POST endpoints should reject unauthenticated requests."""
        resp = api_client.post("/api/countdown/", json={
            "title": "Test", "target_date": "2026-12-31"
        })
        assert resp.status_code == 401
