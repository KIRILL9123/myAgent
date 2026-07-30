import backend.app.agent.llm as llm


def test_model_is_selected_for_each_role(monkeypatch):
    monkeypatch.setattr(llm, "LLM_ROLE_MAIN", "main-model")
    monkeypatch.setattr(llm, "LLM_ROLE_EXTRACTOR", "extractor-model")
    monkeypatch.setattr(llm, "LLM_ROLE_CLASSIFIER", "classifier-model")

    assert llm.get_model_for_role("main") == "main-model"
    assert llm.get_model_for_role("extractor") == "extractor-model"
    assert llm.get_model_for_role("classifier") == "classifier-model"
    assert llm.get_model_for_role("unknown") == "main-model"
