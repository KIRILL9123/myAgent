"""
Integration tests for the full memory lifecycle:
fact extraction → pending → approval → relation building → graph.

Uses isolated DB, REAL execution mode, and mocked LLM.
"""
import pytest
from backend.app.memory.memory_service import (
    get_pending_facts,
    get_approved_facts,
    get_graph_data,
    approve_fact,
)


@pytest.fixture(autouse=True)
def _setup(test_db, real_mode):
    """Memory lifecycle tests need REAL mode (they write facts to DB)."""
    pass


class TestFactExtraction:

    async def test_extraction_creates_pending_facts(self, mock_llm):
        from backend.app.memory.fact_extractor import extract_facts_from_conversation

        mock_llm.return_value = {
            "message": {
                "content": '[{"content": "Зовут Кирилл", "category": "relationship", "confidence": 0.95},'
                           ' {"content": "Не любит встречи до 11 утра", "category": "preference", "confidence": 0.9}]'
            }
        }

        results = await extract_facts_from_conversation(
            "User: Привет! Меня зовут Кирилл.\nAssistant: Привет!"
        )

        # Each new fact triggers a dedup LLM call, so total calls = 1 extraction + N dedup
        assert len(results) >= 1
        assert all(not r.get("is_duplicate", False) for r in results)
        assert all(r["status"] == "pending_approval" for r in results)

        pending = get_pending_facts()
        assert len(pending) >= 1

    async def test_extraction_empty_returns_nothing(self, mock_llm):
        from backend.app.memory.fact_extractor import extract_facts_from_conversation

        mock_llm.return_value = {"message": {"content": "[]"}}

        results = await extract_facts_from_conversation(
            "User: Какая сегодня погода?\nAssistant: Сегодня солнечно."
        )

        assert len(results) == 0
        assert len(get_pending_facts()) == 0


class TestFactDeduplication:

    async def test_duplicate_detected_not_re_saved(self, mock_llm):
        from backend.app.memory.fact_extractor import extract_facts_from_conversation

        # First extraction: create facts
        mock_llm.return_value = {
            "message": {
                "content": '[{"content": "Зовут Кирилл", "category": "relationship", "confidence": 0.95}]'
            }
        }
        await extract_facts_from_conversation("User: Меня зовут Кирилл.")
        first_count = len(get_pending_facts())
        assert first_count == 1

        # Second extraction: the dedup LLM call should return is_duplicate=true
        mock_llm.return_value = {
            "message": {
                "content": '{"is_duplicate": true, "fact_id": 1}'
            }
        }
        results = await extract_facts_from_conversation("User: Меня зовут Кирилл.")

        if results:
            assert results[0].get("is_duplicate") is True

        # Count should not increase
        assert len(get_pending_facts()) == first_count


class TestApprovalAndGraph:

    async def test_approve_adds_to_graph(self, mock_llm):
        from backend.app.memory.fact_extractor import extract_facts_from_conversation

        # Extract a fact
        mock_llm.return_value = {
            "message": {
                "content": '[{"content": "Любит Python", "category": "preference", "confidence": 0.9}]'
            }
        }
        await extract_facts_from_conversation("User: Я люблю Python.")

        pending = get_pending_facts()
        assert len(pending) >= 1
        fact_id = pending[0]["id"]

        # Approve — set mock for relation suggestion call
        mock_llm.return_value = {"message": {"content": "[]"}}
        success = await approve_fact(fact_id)
        assert success is True

        # Should be in approved facts
        approved = get_approved_facts()
        assert any(f["id"] == fact_id for f in approved)

        # Should be in graph
        graph = get_graph_data()
        assert any(n["id"] == fact_id for n in graph["nodes"])

    async def test_approve_nonexistent_returns_false(self, mock_llm):
        result = await approve_fact(99999)
        assert result is False
