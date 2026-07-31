from backend.app.memory.retrieval_gate import decide_retrieval


def test_retrieval_gate_skips_operational_requests():
    assert decide_retrieval("Какая сейчас погода в Эрфурте?").decision == "skip"
    assert decide_retrieval("Проверь мои подписки").reason == "external_domain_request"
    assert decide_retrieval("Search the web for an iPhone price").decision == "skip"


def test_retrieval_gate_retrieves_personal_context():
    decision = decide_retrieval("Что ты помнишь о моих предпочтениях?")
    assert decision.should_retrieve is True
    assert decision.reason == "personal_context_signal"

    assert decide_retrieval("Какой у меня любимый кофе?").decision == "retrieve"


def test_retrieval_gate_handles_empty_or_generic_messages():
    assert decide_retrieval("").reason == "empty_query"
    assert decide_retrieval("Привет").reason == "no_personal_signal"
