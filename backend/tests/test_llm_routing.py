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
