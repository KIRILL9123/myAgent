import os

import pytest


@pytest.fixture
def memory_db(monkeypatch, tmp_path):
    from backend.app.storage import db
    db_path = str(tmp_path / "memory_second_brain.db")
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_notes_are_searchable_and_archivable(memory_db):
    from backend.app.memory.memory_service import create_note, list_notes, search_memory, update_note

    note = create_note("План переезда", "Сравнить Mac mini и Mac Studio для домашнего агента", ["проект", "железо"])
    assert note["title"] == "План переезда"
    assert search_memory("Mac Studio")[0]["type"] == "note"

    archived = update_note(note["id"], status="archived")
    assert archived and archived["status"] == "archived"
    assert list_notes() == []


def test_auto_approval_only_allows_safe_categories(memory_db):
    from backend.app.memory.memory_service import list_facts, save_extracted_fact

    fact_id, status = save_extracted_fact("Предпочитает тёмную тему", "preference", 0.95)
    assert status == "approved"
    fact = next(item for item in list_facts() if item["id"] == fact_id)
    assert fact["approval_mode"] == "auto_high_confidence"

    _, relationship_status = save_extracted_fact("Жена Анна", "relationship", 0.99)
    _, uncertain_status = save_extracted_fact("Возможно любит кофе", "preference", 0.60)
    assert relationship_status == "pending_approval"
    assert uncertain_status == "pending_approval"


def test_confirm_and_update_fact(memory_db):
    from backend.app.memory.memory_service import confirm_fact, list_facts, save_extracted_fact, update_fact

    fact_id, _ = save_extracted_fact("Работает утром", "habit", 0.95)
    updated = update_fact(fact_id, content="Предпочитает работать утром", is_pinned=True)
    assert updated and updated["is_pinned"] is True
    confirmed = confirm_fact(fact_id)
    assert confirmed and confirmed["approval_mode"] == "user_confirmed"
    assert confirmed["last_confirmed_at"] is not None
    assert len(list_facts(category="habit")) == 1


def test_extractor_accepts_completion_model_json_aliases(memory_db, monkeypatch):
    from backend.app.memory import fact_extractor
    from backend.app.memory.memory_service import list_facts

    async def fake_llm(*args, **kwargs):
        return {
            "message": {
                "content": "```json\n[{\"fact\": \"Предпочитает цены в евро\"}]\n```"
            }
        }

    monkeypatch.setattr(fact_extractor, "chat_with_ollama", fake_llm)
    import asyncio
    results = asyncio.run(fact_extractor.extract_facts_from_conversation("User note"))

    assert len(results) == 1
    assert results[0]["content"] == "Предпочитает цены в евро"
    assert results[0]["status"] == "pending_approval"
    assert list_facts(status="pending_approval")[0]["content"] == "Предпочитает цены в евро"
