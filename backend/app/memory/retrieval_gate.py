"""Cheap, deterministic pre-retrieval routing for personal memory."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalDecision:
    decision: str
    reason: str
    confidence: str

    @property
    def should_retrieve(self) -> bool:
        return self.decision == "retrieve"


# These are intentionally conservative signals. Domain-specific requests are
# checked first so phrases such as "my calendar" do not pull unrelated facts.
_EXTERNAL_DOMAIN_TERMS = (
    "weather", "forecast", "price", "cost", "buy", "search", "internet", "website",
    "calendar", "event", "meeting", "email", "mail", "finance", "transaction",
    "subscription", "подписк", "погод", "цен", "купить", "интернет", "сайт",
    "календар", "событ", "встреч", "почта", "почту", "почте", "почтов",
    "финанс", "транзакц", "подписк",
)
_PERSONAL_CONTEXT_PHRASES = (
    "what do you remember", "do you remember", "about me", "my preferences",
    "my habits", "my plans", "my priorities", "my projects", "my goals",
    "что ты помнишь", "ты помнишь", "обо мне", "мои предпочтения", "мои привычки",
    "мои планы", "мои приоритеты", "мои проекты", "мои цели", "учти что",
    "как я обычно", "что мне нравится", "что я люблю", "что я не люблю",
)
_PERSONAL_PRONOUN_RE = re.compile(
    r"\b(?:my|mine|i|me|мой|моя|мои|мне|меня|у\s+меня|я)\b",
    re.IGNORECASE,
)


def decide_retrieval(query: str) -> RetrievalDecision:
    """Decide whether the current turn needs personal-memory lookup.

    The default is ``skip`` because most operational requests do not need
    personal facts. The orchestrator treats a gate exception as fail-open and
    retrieves memory, so this function stays deliberately side-effect free.
    """
    normalized = " ".join((query or "").casefold().split())
    if not normalized:
        return RetrievalDecision("skip", "empty_query", "high")

    tokens = re.findall(r"[a-z\u0430-\u044f\u0451\u0430-\u044f0-9]+", normalized)
    external_signal = any(
        (term in normalized if " " in term else any(token == term or token.startswith(term) for token in tokens))
        for term in _EXTERNAL_DOMAIN_TERMS
    )
    if external_signal:
        return RetrievalDecision("skip", "external_domain_request", "high")

    if any(phrase in normalized for phrase in _PERSONAL_CONTEXT_PHRASES):
        return RetrievalDecision("retrieve", "personal_context_signal", "high")

    if _PERSONAL_PRONOUN_RE.search(normalized):
        return RetrievalDecision("retrieve", "first_person_context", "medium")

    return RetrievalDecision("skip", "no_personal_signal", "medium")
