import os
os.environ["DATABASE_PATH"] = "test_home_agent.db"

import asyncio
import backend.app.agent.orchestrator as orchestrator
from backend.app.agent.orchestrator import _check_confirmation
from backend.app.storage.db import init_db, save_pending_action, delete_pending_action, get_pending_action

# Mock _dispatch_tool to avoid real tool execution (e.g. SMTP or database changes)
orchestrator._dispatch_tool = lambda action, args: {"status": "success", "message": "Mocked execution"}

async def test_confirmation():
    print("Initializing Database...")
    init_db()
    
    session_id = "test_session_123"
    
    # Clean up pending actions
    delete_pending_action(session_id)
    
    # Save a fake pending action
    save_pending_action(session_id, "send_email", {"to": "test@example.com", "subject": "Test"})
    
    # 1. Test exact confirmation match
    result = await _check_confirmation("Да", session_id)
    assert result is not None, "Should match 'Да'"
    assert "подтверждено" in result["response"], f"Unexpected response: {result['response']}"
    print("Test 1 passed: Exact confirmation 'Да'")
    
    # Save pending action again
    save_pending_action(session_id, "send_email", {"to": "test@example.com", "subject": "Test"})
    
    # 2. Test fuzzy confirmation matching (short message, <=3 words)
    result = await _check_confirmation("да, отправляй", session_id)
    assert result is not None, "Should match 'да, отправляй'"
    assert "подтверждено" in result["response"]
    print("Test 2 passed: Fuzzy confirmation 'да, отправляй'")
    
    # Save pending action again
    save_pending_action(session_id, "send_email", {"to": "test@example.com", "subject": "Test"})
    
    # 3. Test existential negation list bypass (e.g. "нет времени")
    result = await _check_confirmation("нет времени", session_id)
    assert result is None, "Should bypass confirmation/cancellation for 'нет времени'"
    # Verify action is still pending
    assert get_pending_action(session_id) is not None, "Action should remain pending"
    print("Test 3 passed: Negation check 'нет времени' bypassed")
    
    # 4. Test exact cancellation match
    result = await _check_confirmation("нет", session_id)
    assert result is not None, "Should match 'нет'"
    assert "отменено" in result["response"]
    assert get_pending_action(session_id) is None, "Action should be deleted"
    print("Test 4 passed: Exact cancellation 'нет'")
    
    # Save pending action again
    save_pending_action(session_id, "send_email", {"to": "test@example.com", "subject": "Test"})
    
    # 5. Test fuzzy cancellation matching
    result = await _check_confirmation("нет, отменяй", session_id)
    assert result is not None, "Should match 'нет, отменяй'"
    assert "отменено" in result["response"]
    print("Test 5 passed: Fuzzy cancellation 'нет, отменяй'")
    
    # Save pending action again
    save_pending_action(session_id, "send_email", {"to": "test@example.com", "subject": "Test"})
    
    # 6. Test long message without prefix guard bypass
    # Message starts with an unrelated word and is long
    result = await _check_confirmation("я подумал, что нет, давай завтра сделаем", session_id)
    assert result is None, "Should bypass cancellation check for long unrelated messages"
    print("Test 6 passed: Long message without cancel prefix bypassed")
    
    # Clean up test database file
    try:
        if os.path.exists("test_home_agent.db"):
            os.remove("test_home_agent.db")
    except Exception as e:
        print(f"Failed to remove test DB: {e}")
        
    print("\nALL CONFIRMATION LOGIC TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_confirmation())
