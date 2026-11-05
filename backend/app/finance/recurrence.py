"""Small, explicit recurrence primitives for Finance templates.

This is intentionally narrower than iCalendar RRULE: Finance only needs
weekly, monthly, and yearly cash-flow occurrences. Keeping the rules local
avoids adding a general recurrence dependency to the personal app.
"""

from calendar import monthrange
from datetime import date, timedelta
import re
from typing import Any


FREQUENCIES = {"weekly", "monthly", "yearly"}
_CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP", "₴": "UAH"}


def normalize_currency(value: str | None, default: str = "EUR") -> str:
    candidate = str(value or default).strip().upper()
    candidate = _CURRENCY_SYMBOLS.get(candidate, candidate)
    if not re.fullmatch(r"[A-Z]{3}", candidate):
        raise ValueError("currency must be an ISO-4217 three-letter code")
    return candidate


def validate_schedule(
    frequency: str,
    day_of_month: int | None = None,
    day_of_week: int | None = None,
    month_of_year: int | None = None,
) -> str:
    normalized = str(frequency or "monthly").strip().lower()
    if normalized not in FREQUENCIES:
        raise ValueError(f"frequency must be one of {sorted(FREQUENCIES)}")
    if normalized in {"monthly", "yearly"} and not day_of_month:
        raise ValueError("day_of_month is required for monthly and yearly schedules")
    if day_of_month is not None and not 1 <= int(day_of_month) <= 31:
        raise ValueError("day_of_month must be between 1 and 31")
    if normalized == "weekly" and (day_of_week is None or not 0 <= int(day_of_week) <= 6):
        raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday) for weekly schedules")
    if normalized == "yearly" and (month_of_year is None or not 1 <= int(month_of_year) <= 12):
        raise ValueError("month_of_year must be between 1 and 12 for yearly schedules")
    return normalized


def _clamped_month_day(year: int, month: int, day_of_month: int) -> date:
    return date(year, month, min(int(day_of_month), monthrange(year, month)[1]))


def occurrences_between(template: dict[str, Any], start: date, end: date) -> list[date]:
    """Return inclusive occurrence dates for a template in a bounded range."""
    if end < start:
        return []
    frequency = validate_schedule(
        template.get("frequency", "monthly"),
        template.get("day_of_month"),
        template.get("day_of_week"),
        template.get("month_of_year"),
    )
    occurrences: list[date] = []
    if frequency == "weekly":
        weekday = int(template["day_of_week"])
        current = start + timedelta(days=(weekday - start.weekday()) % 7)
        while current <= end:
            occurrences.append(current)
            current += timedelta(days=7)
        return occurrences

    if frequency == "monthly":
        year, month = start.year, start.month
        while (year, month) <= (end.year, end.month):
            occurrence = _clamped_month_day(year, month, int(template["day_of_month"]))
            if start <= occurrence <= end:
                occurrences.append(occurrence)
            month += 1
            if month == 13:
                year, month = year + 1, 1
        return occurrences

    month = int(template["month_of_year"])
    for year in range(start.year, end.year + 1):
        occurrence = _clamped_month_day(year, month, int(template["day_of_month"]))
        if start <= occurrence <= end:
            occurrences.append(occurrence)
    return occurrences


def period_bounds(occurrence: date, frequency: str) -> tuple[date, date]:
    """Return an inclusive period used to deduplicate generated transactions."""
    normalized = validate_schedule(frequency, 1, 0, 1 if frequency == "yearly" else None)
    if normalized == "weekly":
        start = occurrence - timedelta(days=occurrence.weekday())
        return start, start + timedelta(days=6)
    if normalized == "monthly":
        start = occurrence.replace(day=1)
        last = monthrange(start.year, start.month)[1]
        return start, start.replace(day=last)
    start = occurrence.replace(month=1, day=1)
    return start, start.replace(month=12, day=31)


def is_due_today(template: dict[str, Any], today: date) -> bool:
    frequency = str(template.get("frequency", "monthly")).lower()
    if frequency == "weekly":
        return today.weekday() == int(template["day_of_week"])
    if frequency == "monthly":
        occurrence = _clamped_month_day(today.year, today.month, int(template["day_of_month"]))
        return today >= occurrence
    occurrence = _clamped_month_day(today.year, int(template["month_of_year"]), int(template["day_of_month"]))
    return today >= occurrence
