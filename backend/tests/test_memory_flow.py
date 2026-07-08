import os
os.environ["DATABASE_PATH"] = "test_home_agent.db"

import asyncio
import sqlite3
from backend.app.storage.db import init_db, _get_connection
from backend.app.memory.memory_service import (
    get_pending_facts,
    get_approved_facts,
    get_graph_data,
    approve_fact
)
from backend.app.memory.fact_extractor import extract_facts_from_conversation

async def main():
    print("Initializing Database...")
    init_db()
    
    # Check tables in SQLite
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Database tables: {tables}")
    conn.close()
    
    # Clean up tables for a clean test run
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_relations")
    cursor.execute("DELETE FROM user_facts")
    conn.commit()
    conn.close()
    print("Cleared user_facts and fact_relations tables for clean test.")
    
    # 1. Test fact extraction from a conversation text
    sample_chat = (
        "User: Привет! Меня зовут Кирилл, я программист. Работаю в основном по вечерам и не люблю встречи до 11 утра.\n"
        "Assistant: Привет, Кирилл! Я запомню это. Теперь я знаю, что вы программируете по вечерам и не любите утренние встречи."
    )
    
    print("\nExtracting facts from sample chat...")
    results = await extract_facts_from_conversation(sample_chat)
    print(f"Extracted fact candidates: {results}")
    
    # Check pending facts in DB
    pending = get_pending_facts()
    print(f"Pending facts in DB: {pending}")
    
    # 2. Test duplicate check (running extraction again)
    print("\nRunning extraction again to test semantic deduplication...")
    results_dup = await extract_facts_from_conversation(
        "User: Напоминаю, что мое имя Кирилл, я пишу код. И не ставь мне встречи по утрам, особенно до 11."
    )
    print(f"Extraction results (duplicates check): {results_dup}")
    
    # 3. Test approval of facts and relation building
    pending = get_pending_facts()
    if pending:
        print(f"\nApproving first fact: {pending[0]['content']} (ID: {pending[0]['id']})")
        await approve_fact(pending[0]['id'])
        
        # Approve others to build relations
        for p in pending[1:]:
            print(f"Approving fact: {p['content']} (ID: {p['id']})")
            await approve_fact(p['id'])
            
    # Check approved facts
    approved = get_approved_facts()
    print(f"\nApproved facts: {approved}")
    
    # Check graph data
    graph = get_graph_data()
    print(f"\nGraph data: {graph}")

    # Clean up test database file
    try:
        if os.path.exists("test_home_agent.db"):
            os.remove("test_home_agent.db")
    except Exception as e:
        print(f"Failed to remove test DB: {e}")

if __name__ == "__main__":
    asyncio.run(main())
