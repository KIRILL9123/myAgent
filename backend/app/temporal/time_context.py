"""One deterministic time contract for Mira's cross-domain read models.

Domain data is stored as ISO-8601 timestamps and compared in UTC. User-facing
calendar-day decisions are made in the configured personal timezone. Callers
may inject a reference time for deterministic tests or replayed read models.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = os.getenv("MIRA_TIMEZONE", "Europe/Berlin").strip() or "Europe/Berlin"


def resolve_timezone(timezone_name: str | None = None) -> ZoneInfo:
    """Resolve and validate the timezone used for calendar-day semantics."""
    name = (timezone_name or DEFAULT_TIMEZONE).strip()
    try:
        return ZoneInfo(name)
    except Exception as exc:
        raise ValueError(f"invalid timezone: {name}") from exc


def parse_datetime(value: Any, *, default_timezone: timezone | ZoneInfo = timezone.utc) -> datetime | None:
    """Parse an ISO timestamp and return an aware UTC datetime.

    Existing domain records historically treated naive timestamps as UTC.
    Callers that read local-calendar values can pass the user's ZoneInfo as the
    default timezone instead.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_timezone)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class TemporalContext:
    """A single reference instant plus the timezone for user-facing dates."""

    now_utc: datetime
    timezone_name: str
    zone: ZoneInfo

    @property
    def now_local(self) -> datetime:
        return self.now_utc.astimezone(self.zone)

    @property
    def today(self) -> date:
        return self.now_local.date()

    @property
    def tomorrow(self) -> date:
        return self.today + timedelta(days=1)

    @property
    def end_of_today(self) -> datetime:
        return datetime.combine(self.tomorrow, time.min, tzinfo=self.zone).astimezone(timezone.utc)

    def parse(self, value: Any, *, assume_local: bool = False) -> datetime | None:
        """Parse a domain timestamp using UTC or the user's local timezone."""
        default_timezone = self.zone if assume_local else timezone.utc
        return parse_datetime(value, default_timezone=default_timezone)


def build_temporal_context(
    reference_time: datetime | None = None,
    timezone_name: str | None = None,
) -> TemporalContext:
    """Create the shared context for one read-model or delivery operation."""
    if reference_time is None:
        now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        if reference_time.tzinfo is None:
            raise ValueError("reference_time must include a timezone")
        now_utc = reference_time.astimezone(timezone.utc)
    zone = resolve_timezone(timezone_name)
    return TemporalContext(now_utc=now_utc, timezone_name=zone.key, zone=zone)


@dataclass(frozen=True)
class DueState:
    """Shared due-state and priority projection for time-bound entities."""

    status: str
    priority: str
    attention: bool


def classify_due(
    value: str | None,
    context: TemporalContext,
    soon_days: int,
) -> DueState:
    """Classify a timestamp using the same local-day boundary everywhere."""
    event = context.parse(value)
    if not event:
        return DueState("planned", "low", False)
    if event < context.now_utc:
        return DueState("overdue", "critical", True)
    if event < context.end_of_today:
        return DueState("due_today", "high", True)
    if event <= context.now_utc + timedelta(days=soon_days):
        return DueState("upcoming", "high", True)
    return DueState("planned", "low", False)


def classify_due_date(value: str | date | None, context: TemporalContext, soon_days: int) -> DueState:
    """Classify a date-only signal without treating today's date as midnight UTC."""
    if value is None or value == "":
        return DueState("planned", "low", False)
    try:
        target = value if isinstance(value, date) else date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return DueState("planned", "low", False)
    if target < context.today:
        return DueState("overdue", "critical", True)
    if target == context.today:
        return DueState("due_today", "high", True)
    if target <= context.today + timedelta(days=soon_days):
        return DueState("upcoming", "high", True)
    return DueState("planned", "low", False)


def days_until(value: str, context: TemporalContext) -> int:
    """Return whole calendar days until a date-only deadline."""
    target = date.fromisoformat(value)
    return (target - context.today).days
