from backend.app.agent.tool_registry import (
    AVAILABLE_TOOLS,
    TOOL_REGISTRY,
    check_registry_integrity,
    dispatch_tool,
)


def test_tool_registry_is_complete_and_drift_free():
    assert check_registry_integrity() == []
    assert len(TOOL_REGISTRY) == len(AVAILABLE_TOOLS) == 49


def test_llm_schema_is_generated_from_registered_model():
    create_event = next(item for item in AVAILABLE_TOOLS if item["function"]["name"] == "create_event")
    properties = create_event["function"]["parameters"]["properties"]

    assert properties["recurrence"]["enum"] == ["none", "daily", "weekly", "monthly", "yearly"]
    assert properties["reminder_minutes"]["minimum"] == 0
    assert "calendar_id" in properties
    assert "commitment_id" in properties


def test_unknown_dispatch_is_denied():
    result = dispatch_tool("missing_tool", {})

    assert result["status"] == "error"
    assert "missing_tool" in result["message"]
