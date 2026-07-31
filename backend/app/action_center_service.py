"""Unified, read-only action feed for the personal agent.

The domain modules remain the source of truth. This service only normalizes
their active signals into one stable contract for the dashboard, chat and
future notification channels.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from backend.app.approvals.approval_service import list_approvals
from backend.app.commitments.commitment_service import list_commitments
from backend.app.countdown.countdown_service import get_all_countdowns
from backend.app.subscriptions.subscription_service import list_subscriptions


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _reference_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError("reference_time must include a timezone")
    return value.astimezone(timezone.utc)


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 4)


def _action(
    *,
    action_id: str,
    kind: str,
    source_id: str | int,
    title: str,
    summary: str,
    status: str,
    priority: str,
    due_at: str | None = None,
    reminder_at: str | None = None,
    source: str | None = None,
    target: str | None = None,
    requires_approval: bool = False,
    reminder_due: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": action_id,
        "kind": kind,
        "source_id": str(source_id),
        "title": title,
        "summary": summary,
        "status": status,
        "priority": priority,
        "due_at": due_at,
        "reminder_at": reminder_at,
        "reminder_due": reminder_due,
        "source": source,
        "target": target,
        "requires_approval": requires_approval,
        "metadata": metadata or {},
    }


def _due_state(event_at: str | None, now: datetime, soon_days: int) -> tuple[str, str, bool]:
    event = _parse_datetime(event_at)
    if not event:
        return "planned", "low", False
    if event < now:
        return "overdue", "critical", True
    if event <= now.replace(hour=23, minute=59, second=59, microsecond=0):
        return "due_today", "high", True
    if event <= now + timedelta(days=soon_days):
        return "upcoming", "high", True
    return "planned", "low", False


def _reminder_due(value: str | None, sent_at: str | None, now: datetime) -> bool:
    reminder = _parse_datetime(value)
    return bool(reminder and reminder <= now and not sent_at)


def _include(item: dict[str, Any], mode: str) -> bool:
    return mode == "all" or item["priority"] in {"critical", "high", "medium"} or item["requires_approval"]


def _sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
    return (_priority_rank(item["priority"]), 0 if item.get("due_at") else 1, item.get("due_at") or "9999")


def build_action_center(
    reference_time: datetime | None = None,
    *,
    mode: str = "attention",
    limit: int = 25,
    include_external: bool = False,
) -> dict[str, Any]:
    """Build the unified action feed without mutating domain data."""
    if mode not in {"attention", "all"}:
        raise ValueError("mode must be attention or all")
    now = _reference_time(reference_time)
    limit = max(1, min(int(limit), 100))
    items: list[dict[str, Any]] = []

    # Proposals and pending tool actions are represented by one approval item,
    # so the feed does not show the same commitment twice.
    for approval in list_approvals("PENDING"):
        payload = approval.get("payload") or {}
        due_at = payload.get("deadline_at") or payload.get("next_charge_at") or payload.get("trial_ends_at")
        items.append(_action(
            action_id=f"approval:{approval['id']}",
            kind="approval",
            source_id=approval["source_id"],
            title=approval["title"],
            summary=approval.get("summary") or "Требуется решение пользователя.",
            status="needs_approval",
            priority="high" if approval.get("kind") == "ACTION" else "medium",
            due_at=due_at,
            source=approval.get("source_channel"),
            target="/approvals",
            requires_approval=True,
            metadata={"approval_id": approval["id"], "approval_kind": approval.get("kind")},
        ))

    commitments = list_commitments(include_completed=False)
    for commitment in commitments:
        if commitment.get("status") != "ACTIVE":
            continue
        deadline_state, priority, deadline_attention = _due_state(commitment.get("deadline_at"), now, 2)
        reminder_due = _reminder_due(commitment.get("reminder_at"), commitment.get("reminder_sent_at"), now)
        if reminder_due:
            priority = "high" if priority == "low" else priority
        if not deadline_attention and not reminder_due and mode != "all":
            continue
        title = f"Напоминание: {commitment['title']}" if reminder_due else commitment["title"]
        items.append(_action(
            action_id=f"commitment:{commitment['id']}",
            kind="commitment",
            source_id=commitment["id"],
            title=title,
            summary="Срок обязательства просрочен." if deadline_state == "overdue" else "Активное обязательство требует внимания.",
            status=deadline_state,
            priority=priority,
            due_at=commitment.get("deadline_at"),
            reminder_at=commitment.get("reminder_at"),
            reminder_due=reminder_due,
            source=commitment.get("source_type"),
            target="/commitments",
            metadata={"owner": commitment.get("owner"), "confidence": commitment.get("confidence")},
        ))

    subscriptions = list_subscriptions()
    for subscription in subscriptions:
        if subscription.get("status") != "ACTIVE":
            continue
        event_at = subscription.get("next_charge_at") or subscription.get("trial_ends_at")
        event_state, priority, event_attention = _due_state(event_at, now, 7)
        reminder_due = _reminder_due(subscription.get("reminder_at"), subscription.get("reminder_sent_at"), now)
        if reminder_due:
            priority = "high" if priority == "low" else priority
        if not event_attention and not reminder_due and mode != "all":
            continue
        event_label = "списание" if subscription.get("next_charge_at") else "окончание trial"
        title = f"Напоминание: {subscription['name']}" if reminder_due else f"Проверьте {event_label}: {subscription['name']}"
        items.append(_action(
            action_id=f"subscription:{subscription['id']}",
            kind="subscription",
            source_id=subscription["id"],
            title=title,
            summary="Дата уже прошла." if event_state == "overdue" else "Проверьте, нужно ли продолжать подписку.",
            status=event_state,
            priority=priority,
            due_at=event_at,
            reminder_at=subscription.get("reminder_at"),
            reminder_due=reminder_due,
            source=subscription.get("source_type"),
            target="/subscriptions",
            metadata={"provider": subscription.get("provider"), "amount": subscription.get("amount"), "currency": subscription.get("currency")},
        ))

    countdown_result = get_all_countdowns()
    countdowns = countdown_result.get("countdowns", []) if isinstance(countdown_result, dict) else []
    for countdown in countdowns:
        days = countdown.get("days_remaining")
        if not isinstance(days, int):
            continue
        attention = days <= 7
        if not attention and mode != "all":
            continue
        status = "overdue" if days < 0 else ("due_today" if days == 0 else "upcoming")
        priority = "critical" if days < 0 else ("high" if days <= 7 else "low")
        items.append(_action(
            action_id=f"deadline:{countdown['id']}",
            kind="deadline",
            source_id=countdown["id"],
            title=countdown["title"],
            summary="Дедлайн просрочен." if days < 0 else f"До дедлайна {days} дн.",
            status=status,
            priority=priority,
            due_at=countdown.get("target_date"),
            source="COUNTDOWN",
            target="/deadlines",
            metadata={"category": countdown.get("category"), "days_remaining": days},
        ))

    if include_external:
        from backend.app.connectors.mail_connector import list_unread_emails
        for account in ("gmail", "ukrnet"):
            result = list_unread_emails(account, limit=20, bypass_last_seen=True)
            if isinstance(result, dict) and result.get("status") == "error":
                continue
            unread = len(result)
            if unread:
                items.append(_action(
                    action_id=f"mail:{account}",
                    kind="mail",
                    source_id=account,
                    title=f"Непрочитанные письма: {account}",
                    summary=f"В очереди {unread} писем.",
                    status="unread",
                    priority="low",
                    source=account,
                    target="/mail",
                    metadata={"unread_count": unread},
                ))

    items = [item for item in items if _include(item, mode)]
    items.sort(key=_sort_key)
    overdue = sum(item["status"] == "overdue" for item in items)
    due_today = sum(item["status"] == "due_today" for item in items)
    return {
        "generated_at": now.isoformat(),
        "timezone": str(now.tzinfo),
        "mode": mode,
        "summary": {
            "total": len(items),
            "returned": min(len(items), limit),
            "critical": sum(item["priority"] == "critical" for item in items),
            "high": sum(item["priority"] == "high" for item in items),
            "overdue": overdue,
            "due_today": due_today,
            "requires_approval": sum(item["requires_approval"] for item in items),
            "reminders_due": sum(item["reminder_due"] for item in items),
        },
        "actions": items[:limit],
    }
