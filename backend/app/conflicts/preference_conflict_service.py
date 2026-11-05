"""Deterministic Calendar x Memory preference checks.

Only active, approved Memory facts in the ``preference`` or ``habit``
categories are considered.  The parser is intentionally narrow: a fact must
match one of the explicit scheduling phrases below before it can affect a
calendar read model or a save warning.
"""

from __future__ import annotations

import re
from datetime import datetime, time
from typing import Any

from backend.app.memory.memory_service import get_approved_facts
from backend.app.temporal.time_context import TemporalContext


_TIME_VALUE = r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?"
_EARLIEST_PATTERNS = (
    re.compile(rf"(?:\bне\s+раньше\b|\bне\s+(?:планировать|назначать|ставить|создавать)[^.!?]{{0,80}}?\b(?:до|раньше)\b)[^0-9]{{0,12}}{_TIME_VALUE}"),
    re.compile(rf"(?:\bnot\s+before\b|\bno\s+(?:meetings?|events?)\s+before\b)[^0-9]{{0,12}}{_TIME_VALUE}"),
)
_LATEST_PATTERNS = (
    re.compile(rf"(?:\bне\s+позже\b|\bне\s+(?:планировать|назначать|ставить|создавать)[^.!?]{{0,80}}?\b(?:после|позже)\b)[^0-9]{{0,12}}{_TIME_VALUE}"),
    re.compile(rf"(?:\bnot\s+after\b|\bno\s+(?:meetings?|events?)\s+after\b)[^0-9]{{0,12}}{_TIME_VALUE}"),
)

_WEEKDAY_FORMS: dict[int, tuple[str, ...]] = {
    0: ("понедельник", "понедельникам", "понедельники", "monday", "mondays"),
    1: ("вторник", "вторникам", "вторники", "tuesday", "tuesdays"),
    2: ("среда", "средам", "среду", "среды", "wednesday", "wednesdays"),
    3: ("четверг", "четвергам", "четверги", "thursday", "thursdays"),
    4: ("пятница", "пятницам", "пятницу", "пятницы", "friday", "fridays"),
    5: ("суббота", "субботам", "субботу", "субботы", "saturday", "saturdays"),
    6: ("воскресенье", "воскресеньям", "воскресенье", "воскресенья", "sunday", "sundays"),
}


def _normalise(value: str) -> str:
    return " ".join(value.lower().replace("ё", "е").split())


def _time_from_match(match: re.Match[str]) -> time | None:
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or 0)
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def _find_time(patterns: tuple[re.Pattern[str], ...], text: str) -> time | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            value = _time_from_match(match)
            if value is not None:
                return value
    return None


def _blocked_weekdays(text: str) -> set[int]:
    blocked: set[int] = set()
    for weekday, forms in _WEEKDAY_FORMS.items():
        alternatives = "|".join(re.escape(form) for form in forms)
        direct_negation = re.search(rf"\bне\s+(?:по\s+)?(?:{alternatives})\b", text)
        scheduling_negation = re.search(
            rf"\bне\b[^.!?]{{0,80}}\b(?:планир\w*|назнач\w*|став\w*|созда\w*|встреч\w*|работ\w*)\b[^.!?]{{0,50}}\b(?:{alternatives})\b",
            text,
        )
        unavailable_day = re.search(
            rf"\b(?:{alternatives})\b[^.!?]{{0,50}}\bне\s+(?:могу|работаю|планирую)\b",
            text,
        )
        english_negation = re.search(
            rf"\b(?:no|not)\b[^.!?]{{0,50}}\b(?:{alternatives})\b",
            text,
        )
        if direct_negation or scheduling_negation or unavailable_day or english_negation:
            blocked.add(weekday)
    return blocked


