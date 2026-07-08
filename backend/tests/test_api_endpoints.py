import os
os.environ["DATABASE_PATH"] = "test_home_agent.db"

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.storage.db import _get_connection, init_db
from backend.app.memory.memory_service import save_pending_fact

def test_routes():
    init_db()
    
    # Clean DB tables for clean testing
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fact_relations")
    cursor.execute("DELETE FROM user_facts")
    conn.commit()
    conn.close()
    
    client = TestClient(app)
    
    # 1. Test get pending (should be empty initially)
    resp = client.get("/api/memory/pending")
    assert resp.status_code == 200
    assert resp.json() == {"facts": []}
    print("Test 1 Passed: GET /api/memory/pending empty state")
    
    # Insert a dummy pending fact
    fact_id = save_pending_fact("Не любит просыпаться рано", "preference", 0.95)
    
    # 2. Test get pending (should contain the fact)
    resp = client.get("/api/memory/pending")
    assert resp.status_code == 200
    facts = resp.json()["facts"]
    assert len(facts) == 1
    assert facts[0]["content"] == "Не любит просыпаться рано"
    assert facts[0]["id"] == fact_id
    print("Test 2 Passed: GET /api/memory/pending with data")
    
    # 3. Test approve endpoint
    resp = client.post(f"/api/memory/{fact_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    print("Test 3 Passed: POST /api/memory/{fact_id}/approve")
    
    # 4. Test graph endpoint (should contain the node, no edges)
    resp = client.get("/api/memory/graph")
    assert resp.status_code == 200
    graph = resp.json()
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["id"] == fact_id
    assert graph["nodes"][0]["content"] == "Не любит просыпаться рано"
    assert graph["edges"] == []
    print("Test 4 Passed: GET /api/memory/graph content")
    
    # Insert another pending fact to test reject
    fact2_id = save_pending_fact("Учит немецкий язык", "project", 0.8)
    
    # 5. Test reject endpoint
    resp = client.post(f"/api/memory/{fact2_id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    print("Test 5 Passed: POST /api/memory/{fact2_id}/reject")
    
    # Verify it is no longer pending
    resp = client.get("/api/memory/pending")
    assert resp.status_code == 200
    assert len(resp.json()["facts"]) == 0
    print("Test 6 Passed: Rejected fact not in pending")
    
    print("\nALL ROUTE TESTS PASSED SUCCESSFULLY!")
    
    # Clean up test database file
    try:
        if os.path.exists("test_home_agent.db"):
            os.remove("test_home_agent.db")
    except Exception as e:
        print(f"Failed to remove test DB: {e}")

if __name__ == "__main__":
    test_routes()
