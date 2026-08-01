import asyncio


def test_filter(test_db, real_mode, monkeypatch):
    """Keyword retrieval stays local until candidates exceed the requested limit."""
    from backend.app.memory.memory_service import get_relevant_facts, save_approved_fact

    llm_call_count = 0

    async def mock_chat(*args, **kwargs):
        nonlocal llm_call_count
        llm_call_count += 1
        return {"message": {"content": '{"fact_ids": []}'}}

    monkeypatch.setattr("backend.app.agent.llm.chat", mock_chat)

    save_approved_fact("Любит пить черный кофе по утрам", "preference", 0.95)
    save_approved_fact("Ездит на работу на машине", "habit", 0.9)
    save_approved_fact("Изучает программирование на Python", "project", 0.85)

    # Exact and stem matches are resolved without a model call.
    llm_call_count = 0
    facts = asyncio.run(get_relevant_facts("кофе", limit=5))
    assert len(facts) == 1
    assert "кофе" in facts[0]["content"]
    assert llm_call_count == 0

    llm_call_count = 0
    facts = asyncio.run(get_relevant_facts("машину", limit=5))
    assert len(facts) == 1
    assert "машине" in facts[0]["content"]
    assert llm_call_count == 0

    llm_call_count = 0
    facts = asyncio.run(get_relevant_facts("какая сегодня погода?", limit=5))
    assert len(facts) == 0
    assert llm_call_count == 0

    save_approved_fact("Пишет код на python", "project", 0.9)
    save_approved_fact("Изучает структуры данных в python", "project", 0.9)
    save_approved_fact("Читает книги про python", "project", 0.9)
    save_approved_fact("Проходит курс по python", "project", 0.9)
    save_approved_fact("Создает веб-приложения на python", "project", 0.9)

    llm_call_count = 0
    asyncio.run(get_relevant_facts("python", limit=5))
    assert llm_call_count == 1

    llm_call_count = 0
    facts = asyncio.run(get_relevant_facts("что это?", limit=5))
    assert len(facts) == 0
    assert llm_call_count == 0