def extract_calendar_preferences(facts: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Extract explicit scheduling rules from approved Memory facts only."""
    source_facts = get_approved_facts() if facts is None else facts
    rules: list[dict[str, Any]] = []
    for fact in source_facts:
        if fact.get("status") not in (None, "approved"):
            continue
        if str(fact.get("category", "")).strip().lower() not in {"preference", "habit"}:
            continue
        content = str(fact.get("content", "")).strip()
        if not content:
            continue
        text = _normalise(content)
        earliest = _find_time(_EARLIEST_PATTERNS, text)
        if earliest:
            rules.append({
                "id": f"memory:{fact.get('id')}:earliest_start:{earliest.isoformat()}",
                "kind": "earliest_start",
                "value": earliest.isoformat(timespec="minutes"),
                "fact_id": fact.get("id"),
                "fact_content": content,
            })
        latest = _find_time(_LATEST_PATTERNS, text)
        if latest:
            rules.append({
                "id": f"memory:{fact.get('id')}:latest_end:{latest.isoformat(timespec='minutes')}",
                "kind": "latest_end",
                "value": latest.isoformat(timespec="minutes"),
                "fact_id": fact.get("id"),
                "fact_content": content,
            })
        for weekday in sorted(_blocked_weekdays(text)):
            rules.append({
                "id": f"memory:{fact.get('id')}:blocked_weekday:{weekday}",
                "kind": "blocked_weekday",
                "value": weekday,
                "fact_id": fact.get("id"),
                "fact_content": content,
            })
    return rules


def _preference_conflict(
    *,
    event: dict[str, Any],
    event_start: datetime,
    event_end: datetime,
    rule: dict[str, Any],
) -> dict[str, Any]:
    event_title = event.get("summary") or "Событие"
    fact_content = rule.get("fact_content") or ""
    if rule["kind"] == "earliest_start":
        summary = f"Событие «{event_title}» начинается раньше, чем указано в Memory: {rule['value']}."
    elif rule["kind"] == "latest_end":
        summary = f"Событие «{event_title}» заканчивается позже, чем указано в Memory: {rule['value']}."
    else:
        summary = f"Событие «{event_title}» попадает на день, который в Memory отмечен как нежелательный."
    return {
        "id": f"event-preference:{event.get('uid')}:{rule['id']}:{event_start.isoformat()}",
        "type": "event_preference",
        "title": f"Проверьте предпочтение: {event_title}",
        "summary": summary,
        "priority": "high",
        "status": "conflict",
        "event_uid": event.get("uid"),
        "event_title": event_title,
        "event_start": event_start.isoformat(),
        "event_end": event_end.isoformat(),
        "due_at": event.get("start"),
        "fact_id": rule.get("fact_id"),
        "fact_content": fact_content,
        "preference_rule": {"kind": rule["kind"], "value": rule["value"]},
        "target": "/calendar",
    }


def detect_preference_conflicts(
    events: list[dict[str, Any]],
    context: TemporalContext,
    *,
    preferences: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return warnings for future events that violate explicit Memory rules."""
    rules = extract_calendar_preferences() if preferences is None else preferences
    conflicts: list[dict[str, Any]] = []
    for event in events:
        start = context.parse(event.get("start"), assume_local=True)
        end = context.parse(event.get("end"), assume_local=True)
        if not start or not end or end <= context.now_utc:
            continue
        start_local = start.astimezone(context.zone)
        end_local = end.astimezone(context.zone)
        is_all_day = bool(event.get("all_day")) or len(str(event.get("start", ""))) <= 10
        for rule in rules:
            violates = False
            if rule["kind"] == "blocked_weekday":
                violates = start_local.weekday() == int(rule["value"])
            elif not is_all_day and rule["kind"] == "earliest_start":
                hour, minute = (int(part) for part in str(rule["value"]).split(":", 1))
                violates = start_local.time().replace(second=0, microsecond=0) < time(hour, minute)
            elif not is_all_day and rule["kind"] == "latest_end":
                hour, minute = (int(part) for part in str(rule["value"]).split(":", 1))
                violates = end_local.time().replace(second=0, microsecond=0) > time(hour, minute)
            if violates:
                conflicts.append(_preference_conflict(event=event, event_start=start, event_end=end, rule=rule))
    return conflicts
