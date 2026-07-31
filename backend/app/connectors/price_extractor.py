"""Small, deterministic price extraction helpers for web research results."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit


_EURO_NUMBER = r"\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?"
_PRICE_RE = re.compile(
    rf"(?:€\s*(?P<before>{_EURO_NUMBER})|(?P<after>{_EURO_NUMBER})\s*€)",
    flags=re.IGNORECASE,
)

_MODEL_PATTERNS = (
    re.compile(r"\biPhone\s+(?:17|16|15)(?:\s+(?:Pro\s+Max|Pro|Air))?\b", re.IGNORECASE),
    re.compile(r"\b(?:PlayStation\s*5|PS5)\s*(?:Pro|Slim)?\b", re.IGNORECASE),
    re.compile(r"\b(?:AirPods|Galaxy\s+S\d+|Pixel\s+\d+)\b", re.IGNORECASE),
)


def _parse_euro_amount(raw: str) -> float:
    value = raw.strip().replace(" ", "")
    last_comma = value.rfind(",")
    last_dot = value.rfind(".")

    if last_comma >= 0 and last_dot >= 0:
        if last_comma > last_dot:
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif last_comma >= 0:
        fractional_digits = len(value) - last_comma - 1
        value = value.replace(",", ".") if fractional_digits <= 2 else value.replace(",", "")
    elif last_dot >= 0:
        fractional_digits = len(value) - last_dot - 1
        value = value if fractional_digits <= 2 else value.replace(".", "")

    return float(value)


def _model_matches(text: str) -> list[re.Match[str]]:
    matches: list[re.Match[str]] = []
    for pattern in _MODEL_PATTERNS:
        matches.extend(pattern.finditer(text))
    return sorted(matches, key=lambda match: match.start())


def _model_from_url(source_url: str) -> str | None:
    path = urlsplit(source_url).path.lower()
    if "iphone-17-pro" in path:
        return "iPhone 17 Pro"
    if "iphone-17" in path:
        return "iPhone 17"
    if "playstation-5-pro" in path or "ps5-pro" in path:
        return "PlayStation 5 Pro"
    return None


def _nearby_model(text: str, price_match: re.Match[str], models: list[re.Match[str]]) -> str | None:
    for model_match in models:
        if model_match.end() <= price_match.start():
            distance = price_match.start() - model_match.end()
        elif price_match.end() <= model_match.start():
            distance = model_match.start() - price_match.end()
        else:
            distance = 0
        if distance <= 50:
            return model_match.group(0).strip()
    return None


def extract_price_info(text: str, source_url: str) -> dict[str, Any]:
    """Extract the first euro price and its evidence quality from text."""
    text = text or ""
    price_matches = list(_PRICE_RE.finditer(text))
    source = source_url or ""
    result: dict[str, Any] = {
        "price": None,
        "currency": "EUR" if ".de" in urlsplit(source).netloc.lower() else None,
        "model": None,
        "source": source,
        "confidence": "none",
    }
    if not price_matches:
        return result

    models = _model_matches(text)
    match = price_matches[0]
    raw_amount = match.group("before") or match.group("after")
    result["price"] = _parse_euro_amount(raw_amount)
    result["currency"] = "EUR"

    nearby_model = _nearby_model(text, match, models)
    if nearby_model:
        result["model"] = nearby_model
        result["confidence"] = "direct"
    else:
        result["model"] = models[0].group(0).strip() if models else _model_from_url(source)
        result["confidence"] = "indirect"
    return result
