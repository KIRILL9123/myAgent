import asyncio

from backend.app.observability.telemetry import (
    get_recent_events,
    get_telemetry_summary,
    record_event,
    trace_agent_turn,
    set_correlation_id,
    reset_correlation_id,
)
from backend.app.storage import db


def test_structured_telemetry_summary_and_redaction(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "observability.db"))
    db.init_db()

    record_event(
        "test_event", "test", "success", 12.345,
        {"safe_value": "ok", "content": "must not be stored"},
        correlation_id="corr-test",
    )

    summary = get_telemetry_summary()
    assert summary["total_events"] == 1
    assert summary["error_events"] == 0
    assert summary["groups"][0]["avg_duration_ms"] == 12.35

    recent = get_recent_events()
    assert recent[0]["correlation_id"] == "corr-test"
    assert recent[0]["payload"] == {"safe_value": "ok"}


def test_agent_turn_trace_aggregates_safe_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "turn.db"))
    db.init_db()
    correlation_token = set_correlation_id("turn-test")

    @trace_agent_turn
    async def fake_turn():
        record_event("retrieval_gate", "memory", "retrieve", payload={"reason": "personal_context_signal"})
        record_event("memory_retrieval", "memory", "hit", payload={"items": 2})
        record_event("agent_iteration", "orchestrator", "started", payload={"round": 1})
        record_event("llm_call", "test", "ok", payload={"input_tokens": 10, "output_tokens": 4})
        record_event("tool_call", "read_file", "success")
        return {"response": "safe result", "tool_calls": ["read_file"]}

    try:
        result = asyncio.run(fake_turn())
    finally:
        reset_correlation_id(correlation_token)

    trace = next(event for event in get_recent_events(10) if event["event_type"] == "agent_turn")
    assert result["response"] == "safe result"
    assert trace["correlation_id"] == "turn-test"
    assert trace["payload"]["iterations"] == 1
    assert trace["payload"]["retrieval_gate"] == "retrieve"
    assert trace["payload"]["retrieval_gate_reason"] == "personal_context_signal"
    assert trace["payload"]["memory_items"] == 2
    assert trace["payload"]["estimated_tokens"] == 14
    assert trace["payload"]["tool_names"] == "read_file"
