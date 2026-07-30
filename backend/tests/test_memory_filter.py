import os
os.environ["DATABASE_PATH"] = "test_home_agent.db"

import asyncio
from backend.app.storage.db import init_db, _get_connection
from backend.app.memory.memory_service import (
    save_approved_fact,
    get_relevant_facts,
    _filter_facts_by_keyword
)
import backend.app.agent.llm as llm

# Keep track of LLM calls
llm_call_count = 0
original_chat = llm.chat

async def mock_chat(messages, tools=None, response_format=None):
    global llm_call_count
    llm_call_count += 1
    return {"message": {"content": '{"fact_ids": []}'}}

# Monkeypatch
llm.chat = mock_chat

async def test_filter():
    global llm_call_count
    print("Initializing Database...")
    init_db()
    
    # Clean DB
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_facts")
    conn.commit()
    conn.close()
    
    # Insert facts
    save_approved_fact("Любит пить черный кофе по утрам", "preference", 0.95)
    save_approved_fact("Ездит на работу на машине", "habit", 0.9)
    save_approved_fact("Изучает программирование на Python", "project", 0.85)
    
    # Test 1: Exact match
    llm_call_count = 0
    facts = await get_relevant_facts("кофе", limit=5)
    assert len(facts) == 1
    assert "кофе" in facts[0]["content"]
    assert llm_call_count == 0, f"Expected 0 LLM calls, got {llm_call_count}"
    print("Test 1 passed: Exact match ('кофе') skipped LLM")
    
    # Test 2: Prefix/stem matching (Russian suffixes/plural)
    # query "машину" or "машины" matches "машине"
    llm_call_count = 0
    facts = await get_relevant_facts("машину", limit=5)
    assert len(facts) == 1
    assert "машине" in facts[0]["content"]
    assert llm_call_count == 0
    print("Test 2 passed: Prefix/stem match ('машину' -> 'машине') skipped LLM")
    
    # Test 3: Irrelevant query (No matches)
    llm_call_count = 0
    facts = await get_relevant_facts("какая сегодня погода?", limit=5)
    assert len(facts) == 0
    assert llm_call_count == 0
    print("Test 3 passed: Irrelevant query ('погода') skipped LLM")

    # Test 4: Multiple matching facts exceeding limit (triggers LLM call)
    # Add more facts about Python/programming so we have 6 facts matching 'python'
    save_approved_fact("Пишет код на python", "project", 0.9)
    save_approved_fact("Изучает структуры данных в python", "project", 0.9)
    save_approved_fact("Читает книги про python", "project", 0.9)
    save_approved_fact("Проходит курс по python", "project", 0.9)
    
    # Now we have 5 facts containing 'python' (1 original + 4 new)
    # Let's add 1 more to exceed limit=5
    save_approved_fact("Создает веб-приложения на python", "project", 0.9)
    
    llm_call_count = 0
    # Search for 'python' with limit 5 (we have 6 matches in total)
    facts = await get_relevant_facts("python", limit=5)
    # LLM should be called because candidates count (6) > limit (5)
    assert llm_call_count == 1, f"Expected 1 LLM call, got {llm_call_count}"
    print("Test 4 passed: Multiple candidate facts exceeding limit triggers LLM call")
    
    # Test 5: Stopwords filter test
    llm_call_count = 0
    facts = await get_relevant_facts("что это?", limit=5)
    assert len(facts) == 0
    assert llm_call_count == 0
    print("Test 5 passed: Stopwords ('что', 'это') correctly ignored")
    
    # Clean up database
    try:
        if os.path.exists("test_home_agent.db"):
            os.remove("test_home_agent.db")
    except Exception as e:
        print(f"Failed to remove test DB: {e}")
        
    print("\nALL MEMORY FILTER TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_filter())
