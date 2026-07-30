import backend.app.agent.llm as llm


def test_model_is_selected_for_each_role(monkeypatch):
    monkeypatch.setattr(llm, "LLM_ROLE_MAIN", "main-model")
    monkeypatch.setattr(llm, "LLM_ROLE_EXTRACTOR", "extractor-model")
    monkeypatch.setattr(llm, "LLM_ROLE_CLASSIFIER", "classifier-model")

    assert llm.get_model_for_role("main") == "main-model"
    assert llm.get_model_for_role("extractor") == "extractor-model"
    assert llm.get_model_for_role("classifier") == "classifier-model"
    assert llm.get_model_for_role("unknown") == "main-model"


def test_pseudo_tool_call_from_local_completion_model_is_normalized():
    message, tool_calls = llm._normalize_message({
        "role": "assistant",
        "content": """<tool_call>
<function=web_fetch>
<parameter=url>https://example.com</parameter>
<parameter=render_js>false</parameter>
</function>
</tool_call>""",
    })

    assert message["content"] == ""
    assert tool_calls[0]["function"]["name"] == "web_fetch"
    assert tool_calls[0]["function"]["arguments"] == {
        "url": "https://example.com",
        "render_js": False,
    }


def test_openai_messages_serialize_tool_arguments_as_json():
    serialized = llm._serialize_messages_for_openai([
        {
            "role": "assistant",
            "tool_calls": [{
                "id": "call-1",
                "type": "function",
                "function": {"name": "web_search", "arguments": {"query": "iPhone 17"}},
            }],
        }
    ])

    assert serialized[0]["tool_calls"][0]["function"]["arguments"] == '{"query": "iPhone 17"}'


def test_tool_messages_can_be_flattened_for_strict_openai_servers():
    flattened = llm._flatten_tool_messages([
        {"role": "user", "content": "find it"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "1"}]},
        {"role": "tool", "name": "web_search", "content": '{"status":"success"}'},
    ])

    assert [item["role"] for item in flattened] == ["user", "user"]
    assert "untrusted_external_content" in flattened[-1]["content"]


def test_pseudo_tool_syntax_is_not_reparsed_when_tools_are_disabled():
    content = "<tool_call><function=web_fetch><parameter=url>https://example.com</parameter></function></tool_call>"

    message, tool_calls = llm._normalize_message({"role": "assistant", "content": content}, parse_pseudo_tools=False)

    assert tool_calls == []
    assert message["content"] == content
